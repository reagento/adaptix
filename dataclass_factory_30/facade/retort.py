from abc import ABC
from datetime import date, datetime, time
from decimal import Decimal
from fractions import Fraction
from ipaddress import IPv4Address, IPv4Interface, IPv4Network, IPv6Address, IPv6Interface, IPv6Network
from itertools import chain
from pathlib import Path
from typing import Any, ByteString, List, Mapping, MutableMapping, Optional, Type, TypeVar, overload
from uuid import UUID

from ..common import Dumper, Loader, TypeHint
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
    DumperRequest,
    EnumExactValueProvider,
    IsoFormatProvider,
    IterableProvider,
    LiteralProvider,
    LoaderRequest,
    ModelDumperProvider,
    ModelLoaderProvider,
    NameMapper,
    NameSanitizer,
    NewTypeUnwrappingProvider,
    NoneProvider,
    Provider,
    RegexPatternProvider,
    Request,
    SecondsTimedeltaProvider,
    TypeHintTagsUnwrappingProvider,
    UnionProvider,
    ValueProvider,
)
from ..provider.model import ExtraPolicy, ExtraSkip, make_input_creation, make_output_extraction
from ..retort import OperatingRetort
from .provider import dumper, loader


def stub(arg):
    return arg


class FilledRetort(OperatingRetort, ABC):
    """A retort contains builtin providers"""

    recipe = [
        NoneProvider(),

        loader(Any, stub),
        dumper(Any, stub),

        IsoFormatProvider(datetime),
        IsoFormatProvider(date),
        IsoFormatProvider(time),
        SecondsTimedeltaProvider(),

        EnumExactValueProvider(),  # it has higher priority than int for IntEnum

        CoercionLimiter(loader(int), [int]),
        dumper(int, stub),

        CoercionLimiter(loader(float), [float, int]),
        dumper(float, stub),

        CoercionLimiter(loader(str, stub), [str]),
        dumper(str, stub),

        CoercionLimiter(loader(bool, stub), [bool]),
        dumper(bool, stub),

        CoercionLimiter(loader(Decimal), [str, Decimal]),
        dumper(Decimal, Decimal.__str__),
        CoercionLimiter(loader(Fraction), [str, Fraction]),
        dumper(Fraction, Fraction.__str__),
        CoercionLimiter(loader(complex), [str, complex]),
        dumper(complex, complex.__str__),

        BytesBase64Provider(),
        BytearrayBase64Provider(),

        *chain.from_iterable(
            (
                loader(tp),
                dumper(tp, tp.__str__),  # type: ignore[arg-type]
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

        ModelLoaderProvider(NameSanitizer(), BuiltinInputExtractionMaker(), make_input_creation),
        ModelDumperProvider(NameSanitizer(), make_output_extraction, BuiltinOutputCreationMaker()),

        NameMapper(),

        NAMED_TUPLE_FIGURE_PROVIDER,
        TYPED_DICT_FIGURE_PROVIDER,
        DATACLASS_FIGURE_PROVIDER,
        CLASS_INIT_FIGURE_PROVIDER,
        ATTRS_FIGURE_PROVIDER,

        NewTypeUnwrappingProvider(),
        TypeHintTagsUnwrappingProvider(),
    ]


T = TypeVar('T')
RequestTV = TypeVar('RequestTV', bound=Request)
R = TypeVar('R', bound='AdornedRetort')


class AdornedRetort(OperatingRetort):
    """A retort implementing high-level user interface"""

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
        super().__init__(recipe)

    def _calculate_derived(self):
        super()._calculate_derived()
        self._loader_cache = {}
        self._dumper_cache = {}

    def replace(
        self: R,
        *,
        strict_coercion: Optional[bool] = None,
        debug_path: Optional[bool] = None,
        extra_policy: Optional[ExtraPolicy] = None,
    ) -> R:
        # pylint: disable=protected-access
        with self._clone() as clone:
            if strict_coercion is not None:
                clone._strict_coercion = strict_coercion

            if debug_path is not None:
                clone._debug_path = debug_path

            if extra_policy is not None:
                clone._extra_policy = extra_policy

        return clone

    def extend(self: R, *, recipe: List[Provider]) -> R:
        # pylint: disable=protected-access
        with self._clone() as clone:
            clone._inc_instance_recipe = recipe + clone._inc_instance_recipe

        return clone

    def _get_config_recipe(self) -> List[Provider]:
        return [
            ValueProvider(CfgExtraPolicy, self._extra_policy),
        ]

    def get_loader(self, tp: Type[T]) -> Loader[T]:
        try:
            return self._loader_cache[tp]
        except KeyError:
            loader_ = self._facade_provide(
                LoaderRequest(
                    type=tp,
                    strict_coercion=self._strict_coercion,
                    debug_path=self._debug_path
                )
            )
            self._loader_cache[tp] = loader_
            return loader_

    def get_dumper(self, tp: Type[T]) -> Dumper[T]:
        try:
            return self._dumper_cache[tp]
        except KeyError:
            dumper_ = self._facade_provide(
                DumperRequest(
                    type=tp,
                    debug_path=self._debug_path
                )
            )
            self._dumper_cache[tp] = dumper_
            return dumper_

    @overload
    def load(self, data: Any, tp: Type[T], /) -> T:
        ...

    @overload
    def load(self, data: Any, tp: TypeHint, /) -> Any:
        ...

    def load(self, data: Any, tp: TypeHint, /):
        return self.get_loader(tp)(data)

    @overload
    def dump(self, data: T, tp: Type[T], /) -> Any:
        ...

    @overload
    def dump(self, data: Any, tp: Optional[TypeHint] = None, /) -> Any:
        ...

    def dump(self, data: Any, tp: Optional[TypeHint] = None, /) -> Any:
        if tp is None:
            tp = type(data)
        return self.get_dumper(tp)(data)


class Retort(FilledRetort, AdornedRetort):
    pass
