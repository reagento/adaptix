from abc import ABC
from datetime import date, datetime, time
from decimal import Decimal
from fractions import Fraction
from ipaddress import IPv4Address, IPv4Interface, IPv4Network, IPv6Address, IPv6Interface, IPv6Network
from itertools import chain
from pathlib import Path, PosixPath, PurePath, PurePosixPath, PureWindowsPath, WindowsPath
from typing import Any, ByteString, Iterable, Mapping, MutableMapping, Optional, Type, TypeVar, overload
from uuid import UUID

from ..common import Dumper, Loader, TypeHint, VarTuple
from ..essential import Provider, Request
from ..provider.concrete_provider import (
    BOOL_LOADER_PROVIDER,
    COMPLEX_LOADER_PROVIDER,
    DECIMAL_LOADER_PROVIDER,
    FLOAT_LOADER_PROVIDER,
    FRACTION_LOADER_PROVIDER,
    INT_LOADER_PROVIDER,
    STR_LOADER_PROVIDER,
    BytearrayBase64Provider,
    BytesBase64Provider,
    IsoFormatProvider,
    NoneProvider,
    RegexPatternProvider,
    SecondsTimedeltaProvider,
)
from ..provider.enum_provider import EnumExactValueProvider
from ..provider.generic_provider import (
    DictProvider,
    IterableProvider,
    LiteralProvider,
    NewTypeUnwrappingProvider,
    TypeHintTagsUnwrappingProvider,
    UnionProvider,
)
from ..provider.model.basic_gen import NameSanitizer
from ..provider.model.crown_definitions import ExtraSkip
from ..provider.model.dumper_provider import BuiltinOutputCreationMaker, ModelDumperProvider, make_output_extraction
from ..provider.model.loader_provider import BuiltinInputExtractionMaker, ModelLoaderProvider, make_input_creation
from ..provider.model.shape_provider import (
    ATTRS_SHAPE_PROVIDER,
    CLASS_INIT_SHAPE_PROVIDER,
    DATACLASS_SHAPE_PROVIDER,
    NAMED_TUPLE_SHAPE_PROVIDER,
    TYPED_DICT_SHAPE_PROVIDER,
)
from ..provider.name_layout.component import BuiltinExtraMoveAndPoliciesMaker, BuiltinSievesMaker, BuiltinStructureMaker
from ..provider.name_layout.provider import BuiltinNameLayoutProvider
from ..provider.provider_template import ABCProxy, ValueProvider
from ..provider.request_cls import (
    DebugPathRequest,
    DumperRequest,
    LoaderRequest,
    LocMap,
    StrictCoercionRequest,
    TypeHintLoc,
)
from ..provider.request_filtering import AnyRequestChecker
from ..retort import OperatingRetort
from ..type_tools.basic_utils import is_generic_class
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

        EnumExactValueProvider(),  # it has higher priority than scalar types for Enum with mixins

        INT_LOADER_PROVIDER,
        as_is_dumper(int),

        FLOAT_LOADER_PROVIDER,
        as_is_dumper(float),

        STR_LOADER_PROVIDER,
        as_is_dumper(str),

        BOOL_LOADER_PROVIDER,
        as_is_dumper(bool),

        DECIMAL_LOADER_PROVIDER,
        dumper(Decimal, Decimal.__str__),

        FRACTION_LOADER_PROVIDER,
        dumper(Fraction, Fraction.__str__),

        COMPLEX_LOADER_PROVIDER,
        dumper(complex, complex.__str__),

        BytesBase64Provider(),
        BytearrayBase64Provider(),

        *chain.from_iterable(
            (
                loader(tp, tp),
                dumper(tp, tp.__str__),  # type: ignore[arg-type]
            )
            for tp in [
                UUID,
                PurePath, Path,
                PurePosixPath, PosixPath,
                PureWindowsPath, WindowsPath,
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
            only=AnyRequestChecker(),
            map={},
            trim_trailing_underscore=True,
            name_style=None,
            as_list=False,
            omit_default=False,
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

        NAMED_TUPLE_SHAPE_PROVIDER,
        TYPED_DICT_SHAPE_PROVIDER,
        DATACLASS_SHAPE_PROVIDER,
        CLASS_INIT_SHAPE_PROVIDER,
        ATTRS_SHAPE_PROVIDER,

        NewTypeUnwrappingProvider(),
        TypeHintTagsUnwrappingProvider(),
    ]


T = TypeVar('T')
RequestT = TypeVar('RequestT', bound=Request)
AR = TypeVar('AR', bound='AdornedRetort')


class AdornedRetort(OperatingRetort):
    """A retort implementing high-level user interface"""

    def __init__(
        self,
        *,
        recipe: Iterable[Provider] = (),
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
        return (
            ValueProvider(StrictCoercionRequest, self._strict_coercion),
            ValueProvider(DebugPathRequest, self._debug_path),
        )

    def get_loader(self, tp: Type[T]) -> Loader[T]:
        try:
            return self._loader_cache[tp]
        except KeyError:
            pass
        loader_ = self._facade_provide(
            LoaderRequest(loc_map=LocMap(TypeHintLoc(type=tp)))
        )
        self._loader_cache[tp] = loader_
        return loader_

    def get_dumper(self, tp: Type[T]) -> Dumper[T]:
        try:
            return self._dumper_cache[tp]
        except KeyError:
            pass
        dumper_ = self._facade_provide(
            DumperRequest(loc_map=LocMap(TypeHintLoc(type=tp)))
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
            if is_generic_class(tp):
                raise ValueError(
                    'Can not infer the actual type of generic class instance,'
                    ' you have to explicitly pass the type of object'
                )
        return self.get_dumper(tp)(data)


class Retort(FilledRetort, AdornedRetort):
    pass
