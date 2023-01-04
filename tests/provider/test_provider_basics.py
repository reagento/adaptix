from typing import Any

import pytest

from _dataclass_factory.provider.provider_basics import StackEndRC, create_req_checker
from _dataclass_factory.provider.request_cls import LocatedRequest, TypeHintLocation
from _dataclass_factory.retort import BuiltinMediator, RawRecipeSearcher, RecursionResolving
from dataclass_factory import CannotProvide, Request


def create_mediator(*elements: Request[Any]):
    return BuiltinMediator(
        searcher=RawRecipeSearcher([]),
        recursion_resolving=RecursionResolving(),
        request_stack=elements,
    )


def test_stack_end_rc():
    checker = StackEndRC(
        [
            create_req_checker(int),
            create_req_checker(str),
            create_req_checker(bool),
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
            LocatedRequest(loc=TypeHintLocation(int)),
        )

    with pytest.raises(CannotProvide):
        checker.check_request(
            create_mediator(
                LocatedRequest(loc=TypeHintLocation(int)),
                LocatedRequest(loc=TypeHintLocation(str)),
                LocatedRequest(loc=TypeHintLocation(str)),
            ),
            LocatedRequest(loc=TypeHintLocation(int)),
        )

    checker.check_request(
        create_mediator(
            LocatedRequest(loc=TypeHintLocation(int)),
            LocatedRequest(loc=TypeHintLocation(str)),
            LocatedRequest(loc=TypeHintLocation(bool)),
        ),
        LocatedRequest(loc=TypeHintLocation(int)),
    )
    checker.check_request(
        create_mediator(
            LocatedRequest(loc=TypeHintLocation(int)),
            LocatedRequest(loc=TypeHintLocation(int)),
            LocatedRequest(loc=TypeHintLocation(str)),
            LocatedRequest(loc=TypeHintLocation(bool)),
        ),
        LocatedRequest(loc=TypeHintLocation(int)),
    )
    checker.check_request(
        create_mediator(
            LocatedRequest(loc=TypeHintLocation(str)),
            LocatedRequest(loc=TypeHintLocation(int)),
            LocatedRequest(loc=TypeHintLocation(str)),
            LocatedRequest(loc=TypeHintLocation(bool)),
        ),
        LocatedRequest(loc=TypeHintLocation(int)),
    )
