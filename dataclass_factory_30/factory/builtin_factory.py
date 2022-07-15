from abc import ABC, abstractmethod
from datetime import date, datetime, time
from decimal import Decimal
from fractions import Fraction
from ipaddress import IPv4Address, IPv4Interface, IPv4Network, IPv6Address, IPv6Interface, IPv6Network
from itertools import chain
from pathlib import Path
from typing import Any, ByteString, Mapping, MutableMapping
from uuid import UUID

from ..provider import (
    CLASS_INIT_FIGURE_PROVIDER,
    DATACLASS_FIGURE_PROVIDER,
    NAMED_TUPLE_FIGURE_PROVIDER,
    TYPED_DICT_FIGURE_PROVIDER,
    ABCProxy,
    BuiltinInputCreationImageProvider,
    BuiltinInputExtractionImageProvider,
    BuiltinOutputCreationImageProvider,
    BuiltinOutputExtractionImageProvider,
    BytearrayBase64Provider,
    BytesBase64Provider,
    CoercionLimiter,
    DictProvider,
    EnumExactValueProvider,
    FieldsParserProvider,
    FieldsSerializerProvider,
    IsoFormatProvider,
    IterableProvider,
    LiteralProvider,
    NameMapper,
    NameSanitizer,
    NewTypeUnwrappingProvider,
    NoneProvider,
    ParserRequest,
    Provider,
    SerializerRequest,
    TimedeltaProvider,
    TypeHintTagsUnwrappingProvider,
    UnionProvider,
    ValueProvider,
    as_parser,
    as_serializer,
    bound
)
from .basic_factory import IncrementalRecipe, ProvidingFromRecipe
from .mediator import RecursionResolving, StubsRecursionResolver


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
        bound(Any, ValueProvider(ParserRequest, stub)),
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
        BytearrayBase64Provider(),

        *chain.from_iterable(
            (
                as_parser(tp),
                as_serializer(tp, tp.__str__),  # type: ignore[arg-type]
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
        DictProvider(),

        ABCProxy(Mapping, dict),
        ABCProxy(MutableMapping, dict),
        ABCProxy(ByteString, bytes),

        FieldsParserProvider(NameSanitizer()),
        BuiltinInputExtractionImageProvider(),
        BuiltinInputCreationImageProvider(),

        FieldsSerializerProvider(NameSanitizer()),
        BuiltinOutputExtractionImageProvider(),
        BuiltinOutputCreationImageProvider(),

        NameMapper(),

        NAMED_TUPLE_FIGURE_PROVIDER,
        TYPED_DICT_FIGURE_PROVIDER,
        DATACLASS_FIGURE_PROVIDER,
        CLASS_INIT_FIGURE_PROVIDER,

        NewTypeUnwrappingProvider(),
        TypeHintTagsUnwrappingProvider(),
    ]

    @abstractmethod
    def clear_cache(self):
        pass
