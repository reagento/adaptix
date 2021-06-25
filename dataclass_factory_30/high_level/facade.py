from typing import TypeVar, Type, overload, Any

from ..common import Parser, Serializer
from ..core import Provider
from ..low_level.provider_utils import ProvCtxChecker, AsProvider, NextProvider
from ..low_level.provider import ParserProvider, SerializerProvider

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
