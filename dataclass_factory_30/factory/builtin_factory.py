from abc import ABC, abstractmethod
from datetime import datetime, date, time
from ipaddress import IPv4Address, IPv6Address, IPv4Network, IPv6Network, IPv4Interface, IPv6Interface
from itertools import chain
from pathlib import Path
from typing import final, List
from uuid import UUID

from .basic_factory import IncrementalRecipe, ProvidingFromRecipe
from .mediator import RecursionResolving
from ..provider import StaticProvider, Provider, as_parser, as_serializer
from ..provider.generic_provider import (
    LiteralProvider,
    UnionProvider,
    NewTypeUnwrappingProvider,
    TypeHintTagsUnwrappingProvider,
    stub,
)
from ..provider.provider_basics import CoercionLimiter
from ..provider.concrete_provider import (
    NoneProvider,
    IsoFormatProvider,
    TimedeltaProvider,
    BytesBase64Provider,
)


class MultiInheritanceFactory(IncrementalRecipe, ProvidingFromRecipe, ABC):
    @abstractmethod
    def _get_raw_config_recipe(self) -> List[Provider]:
        pass

    @final
    def _get_config_recipe(self) -> List[Provider]:
        result = []
        for base in type(self).__bases__:
            if issubclass(base, MultiInheritanceFactory):
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
        for base in reversed(type(self).__bases__):
            if issubclass(base, MultiInheritanceFactory):
                result.update(base._get_raw_recursion_resolving(self).to_dict())

        return RecursionResolving(result)


def _as_is_parser_provider(tp: type) -> Provider:
    return CoercionLimiter(as_parser(tp, stub), [tp])


class BuiltinFactory(MultiInheritanceFactory, StaticProvider, ABC):
    recipe = [
        NoneProvider(),

        IsoFormatProvider(datetime),
        IsoFormatProvider(date),
        IsoFormatProvider(time),
        TimedeltaProvider(),

        CoercionLimiter(as_parser(int), [int]),
        CoercionLimiter(as_parser(float), [float, int]),
        _as_is_parser_provider(str),
        _as_is_parser_provider(bool),

        BytesBase64Provider(),

        *chain.from_iterable(
            (
                as_parser(tp),
                as_serializer(tp.__str__),
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

        NewTypeUnwrappingProvider(),
        TypeHintTagsUnwrappingProvider()
    ]

    @abstractmethod
    def clear_cache(self):
        pass
