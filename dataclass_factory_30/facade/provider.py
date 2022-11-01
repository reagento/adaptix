from enum import Enum, EnumMeta
from types import MappingProxyType
from typing import Any, Callable, Dict, Iterable, Mapping, Optional, Sequence, Type, TypeVar, Union, overload

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
    ExtraIn,
    ExtraOut,
    InputFigureRequest,
    LoaderRequest,
    LoadError,
    NameMapper,
    NameStyle,
    OrRequestChecker,
    PropertyAdder,
    Provider,
    ValidationError,
    ValueProvider,
    create_req_checker,
)
from ..provider.model import ExtraSkip
from .utils import resolve_pred_value_chain

T = TypeVar('T')
_OMITTED = object()


def bound(pred: Any, provider: Provider, /) -> Provider:
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


def name_mapping(
    pred: Any = _OMITTED,
    /,
    *,
    skip: Optional[Iterable[str]] = None,
    only_mapped: bool = False,
    only: Optional[Iterable[str]] = None,
    skip_internal: bool = True,
    map: Optional[Dict[str, str]] = None,  # noqa: A002
    trim_trailing_underscore: bool = True,
    name_style: Optional[NameStyle] = None,
    omit_default: bool = True,
    extra_in: ExtraIn = ExtraSkip(),
    extra_out: ExtraOut = ExtraSkip(),
) -> Provider:
    opt_mut_params: Dict[str, Any] = {}
    if skip is not None:
        opt_mut_params['skip'] = list(skip)
    if map is not None:
        opt_mut_params['map'] = map

    name_mapper = NameMapper(
        only_mapped=only_mapped,
        only=None if only is None else list(only),
        skip_internal=skip_internal,
        trim_trailing_underscore=trim_trailing_underscore,
        name_style=name_style,
        omit_default=omit_default,
        extra_in=extra_in,
        extra_out=extra_out,
        **opt_mut_params,  # type: ignore[arg-type]
    )

    return name_mapper if pred is _OMITTED else bound(pred, name_mapper)


NameOrProp = Union[str, property]


@overload
def add_property(
    pred: Any,
    prop: NameOrProp,
    /,
    *,
    default: Default = NoDefault(),
    access_error: Optional[Catchable] = None,
    metadata: Mapping[Any, Any] = MappingProxyType({}),
) -> Provider:
    ...


@overload
def add_property(
    pred: Any,
    prop: NameOrProp,
    tp: TypeHint,
    /,
    *,
    default: Default = NoDefault(),
    access_error: Optional[Catchable] = None,
    metadata: Mapping[Any, Any] = MappingProxyType({}),
) -> Provider:
    ...


def add_property(
    pred: Any,
    prop: NameOrProp,
    tp: TypeHint = _OMITTED,
    /,
    *,
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
            infer_types_for=[field.name] if tp is _OMITTED else [],
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
    error_func = (
        lambda x: ValidationError(error)
        if error is None or isinstance(error, str) else
        error
    )

    def validating_loader(data):
        if function(data):
            return data
        raise error_func(data)

    return loader(pred, validating_loader, p_chain)
