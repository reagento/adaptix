from typing import Any, Sequence

import pytest

from dataclass_factory_30.factory import BuiltinMediator, RawRecipeSearcher, RecursionResolving
from dataclass_factory_30.provider import CannotProvide, FieldRM, Request, TypeHintRM
from dataclass_factory_30.provider.provider_basics import ExactFieldNameRC, ExactTypeRC, StackEndRC, create_req_checker


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
        checker(
            _create_mediator(TypeHintRM(int)),
            TypeHintRM(int),
        )

    with pytest.raises(CannotProvide, match="Request stack is too small"):
        checker(
            _create_mediator(TypeHintRM(int), TypeHintRM(str)),
            TypeHintRM(int),
        )

    with pytest.raises(CannotProvide):
        checker(
            _create_mediator(TypeHintRM(int), TypeHintRM(str), TypeHintRM(str)),
            TypeHintRM(int),
        )

    checker(
        _create_mediator(TypeHintRM(int), TypeHintRM(str), TypeHintRM(bool)),
        TypeHintRM(int),
    )
    checker(
        _create_mediator(TypeHintRM(int), TypeHintRM(int), TypeHintRM(str), TypeHintRM(bool)),
        TypeHintRM(int),
    )
    checker(
        _create_mediator(TypeHintRM(str), TypeHintRM(int), TypeHintRM(str), TypeHintRM(bool)),
        TypeHintRM(int),
    )
