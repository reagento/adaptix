import re
from enum import Enum, EnumMeta
from types import MappingProxyType
from typing import Any, Callable, Iterable, Mapping, Optional, Sequence, Type, TypeVar, Union, overload

from dataclass_factory_30.provider.overlay import OverlayProvider

from ..common import Catchable, Dumper, Loader, TypeHint
from ..model_tools import Default, DescriptorAccessor, NoDefault, OutputField, get_func_figure
from ..provider import (
    BoundingProvider,
    Chain,
    ChainingProvider,
    DumperRequest,
    EnumExactValueProvider,
    EnumNameProvider,
    EnumValueProvider,
    InputFigureRequest,
    LoaderRequest,
    LoadError,
    NameStyle,
    OrRequestChecker,
    PropertyAdder,
    Provider,
    ValidationError,
    ValueProvider,
    create_req_checker,
)
from ..provider.name_layout.base import ExtraIn, ExtraOut
from ..provider.name_layout.component import (
    ExtraMoveAndPoliciesOverlay,
    NameMap,
    NameMapStack,
    SievesOverlay,
    StructureOverlay,
)
from ..utils import Omittable, Omitted
from .utils import resolve_pred_value_chain

T = TypeVar('T')


def bound(pred: Any, provider: Provider, /) -> Provider:
    if pred == Omitted():
        return provider
    return BoundingProvider(create_req_checker(pred), provider)


def make_chain(chain: Optional[Chain], provider: Provider, /) -> Provider:
    if chain is None:
        return provider

    return ChainingProvider(chain, provider)


@overload
def loader(pred: Type[T], func: Loader[T], chain: Optional[Chain] = None, /) -> Provider:
    ...


@overload
def loader(pred: Any, func: Loader, chain: Optional[Chain] = None, /) -> Provider:
    ...


@overload
def loader(type_or_class_method: Union[type, Loader], chain: Optional[Chain] = None, /) -> Provider:
    ...


def loader(func_or_pred, func_or_chain=None, maybe_chain=None):
    pred, func, chain = resolve_pred_value_chain(func_or_pred, func_or_chain, maybe_chain)
    return bound(
        pred,
        make_chain(
            chain,
            ValueProvider(LoaderRequest, func)
        )
    )


@overload
def dumper(pred: Type[T], func: Dumper[T], chain: Optional[Chain] = None, /) -> Provider:
    ...


@overload
def dumper(pred: Any, func: Dumper, chain: Optional[Chain] = None, /) -> Provider:
    ...


# We can not extract origin class from method
# because at class level it is a simple function.
# There is rare case when method is WrapperDescriptorType,
# nevertheless one arg signature was removed
def dumper(pred, func, chain=None):
    return bound(
        pred,
        make_chain(
            chain,
            ValueProvider(DumperRequest, func),
        ),
    )


def as_is_loader(pred: Any) -> Provider:
    return loader(pred, lambda x: x)


def as_is_dumper(pred: Any) -> Provider:
    return dumper(pred, lambda x: x)


@overload
def constructor(pred: Type[T], func: Callable[..., T], /) -> Provider:
    ...


@overload
def constructor(pred: Any, func: Callable, /) -> Provider:
    ...


@overload
def constructor(type_or_class_method: Callable, /) -> Provider:
    ...


def constructor(func_or_pred, opt_func=None):
    pred, func, _ = resolve_pred_value_chain(func_or_pred, opt_func, None)

    return bound(
        pred,
        ValueProvider(
            InputFigureRequest,
            get_func_figure(
                func,
                slice(0 if opt_func else 1, None),
            )
        ),
    )


def _convert_name_map_to_stack(name_map: NameMap) -> NameMapStack:
    return tuple((re.compile(pattern), tuple(path)) for pattern, path in name_map.items())


def name_mapping(
    pred: Any = Omitted(),
    /, *,
    # filtering which fields are presented
    skip: Omittable[Iterable[str]] = Omitted(),
    only: Omittable[Optional[Iterable[str]]] = Omitted(),
    only_mapped: Omittable[bool] = Omitted(),
    # mutating names of presented fields
    map: Omittable[NameMap] = Omitted(),  # noqa: A002
    trim_trailing_underscore: Omittable[bool] = Omitted(),
    name_style: Omittable[Optional[NameStyle]] = Omitted(),
    # filtering of dumped data
    omit_default: Omittable[bool] = Omitted(),
    # policy for data that does not map to fields
    extra_in: Omittable[ExtraIn] = Omitted(),
    extra_out: Omittable[ExtraOut] = Omitted(),
    # chaining
    chain: Optional[Chain] = Chain.FIRST,
) -> Provider:
    """A name mapping decides which fields will be presented
    to the outside world and how they will look.

    The mapping process consists of two stages:
    1. Determining which fields are presented
    2. Mutating names of presented fields

    Parameters that are responsible for
    filtering of available have such priority
    1. skip
    2. only | only_mapped
    3. skip_internal

    Fields selected by only and only_mapped are unified.
    Rules with higher priority overlap other rules.

    Mutating parameters works in that way:
    Mapper tries to use the value from the map.
    If the field is not presented in the map,
    trim trailing underscore and convert name style.

    The field must follow snake_case to could be converted.

    If you try to skip required input field,
    class will raise error
    """
    return bound(
        pred,
        OverlayProvider(
            overlays=[
                StructureOverlay(
                    skip=skip,
                    only=only,
                    only_mapped=only_mapped,
                    map=Omitted() if isinstance(map, Omitted) else _convert_name_map_to_stack(map),
                    trim_trailing_underscore=trim_trailing_underscore,
                    name_style=name_style,
                ),
                SievesOverlay(
                    omit_default=omit_default,
                ),
                ExtraMoveAndPoliciesOverlay(
                    extra_in=extra_in,
                    extra_out=extra_out,
                ),
            ],
            chain=chain,
        )
    )


NameOrProp = Union[str, property]


def add_property(
    pred: Any,
    prop: NameOrProp,
    tp: Omittable[TypeHint] = Omitted(),
    /, *,
    default: Default = NoDefault(),
    access_error: Optional[Catchable] = None,
    metadata: Mapping[Any, Any] = MappingProxyType({}),
) -> Provider:
    attr_name = _ensure_attr_name(prop)

    field = OutputField(
        name=attr_name,
        type=tp,
        accessor=DescriptorAccessor(attr_name, access_error),
        default=default,
        metadata=metadata,
    )

    return bound(
        pred,
        PropertyAdder(
            output_fields=[field],
            infer_types_for=[field.name] if tp == Omitted() else [],
        )
    )


def _ensure_attr_name(prop: NameOrProp) -> str:
    if isinstance(prop, str):
        return prop

    fget = prop.fget
    if fget is None:
        raise ValueError(f"Property {prop} has no fget")

    return fget.__name__


EnumPred = Union[TypeHint, str, EnumMeta]


def _wrap_enum_provider(preds: Sequence[EnumPred], provider: Provider) -> Provider:
    if len(preds) == 0:
        return provider

    if Enum in preds:
        raise ValueError(f"Can not apply enum rules to {Enum}")

    return BoundingProvider(
        OrRequestChecker([create_req_checker(pred) for pred in preds]),
        provider,
    )


def enum_by_name(*preds: EnumPred) -> Provider:
    return _wrap_enum_provider(preds, EnumNameProvider())


def enum_by_exact_value(*preds: EnumPred) -> Provider:
    return _wrap_enum_provider(preds, EnumExactValueProvider())


def enum_by_value(first_pred: EnumPred, /, *preds: EnumPred, tp: TypeHint) -> Provider:
    return _wrap_enum_provider([first_pred, *preds], EnumValueProvider(tp))


@overload
def validator(
    pred: Any,
    function: Callable[[Any], bool],
    error: Union[str, Callable[[Any], LoadError], None] = None,
    chain: Chain = Chain.LAST,
    /,
) -> Provider:
    ...


@overload
def validator(
    pred: Any,
    function: Callable[[Any], bool],
    chain: Chain,
    /,
) -> Provider:
    ...


def validator(
    pred: Any,
    function: Callable[[Any], bool],
    error_or_chain: Union[str, Callable[[Any], LoadError], None, Chain] = None,
    chain: Optional[Chain] = None,
    /,
) -> Provider:
    if isinstance(error_or_chain, Chain):
        if chain is None:
            raise ValueError
        error = None
        p_chain = error_or_chain
    elif chain is None:
        error = error_or_chain
        p_chain = Chain.LAST
    else:
        error = error_or_chain
        p_chain = chain

    # pylint: disable=C3001
    exception_factory = (
        lambda x: ValidationError(error)
        if error is None or isinstance(error, str) else
        error
    )

    def validating_loader(data):
        if function(data):
            return data
        raise exception_factory(data)

    return loader(pred, validating_loader, p_chain)
