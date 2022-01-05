from abc import ABC, abstractmethod
from datetime import datetime, date, time
from decimal import Decimal
from fractions import Fraction
from ipaddress import IPv4Address, IPv6Address, IPv4Network, IPv6Network, IPv4Interface, IPv6Interface
from itertools import chain
from pathlib import Path
from typing import final, List, Any, ClassVar, Type
from uuid import UUID

from .basic_factory import IncrementalRecipe, ProvidingFromRecipe
from .mediator import RecursionResolving
from ..provider import (
    StaticProvider,
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
)
from ..provider.generic_provider import IterableProvider


def stub(arg):
    return arg


class MultiInheritanceFactory(IncrementalRecipe, ProvidingFromRecipe, ABC):
    _mtf_bases: ClassVar[List[Type['MultiInheritanceFactory']]] = []

    def __init_subclass__(cls, **kwargs):
        cls._mtf_bases = [
            base for base in cls.__bases__
            if issubclass(base, MultiInheritanceFactory) and base != MultiInheritanceFactory
        ]

    @abstractmethod
    def _get_raw_config_recipe(self) -> List[Provider]:
        pass

    @final
    def _get_config_recipe(self) -> List[Provider]:
        result = []
        for base in self._mtf_bases:
            result.extend(
                base._get_config_recipe(self)
            )

        return result

    @abstractmethod
    def _get_raw_recursion_resolving(self) -> RecursionResolving:
        pass

    @final
    def _get_recursion_resolving(self) -> RecursionResolving:
        result = {}
        for base in self._mtf_bases:
            result.update(base._get_raw_recursion_resolving(self).to_dict())

        return RecursionResolving(result)


def _as_is_parser_provider(tp: type) -> Provider:
    return CoercionLimiter(as_parser(tp, stub), [tp])


def _stub_serializer(tp: type) -> Provider:
    return as_serializer(tp, stub)


class BuiltinFactory(MultiInheritanceFactory, StaticProvider, ABC):
    recipe = [
        NoneProvider(),
        as_parser(Any, stub),
        as_serializer(Any, stub),

        IsoFormatProvider(datetime),
        IsoFormatProvider(date),
        IsoFormatProvider(time),
        TimedeltaProvider(),

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
        TypeHintTagsUnwrappingProvider()
    ]

    @abstractmethod
    def clear_cache(self):
        pass
