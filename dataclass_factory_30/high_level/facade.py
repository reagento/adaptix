from types import MethodType, BuiltinMethodType
from typing import TypeVar, Type, overload, Any, Callable

from ..common import Parser, Serializer
from ..core import Provider
from ..low_level import (
    ProvCtxChecker, AsProvider, NextProvider,
    ParserProvider, SerializerProvider,
    ConstructorParserProvider,
)
from ..type_tools.utils import is_generic_class

T = TypeVar('T')


@overload
def as_parser(pred: Type[T], func: Parser[Any, T]) -> Provider:
    pass


@overload
def as_parser(pred: ProvCtxChecker.ALLOWS, func: Parser) -> Provider:
    pass


def as_parser(pred: ProvCtxChecker.ALLOWS, func: Parser) -> Provider:
    return AsProvider(ParserProvider, ProvCtxChecker(pred), func)


@overload
def as_serializer(pred: Type[T], func: Serializer[Any, T]) -> Provider:
    pass


@overload
def as_serializer(pred: ProvCtxChecker.ALLOWS, func: Serializer) -> Provider:
    pass


def as_serializer(pred: ProvCtxChecker.ALLOWS, func: Serializer) -> Provider:
    return AsProvider(SerializerProvider, ProvCtxChecker(pred), func)


NEXT_PROVIDER = NextProvider()


@overload
def as_constructor(constr_or_pred: Type[T], constructor: Callable[..., T]) -> ParserProvider:
    pass


@overload
def as_constructor(constr_or_pred: ProvCtxChecker.ALLOWS, constructor: Callable) -> ParserProvider:
    pass


@overload
def as_constructor(constr_or_pred: Callable) -> ParserProvider:
    pass


def as_constructor(constr_or_pred, constructor=None) -> ParserProvider:
    if constructor is None:
        if not isinstance(constr_or_pred, (MethodType, BuiltinMethodType)):
            raise ValueError(
                'as_constructor() with one argument expects classmethod'
            )

        bound = constr_or_pred.__self__

        if not isinstance(bound, type):
            raise ValueError(
                'as_constructor() with one argument expects classmethod'
            )

        if is_generic_class(bound):
            raise ValueError(
                'as_constructor() with one argument does not support generic'
            )

        return ConstructorParserProvider(
            ProvCtxChecker(bound), constr_or_pred
        )

    return ConstructorParserProvider(
        ProvCtxChecker(constr_or_pred), constructor
    )
