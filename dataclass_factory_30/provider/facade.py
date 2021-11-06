from typing import TypeVar, Type, overload, Any, Callable, Tuple

from .provider import FuncProvider, ConstructorParserProvider, NextProvider
from .request_cls import (
    SerializerRequest, ParserRequest,
)
from .utils import resolve_classmethod
from ..common import Parser, Serializer

T = TypeVar('T')

AsParser = Tuple[Any, Parser]


@overload
def as_parser(func_or_pred: Type[T], func: Parser[Any, T]) -> AsParser:
    pass


@overload
def as_parser(func_or_pred: Any, func: Parser) -> AsParser:
    pass


@overload
def as_parser(func_or_pred: Parser) -> AsParser:
    pass


def as_parser(func_or_pred, func=None):
    if func is None:
        pred, func = resolve_classmethod(func_or_pred)
    else:
        pred, func = func_or_pred, func

    return pred, FuncProvider(ParserRequest, func)


AsSerializer = Tuple[Any, Serializer]


@overload
def as_serializer(func_or_pred: Type[T], func: Serializer[Any, T]) -> AsSerializer:
    pass


@overload
def as_serializer(func_or_pred: Any, func: Serializer) -> AsSerializer:
    pass


@overload
def as_serializer(func_or_pred: Serializer) -> AsSerializer:
    pass


def as_serializer(func_or_pred, func=None):
    if func is None:
        pred, func = resolve_classmethod(func_or_pred)
    else:
        pred, func = func_or_pred, func

    return pred, FuncProvider(SerializerRequest, func)


AsConstructor = Tuple[Any, Parser]


@overload
def as_constructor(func_or_pred: Type[T], constructor: Callable[..., T]) -> AsConstructor:
    pass


@overload
def as_constructor(func_or_pred: Any, constructor: Callable) -> AsConstructor:
    pass


@overload
def as_constructor(func_or_pred: Callable) -> AsConstructor:
    pass


def as_constructor(func_or_pred, constructor=None):
    if constructor is None:
        pred, func = resolve_classmethod(func_or_pred)
    else:
        pred, func = func_or_pred, constructor

    return pred, ConstructorParserProvider(func)


NEXT_PROVIDER = NextProvider()
