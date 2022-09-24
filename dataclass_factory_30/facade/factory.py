from abc import ABC, abstractmethod
from copy import copy
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
    ATTRS_FIGURE_PROVIDER,
    CLASS_INIT_FIGURE_PROVIDER,
    DATACLASS_FIGURE_PROVIDER,
    NAMED_TUPLE_FIGURE_PROVIDER,
    TYPED_DICT_FIGURE_PROVIDER,
    ABCProxy,
    BuiltinInputExtractionMaker,
    BuiltinOutputCreationMaker,
    BytearrayBase64Provider,
    BytesBase64Provider,
    CfgExtraPolicy,
    CoercionLimiter,
    DictProvider,
    EnumExactValueProvider,
    FactoryProvider,
    IsoFormatProvider,
    IterableProvider,
    LiteralProvider,
    ModelParserProvider,
    ModelSerializerProvider,
    NameMapper,
    NameSanitizer,
    NewTypeUnwrappingProvider,
    NoneProvider,
    ParserRequest,
    Provider,
    RegexPatternProvider,
    Request,
    SecondsTimedeltaProvider,
    SerializerRequest,
    TypeHintTagsUnwrappingProvider,
    UnionProvider,
)
from ..provider.model import ExtraPolicy, ExtraSkip, make_input_creation, make_output_extraction
from .provider import parser, serializer


def stub(arg):
    return arg


class BuiltinFactory(OperatingFactory, ABC):
    """A factory contains builtin providers"""

    recipe = [
        NoneProvider(),

        parser(Any, stub),
        serializer(Any, stub),

        IsoFormatProvider(datetime),
        IsoFormatProvider(date),
        IsoFormatProvider(time),
        SecondsTimedeltaProvider(),

        EnumExactValueProvider(),  # it has higher priority than int for IntEnum

        CoercionLimiter(parser(int), [int]),
        serializer(int, stub),

        CoercionLimiter(parser(float), [float, int]),
        serializer(float, stub),

        CoercionLimiter(parser(str, stub), [str]),
        serializer(str, stub),

        CoercionLimiter(parser(bool, stub), [bool]),
        serializer(bool, stub),

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
        RegexPatternProvider(),

        ABCProxy(Mapping, dict),
        ABCProxy(MutableMapping, dict),
        ABCProxy(ByteString, bytes),

        ModelParserProvider(NameSanitizer(), BuiltinInputExtractionMaker(), make_input_creation),
        ModelSerializerProvider(NameSanitizer(), make_output_extraction, BuiltinOutputCreationMaker()),

        NameMapper(),

        NAMED_TUPLE_FIGURE_PROVIDER,
        TYPED_DICT_FIGURE_PROVIDER,
        DATACLASS_FIGURE_PROVIDER,
        CLASS_INIT_FIGURE_PROVIDER,
        ATTRS_FIGURE_PROVIDER,

        NewTypeUnwrappingProvider(),
        TypeHintTagsUnwrappingProvider(),
    ]

    @abstractmethod
    def clear_cache(self):
        pass


T = TypeVar('T')
RequestTV = TypeVar('RequestTV', bound=Request)
F = TypeVar('F', bound='Factory')


class Factory(BuiltinFactory):
    def __init__(
        self,
        *,
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

    def replace(
        self: F,
        *,
        strict_coercion: Optional[bool] = None,
        debug_path: Optional[bool] = None,
        extra_policy: Optional[ExtraPolicy] = None,
    ) -> F:
        # pylint: disable=protected-access
        clone = self._clone()

        if strict_coercion is not None:
            clone._strict_coercion = strict_coercion

        if debug_path is not None:
            clone._debug_path = debug_path

        if extra_policy is not None:
            clone._extra_policy = extra_policy

        return clone

    def extend(self: F, *, recipe: List[Provider]) -> F:
        # pylint: disable=protected-access
        clone = self._clone()
        clone._inc_instance_recipe = recipe + clone._inc_instance_recipe
        return clone

    def _after_clone(self):
        self.clear_cache()

    def _clone(self: F) -> F:
        # pylint: disable=protected-access
        self_copy = copy(self)
        self_copy._after_clone()
        return self_copy

    def _get_config_recipe(self) -> List[Provider]:
        return [
            FactoryProvider(CfgExtraPolicy, lambda: self._extra_policy),
        ]

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
            return self._facade_provide(
                SerializerRequest(
                    tp,
                    debug_path=self._debug_path
                )
            )

    def clear_cache(self):
        self._parser_cache = {}
        self._serializers_cache = {}
