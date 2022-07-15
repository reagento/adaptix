from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date, datetime, time
from decimal import Decimal
from fractions import Fraction
from ipaddress import IPv4Address, IPv4Interface, IPv4Network, IPv6Address, IPv6Interface, IPv6Network
from itertools import chain
from pathlib import Path
from typing import Any, ByteString, Dict, List, Mapping, MutableMapping, Optional, Type, TypeVar
from uuid import UUID

from ..common import Parser, Serializer, TypeHint
from ..factory import OperatingFactory
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
    CannotProvide,
    CfgExtraPolicy,
    CoercionLimiter,
    DictProvider,
    EnumExactValueProvider,
    FactoryProvider,
    FieldsParserProvider,
    FieldsSerializerProvider,
    IsoFormatProvider,
    IterableProvider,
    LiteralProvider,
    Mediator,
    NameMapper,
    NameSanitizer,
    NewTypeUnwrappingProvider,
    NoneProvider,
    ParserRequest,
    Provider,
    Request,
    SerializerRequest,
    TimedeltaProvider,
    TypeHintTagsUnwrappingProvider,
    UnionProvider,
    ValueProvider
)
from ..provider.model import ExtraPolicy, ExtraSkip
from .provider import bound, parser, serializer


def stub(arg):
    return arg


def _as_is_parser(tp: type) -> Provider:
    return CoercionLimiter(parser(tp, stub), [tp])


def _stub_serializer(tp: type) -> Provider:
    return serializer(tp, stub)


class BuiltinFactory(OperatingFactory, ABC):
    """A factory contains builtin providers"""

    recipe = [
        NoneProvider(),

        # omit wrapping with foreign_parser
        bound(Any, ValueProvider(ParserRequest, stub)),
        serializer(Any, stub),

        IsoFormatProvider(datetime),
        IsoFormatProvider(date),
        IsoFormatProvider(time),
        TimedeltaProvider(),

        EnumExactValueProvider(),  # it has higher priority than int for IntEnum

        CoercionLimiter(parser(int), [int]),
        _stub_serializer(int),

        CoercionLimiter(parser(float), [float, int]),
        _stub_serializer(float),

        _as_is_parser(str),
        _stub_serializer(str),

        _as_is_parser(bool),
        _stub_serializer(bool),

        CoercionLimiter(parser(Decimal), [str, Decimal]),
        serializer(Decimal, Decimal.__str__),
        CoercionLimiter(parser(Fraction), [str, Fraction]),
        serializer(Fraction, Fraction.__str__),

        BytesBase64Provider(),
        BytearrayBase64Provider(),

        *chain.from_iterable(
            (
                parser(tp),
                serializer(tp, tp.__str__),  # type: ignore[arg-type]
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


T = TypeVar('T')
RequestTV = TypeVar('RequestTV', bound=Request)


@dataclass
class NoSuitableProvider(Exception):
    important_error: Optional[CannotProvide]

    def __str__(self):
        return repr(self.important_error)


# TODO: Add JsonSchemaFactory with new API
class Factory(BuiltinFactory, Provider):
    def __init__(
        self,
        recipe: Optional[List[Provider]] = None,
        strict_coercion: bool = True,
        debug_path: bool = True,
        extra_policy: ExtraPolicy = ExtraSkip(),
    ):
        self._strict_coercion = strict_coercion
        self._debug_path = debug_path
        self._extra_policy = extra_policy

        self._parser_cache: Dict[TypeHint, Parser] = {}
        self._serializers_cache: Dict[TypeHint, Serializer] = {}

        super().__init__(recipe)

    def _get_config_recipe(self) -> List[Provider]:
        return [
            FactoryProvider(CfgExtraPolicy, lambda: self._extra_policy),
        ]

    def apply_provider(self, mediator: Mediator, request: Request[T]) -> T:
        return self._provide_from_recipe(request)

    def _facade_provide(self, request: Request[T]) -> T:
        try:
            return self._provide_from_recipe(request)
        except CannotProvide as e:
            important_error = e if e.is_important() else None
            raise NoSuitableProvider(important_error=important_error)

    def parser(self, tp: Type[T]) -> Parser[T]:
        try:
            return self._parser_cache[tp]
        except KeyError:
            return self._facade_provide(
                ParserRequest(
                    tp,
                    strict_coercion=self._strict_coercion,
                    debug_path=self._debug_path
                )
            )

    def serializer(self, tp: Type[T]) -> Serializer[T]:
        try:
            return self._serializers_cache[tp]
        except KeyError:
            return self._facade_provide(SerializerRequest(tp, debug_path=self._debug_path))

    def clear_cache(self):
        self._parser_cache = {}
        self._serializers_cache = {}
