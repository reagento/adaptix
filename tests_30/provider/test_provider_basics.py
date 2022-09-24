from typing import Any

import pytest

from dataclass_factory_30.provider import CannotProvide, Request, TypeHintRM
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
            _create_mediator(TypeHintRM(int)),
            TypeHintRM(int),
        )

    with pytest.raises(CannotProvide, match="Request stack is too small"):
        checker.check_request(
            _create_mediator(TypeHintRM(int), TypeHintRM(str)),
            TypeHintRM(int),
        )

    with pytest.raises(CannotProvide):
        checker.check_request(
            _create_mediator(TypeHintRM(int), TypeHintRM(str), TypeHintRM(str)),
            TypeHintRM(int),
        )

    checker.check_request(
        _create_mediator(TypeHintRM(int), TypeHintRM(str), TypeHintRM(bool)),
        TypeHintRM(int),
    )
    checker.check_request(
        _create_mediator(TypeHintRM(int), TypeHintRM(int), TypeHintRM(str), TypeHintRM(bool)),
        TypeHintRM(int),
    )
    checker.check_request(
        _create_mediator(TypeHintRM(str), TypeHintRM(int), TypeHintRM(str), TypeHintRM(bool)),
        TypeHintRM(int),
    )
