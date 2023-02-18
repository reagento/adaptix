from contextlib import nullcontext
from dataclasses import dataclass
from typing import Any, List, Union

import pytest

from adaptix import CannotProvide, P, Request
from adaptix._internal.common import TypeHint
from adaptix._internal.model_tools import NoDefault
from adaptix._internal.provider import create_request_checker
from adaptix._internal.provider.request_cls import FieldLocation, LocatedRequest, TypeHintLocation
from adaptix._internal.provider.request_filtering import AnyRequestChecker, RequestPattern, StackEndRC
from adaptix._internal.retort import BuiltinMediator, RawRecipeSearcher, RecursionResolving
from tests_helpers import full_match_regex_str


def create_mediator(*elements: Request[Any]):
    return BuiltinMediator(
        searcher=RawRecipeSearcher([]),
        recursion_resolving=RecursionResolving(),
        request_stack=elements,
    )


def test_stack_end_rc():
    checker = StackEndRC(
        [
            create_request_checker(int),
            create_request_checker(str),
            create_request_checker(bool),
        ]
    )

    with pytest.raises(CannotProvide, match="Request stack is too small"):
        checker.check_request(
            create_mediator(
                LocatedRequest(loc=TypeHintLocation(int)),
            ),
            LocatedRequest(loc=TypeHintLocation(int)),
        )

    with pytest.raises(CannotProvide, match="Request stack is too small"):
        checker.check_request(
            create_mediator(
                LocatedRequest(loc=TypeHintLocation(int)),
                LocatedRequest(loc=TypeHintLocation(str)),
            ),
            LocatedRequest(loc=TypeHintLocation(str)),
        )

    with pytest.raises(CannotProvide):
        checker.check_request(
            create_mediator(
                LocatedRequest(loc=TypeHintLocation(int)),
                LocatedRequest(loc=TypeHintLocation(str)),
                LocatedRequest(loc=TypeHintLocation(str)),
            ),
            LocatedRequest(loc=TypeHintLocation(str)),
        )

    checker.check_request(
        create_mediator(
            LocatedRequest(loc=TypeHintLocation(int)),
            LocatedRequest(loc=TypeHintLocation(str)),
            LocatedRequest(loc=TypeHintLocation(bool)),
        ),
        LocatedRequest(loc=TypeHintLocation(bool)),
    )
    checker.check_request(
        create_mediator(
            LocatedRequest(loc=TypeHintLocation(int)),
            LocatedRequest(loc=TypeHintLocation(int)),
            LocatedRequest(loc=TypeHintLocation(str)),
            LocatedRequest(loc=TypeHintLocation(bool)),
        ),
        LocatedRequest(loc=TypeHintLocation(bool)),
    )
    checker.check_request(
        create_mediator(
            LocatedRequest(loc=TypeHintLocation(str)),
            LocatedRequest(loc=TypeHintLocation(int)),
            LocatedRequest(loc=TypeHintLocation(str)),
            LocatedRequest(loc=TypeHintLocation(bool)),
        ),
        LocatedRequest(loc=TypeHintLocation(bool)),
    )


def test_nested_start_rc():
    checker = StackEndRC(
        [
            AnyRequestChecker(),
            StackEndRC(
                [
                    create_request_checker(bool),
                    create_request_checker(int),
                    create_request_checker(str),
                ]
            ),
            create_request_checker(bool),
        ]
    )

    checker.check_request(
        create_mediator(
            LocatedRequest(loc=TypeHintLocation(bool)),
            LocatedRequest(loc=TypeHintLocation(int)),
            LocatedRequest(loc=TypeHintLocation(str)),
            LocatedRequest(loc=TypeHintLocation(bool)),
        ),
        LocatedRequest(loc=TypeHintLocation(bool)),
    )

    with pytest.raises(CannotProvide, match="Request stack is too small"):
        checker.check_request(
            create_mediator(
                LocatedRequest(loc=TypeHintLocation(int)),
                LocatedRequest(loc=TypeHintLocation(str)),
                LocatedRequest(loc=TypeHintLocation(bool)),
            ),
            LocatedRequest(loc=TypeHintLocation(bool)),
        )

    with pytest.raises(CannotProvide):
        checker.check_request(
            create_mediator(
                LocatedRequest(loc=TypeHintLocation(str)),
                LocatedRequest(loc=TypeHintLocation(int)),
                LocatedRequest(loc=TypeHintLocation(str)),
                LocatedRequest(loc=TypeHintLocation(bool)),
            ),
            LocatedRequest(loc=TypeHintLocation(bool)),
        )


def check_request_pattern(
    request_pattern: RequestPattern,
    request_or_stack: Union[Request, List[Request]],
    *,
    fail: bool,
) -> None:
    if isinstance(request_or_stack, list):
        request = request_or_stack[-1]
        stack = request_or_stack
    else:
        request = request_or_stack
        stack = []

    with pytest.raises(CannotProvide) if fail else nullcontext():
        request_pattern.build_request_checker().check_request(
            create_mediator(*stack),
            request,
        )


@dataclass
class WithUserName:
    user_name: str


def field_loc(name: str, tp: TypeHint) -> FieldLocation:
    return FieldLocation(
        type=tp,
        name=name,
        default=NoDefault(),
        metadata={},
    )


def test_request_pattern():
    check_request_pattern(
        P[int],
        LocatedRequest(loc=TypeHintLocation(int)),
        fail=False,
    )
    check_request_pattern(
        P[int],
        LocatedRequest(loc=TypeHintLocation(str)),
        fail=True,
    )

    check_request_pattern(
        P[WithUserName].user_name,
        [
            LocatedRequest(loc=TypeHintLocation(WithUserName)),
            LocatedRequest(loc=field_loc('user_name', str)),
        ],
        fail=False,
    )
    check_request_pattern(
        P[WithUserName].user_name,
        [
            LocatedRequest(loc=TypeHintLocation(WithUserName)),
            LocatedRequest(loc=field_loc('user_name', int)),
        ],
        fail=False,
    )
    check_request_pattern(
        P[WithUserName].user_id,
        [
            LocatedRequest(loc=TypeHintLocation(WithUserName)),
            LocatedRequest(loc=field_loc('user_name', int)),
        ],
        fail=True,
    )

    with pytest.raises(
        TypeError,
        match=full_match_regex_str(
            'Can not use RequestPattern as predicate inside RequestPattern.'
            ' If you want to combine several RequestPattern, you can use `+` operator'
        )
    ):
        P[WithUserName][P.user_name]

    check_request_pattern(
        P[WithUserName] + P.user_name,
        [
            LocatedRequest(loc=TypeHintLocation(WithUserName)),
            LocatedRequest(loc=field_loc('user_name', int)),
        ],
        fail=False,
    )
