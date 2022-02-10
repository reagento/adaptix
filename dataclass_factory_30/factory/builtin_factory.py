from abc import ABC, abstractmethod
from datetime import datetime, date, time
from decimal import Decimal
from fractions import Fraction
from ipaddress import IPv4Address, IPv6Address, IPv4Network, IPv6Network, IPv4Interface, IPv6Interface
from itertools import chain
from pathlib import Path
from typing import Any
from uuid import UUID

from .basic_factory import IncrementalRecipe, ProvidingFromRecipe
from .mediator import StubsRecursionResolver, RecursionResolving
from ..provider import (
    Provider,
    as_parser,
    as_serializer,
    NoneProvider,
    IsoFormatProvider,
    TimedeltaProvider,
    BytesBase64Provider,
    LiteralProvider,
    UnionProvider,
    NewTypeUnwrappingProvider,
    TypeHintTagsUnwrappingProvider,
    CoercionLimiter,
    EnumExactValueProvider,
    FieldsParserProvider,
    NameMapper,
    NamedTupleFieldsProvider,
    TypedDictFieldsProvider,
    DataclassFieldsProvider,
    ClassInitFieldsProvider,
    ValueProvider,
    ParserRequest,
    LimitingProvider,
    create_req_checker,
    SerializerRequest,
)
from ..provider.generic_provider import IterableProvider


def stub(arg):
    return arg


def _as_is_parser_provider(tp: type) -> Provider:
    return CoercionLimiter(as_parser(tp, stub), [tp])


def _stub_serializer(tp: type) -> Provider:
    return as_serializer(tp, stub)


class FuncWrapper:
    __slots__ = ('__call__',)

    def __init__(self):
        self.__call__ = None

    def set_func(self, func):
        self.__call__ = func.__call__


class FuncRecursionResolver(StubsRecursionResolver):
    def get_stub(self, request):
        return FuncWrapper()

    def saturate_stub(self, actual, stub) -> None:
        stub.set_func(actual)


class OperatingFactory(IncrementalRecipe, ProvidingFromRecipe, ABC):
    """A factory that can operate as Factory but have no predefined providers"""

    def _get_recursion_resolving(self) -> RecursionResolving:
        return RecursionResolving(
            {
                ParserRequest: FuncRecursionResolver(),
                SerializerRequest: FuncRecursionResolver(),
            }
        )


class BuiltinFactory(OperatingFactory, ABC):
    """A factory contains builtin providers"""

    recipe = [
        NoneProvider(),

        # omit wrapping with foreign_parser
        LimitingProvider(
            create_req_checker(Any),
            ValueProvider(ParserRequest, stub)
        ),
        as_serializer(Any, stub),

        IsoFormatProvider(datetime),
        IsoFormatProvider(date),
        IsoFormatProvider(time),
        TimedeltaProvider(),

        EnumExactValueProvider(),  # it has higher priority than int for IntEnum

        CoercionLimiter(as_parser(int), [int]),
        _stub_serializer(int),

        CoercionLimiter(as_parser(float), [float, int]),
        _stub_serializer(float),

        _as_is_parser_provider(str),
        _stub_serializer(str),

        _as_is_parser_provider(bool),
        _stub_serializer(bool),

        CoercionLimiter(as_parser(Decimal), [str, Decimal]),
        as_serializer(Decimal, Decimal.__str__),
        CoercionLimiter(as_parser(Fraction), [str, Fraction]),
        as_serializer(Fraction, Fraction.__str__),

        BytesBase64Provider(),

        *chain.from_iterable(
            (
                as_parser(tp),
                as_serializer(tp, tp.__str__),
            )
            for tp in [
                UUID, Path,
                IPv4Address, IPv6Address,
                IPv4Network, IPv6Network,
                IPv4Interface, IPv6Interface,
            ]
        ),

        LiteralProvider(),
        UnionProvider(),
        IterableProvider(),

        NewTypeUnwrappingProvider(),
        TypeHintTagsUnwrappingProvider(),

        FieldsParserProvider(),

        NameMapper(),

        NamedTupleFieldsProvider(),
        TypedDictFieldsProvider(),
        DataclassFieldsProvider(),
        ClassInitFieldsProvider(),
    ]

    @abstractmethod
    def clear_cache(self):
        pass
