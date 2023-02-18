from abc import ABC
from datetime import date, datetime, time
from decimal import Decimal
from fractions import Fraction
from ipaddress import IPv4Address, IPv4Interface, IPv4Network, IPv6Address, IPv6Interface, IPv6Network
from itertools import chain
from pathlib import Path
from typing import Any, ByteString, Iterable, Mapping, MutableMapping, Optional, Type, TypeVar, overload
from uuid import UUID

from ..common import Dumper, Loader, TypeHint, VarTuple
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
    NameSanitizer,
    NewTypeUnwrappingProvider,
    NoneProvider,
    Provider,
    RegexPatternProvider,
    Request,
    SecondsTimedeltaProvider,
    TypeHintLocation,
    TypeHintTagsUnwrappingProvider,
    UnionProvider,
)
from ..provider.model import ExtraSkip, make_input_creation, make_output_extraction
from ..provider.name_layout import (
    BuiltinExtraMoveAndPoliciesMaker,
    BuiltinNameLayoutProvider,
    BuiltinSievesMaker,
    BuiltinStructureMaker,
)
from ..retort import OperatingRetort
from .provider import as_is_dumper, as_is_loader, dumper, loader, name_mapping


class FilledRetort(OperatingRetort, ABC):
    """A retort contains builtin providers"""

    recipe = [
        NoneProvider(),

        as_is_loader(Any),
        as_is_dumper(Any),

        IsoFormatProvider(datetime),
        IsoFormatProvider(date),
        IsoFormatProvider(time),
        SecondsTimedeltaProvider(),

        EnumExactValueProvider(),  # it has higher priority than int for IntEnum

        CoercionLimiter(loader(int, int), [int]),
        as_is_dumper(int),

        CoercionLimiter(loader(float, float), [float, int]),
        as_is_dumper(float),

        CoercionLimiter(loader(str, str), [str]),
        as_is_dumper(str),

        CoercionLimiter(loader(bool, bool), [bool]),
        as_is_dumper(bool),

        CoercionLimiter(loader(Decimal, Decimal), [str, Decimal]),
        dumper(Decimal, Decimal.__str__),
        CoercionLimiter(loader(Fraction, Fraction), [str, Fraction]),
        dumper(Fraction, Fraction.__str__),
        CoercionLimiter(loader(complex, complex), [str, complex]),
        dumper(complex, complex.__str__),

        BytesBase64Provider(),
        BytearrayBase64Provider(),

        *chain.from_iterable(
            (
                loader(tp, tp),
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

        name_mapping(
            chain=None,
            skip=(),
            only_mapped=False,
            only=None,
            map={},
            trim_trailing_underscore=True,
            name_style=None,
            omit_default=True,
            extra_in=ExtraSkip(),
            extra_out=ExtraSkip(),
        ),
        BuiltinNameLayoutProvider(
            structure_maker=BuiltinStructureMaker(),
            sieves_maker=BuiltinSievesMaker(),
            extra_move_maker=BuiltinExtraMoveAndPoliciesMaker(),
            extra_policies_maker=BuiltinExtraMoveAndPoliciesMaker(),
        ),
        ModelLoaderProvider(NameSanitizer(), BuiltinInputExtractionMaker(), make_input_creation),
        ModelDumperProvider(NameSanitizer(), make_output_extraction, BuiltinOutputCreationMaker()),

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
AR = TypeVar('AR', bound='AdornedRetort')


class AdornedRetort(OperatingRetort):
    """A retort implementing high-level user interface"""

    def __init__(
        self,
        *,
        recipe: Optional[Iterable[Provider]] = None,
        strict_coercion: bool = True,
        debug_path: bool = True,
    ):
        self._strict_coercion = strict_coercion
        self._debug_path = debug_path
        super().__init__(recipe)

    def _calculate_derived(self):
        super()._calculate_derived()
        self._loader_cache = {}
        self._dumper_cache = {}

    def replace(
        self: AR,
        *,
        strict_coercion: Optional[bool] = None,
        debug_path: Optional[bool] = None,
    ) -> AR:
        # pylint: disable=protected-access
        with self._clone() as clone:
            if strict_coercion is not None:
                clone._strict_coercion = strict_coercion

            if debug_path is not None:
                clone._debug_path = debug_path

        return clone

    def extend(self: AR, *, recipe: Iterable[Provider]) -> AR:
        # pylint: disable=protected-access
        with self._clone() as clone:
            clone._inc_instance_recipe = (
                tuple(recipe) + clone._inc_instance_recipe
            )

        return clone

    def _get_config_recipe(self) -> VarTuple[Provider]:
        return ()

    def get_loader(self, tp: Type[T]) -> Loader[T]:
        try:
            return self._loader_cache[tp]
        except KeyError:
            pass
        loader_ = self._facade_provide(
            LoaderRequest(
                loc=TypeHintLocation(tp),
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
            pass
        dumper_ = self._facade_provide(
            DumperRequest(
                loc=TypeHintLocation(tp),
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
