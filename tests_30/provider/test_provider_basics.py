from typing import Any

import pytest

from dataclass_factory_30.provider import CannotProvide, Request, TypeHintLocation
from dataclass_factory_30.provider.provider_basics import StackEndRC, create_req_checker
from dataclass_factory_30.retort import BuiltinMediator, RawRecipeSearcher, RecursionResolving


def _create_mediator(*arg: Request[Any]):
    return BuiltinMediator(
        searcher=RawRecipeSearcher([]),
        recursion_resolving=RecursionResolving(),
        request_stack=arg,
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
            _create_mediator(TypeHintLocation(int)),
            TypeHintLocation(int),
        )

    with pytest.raises(CannotProvide, match="Request stack is too small"):
        checker.check_request(
            _create_mediator(TypeHintLocation(int), TypeHintLocation(str)),
            TypeHintLocation(int),
        )

    with pytest.raises(CannotProvide):
        checker.check_request(
            _create_mediator(TypeHintLocation(int), TypeHintLocation(str), TypeHintLocation(str)),
            TypeHintLocation(int),
        )

    checker.check_request(
        _create_mediator(TypeHintLocation(int), TypeHintLocation(str), TypeHintLocation(bool)),
        TypeHintLocation(int),
    )
    checker.check_request(
        _create_mediator(TypeHintLocation(int), TypeHintLocation(int), TypeHintLocation(str), TypeHintLocation(bool)),
        TypeHintLocation(int),
    )
    checker.check_request(
        _create_mediator(TypeHintLocation(str), TypeHintLocation(int), TypeHintLocation(str), TypeHintLocation(bool)),
        TypeHintLocation(int),
    )
