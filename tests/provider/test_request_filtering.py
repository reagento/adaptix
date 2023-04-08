from contextlib import nullcontext
from dataclasses import dataclass
from typing import Any, Dict, List, Union

import pytest

from adaptix import CannotProvide, Chain, P, Request, Retort, loader
from adaptix._internal.common import TypeHint
from adaptix._internal.model_tools import NoDefault
from adaptix._internal.provider import create_request_checker
from adaptix._internal.provider.request_cls import FieldLoc, GenericParamLoc, LocatedRequest, LocMap, TypeHintLoc
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
                LocatedRequest(loc_map=LocMap(TypeHintLoc(int))),
            ),
            LocatedRequest(loc_map=LocMap(TypeHintLoc(int))),
        )

    with pytest.raises(CannotProvide, match="Request stack is too small"):
        checker.check_request(
            create_mediator(
                LocatedRequest(loc_map=LocMap(TypeHintLoc(int))),
                LocatedRequest(loc_map=LocMap(TypeHintLoc(str))),
            ),
            LocatedRequest(loc_map=LocMap(TypeHintLoc(str))),
        )

    with pytest.raises(CannotProvide):
        checker.check_request(
            create_mediator(
                LocatedRequest(loc_map=LocMap(TypeHintLoc(int))),
                LocatedRequest(loc_map=LocMap(TypeHintLoc(str))),
                LocatedRequest(loc_map=LocMap(TypeHintLoc(str))),
            ),
            LocatedRequest(loc_map=LocMap(TypeHintLoc(str))),
        )

    checker.check_request(
        create_mediator(
            LocatedRequest(loc_map=LocMap(TypeHintLoc(int))),
            LocatedRequest(loc_map=LocMap(TypeHintLoc(str))),
            LocatedRequest(loc_map=LocMap(TypeHintLoc(bool))),
        ),
        LocatedRequest(loc_map=LocMap(TypeHintLoc(bool))),
    )
    checker.check_request(
        create_mediator(
            LocatedRequest(loc_map=LocMap(TypeHintLoc(int))),
            LocatedRequest(loc_map=LocMap(TypeHintLoc(int))),
            LocatedRequest(loc_map=LocMap(TypeHintLoc(str))),
            LocatedRequest(loc_map=LocMap(TypeHintLoc(bool))),
        ),
        LocatedRequest(loc_map=LocMap(TypeHintLoc(bool))),
    )
    checker.check_request(
        create_mediator(
            LocatedRequest(loc_map=LocMap(TypeHintLoc(str))),
            LocatedRequest(loc_map=LocMap(TypeHintLoc(int))),
            LocatedRequest(loc_map=LocMap(TypeHintLoc(str))),
            LocatedRequest(loc_map=LocMap(TypeHintLoc(bool))),
        ),
        LocatedRequest(loc_map=LocMap(TypeHintLoc(bool))),
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
            LocatedRequest(loc_map=LocMap(TypeHintLoc(bool))),
            LocatedRequest(loc_map=LocMap(TypeHintLoc(int))),
            LocatedRequest(loc_map=LocMap(TypeHintLoc(str))),
            LocatedRequest(loc_map=LocMap(TypeHintLoc(bool))),
        ),
        LocatedRequest(loc_map=LocMap(TypeHintLoc(bool))),
    )

    with pytest.raises(CannotProvide, match="Request stack is too small"):
        checker.check_request(
            create_mediator(
                LocatedRequest(loc_map=LocMap(TypeHintLoc(int))),
                LocatedRequest(loc_map=LocMap(TypeHintLoc(str))),
                LocatedRequest(loc_map=LocMap(TypeHintLoc(bool))),
            ),
            LocatedRequest(loc_map=LocMap(TypeHintLoc(bool))),
        )

    with pytest.raises(CannotProvide):
        checker.check_request(
            create_mediator(
                LocatedRequest(loc_map=LocMap(TypeHintLoc(str))),
                LocatedRequest(loc_map=LocMap(TypeHintLoc(int))),
                LocatedRequest(loc_map=LocMap(TypeHintLoc(str))),
                LocatedRequest(loc_map=LocMap(TypeHintLoc(bool))),
            ),
            LocatedRequest(loc_map=LocMap(TypeHintLoc(bool))),
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


def field_loc_map(name: str, tp: TypeHint) -> LocMap:
    return LocMap(
        TypeHintLoc(tp),
        FieldLoc(
            name=name,
            default=NoDefault(),
            metadata={},
        )
    )


def test_request_pattern():
    check_request_pattern(
        P[int],
        LocatedRequest(loc_map=LocMap(TypeHintLoc(int))),
        fail=False,
    )
    check_request_pattern(
        P[int],
        LocatedRequest(loc_map=LocMap(TypeHintLoc(str))),
        fail=True,
    )

    check_request_pattern(
        P[WithUserName].user_name,
        [
            LocatedRequest(loc_map=LocMap(TypeHintLoc(WithUserName))),
            LocatedRequest(loc_map=field_loc_map('user_name', str)),
        ],
        fail=False,
    )
    check_request_pattern(
        P[WithUserName].user_name,
        [
            LocatedRequest(loc_map=LocMap(TypeHintLoc(WithUserName))),
            LocatedRequest(loc_map=field_loc_map('user_name', int)),
        ],
        fail=False,
    )
    check_request_pattern(
        P[WithUserName].user_id,
        [
            LocatedRequest(loc_map=LocMap(TypeHintLoc(WithUserName))),
            LocatedRequest(loc_map=field_loc_map('user_name', int)),
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
            LocatedRequest(loc_map=LocMap(TypeHintLoc(WithUserName))),
            LocatedRequest(loc_map=field_loc_map('user_name', int)),
        ],
        fail=False,
    )


def test_request_pattern_generic_arg():
    check_request_pattern(
        P[Dict].generic_arg(0, str),
        [
            LocatedRequest(loc_map=LocMap(TypeHintLoc(Dict))),
            LocatedRequest(loc_map=LocMap(TypeHintLoc(str), GenericParamLoc(0))),
        ],
        fail=False,
    )
    check_request_pattern(
        P[Dict].generic_arg(0, str),
        [
            LocatedRequest(loc_map=LocMap(TypeHintLoc(Dict))),
            LocatedRequest(loc_map=LocMap(TypeHintLoc(str), GenericParamLoc(1))),
        ],
        fail=True,
    )


def plus_one(data):
    return data + 1


def plus_two(data):
    return data + 2


def test_request_pattern_generic_arg_dict_override():
    retort = Retort(
        recipe=[
            loader(P[Dict].generic_arg(0, int), plus_one, Chain.LAST),
            loader(P[Dict].generic_arg(1, int), plus_two, Chain.LAST),
        ]
    )

    loaded_dict = retort.load({10: 20}, Dict[int, int])
    assert loaded_dict == {11: 22}
