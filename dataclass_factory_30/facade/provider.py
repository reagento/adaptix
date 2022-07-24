from enum import Enum, EnumMeta
from types import MappingProxyType
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence, Type, TypeVar, Union, overload

from ..common import Catchable, Parser, Serializer, TypeHint
from ..model_tools import Default, NoDefault, OutputField, PropertyAccessor, get_func_input_figure
from ..provider import (
    BoundingProvider,
    EnumExactValueProvider,
    EnumNameProvider,
    EnumValueProvider,
    InputFigureRequest,
    NameMapper,
    NameStyle,
    OrRequestChecker,
    ParserRequest,
    PropertyAdder,
    Provider,
    SerializerRequest,
    ValueProvider,
    create_req_checker,
    foreign_parser,
)
from .utils import resolve_pred_and_value

T = TypeVar('T')
_OMITTED = object()


def bound(pred: Any, provider: Provider, /) -> Provider:
    return BoundingProvider(create_req_checker(pred), provider)


@overload
def parser(pred: Type[T], func: Parser[T], /) -> Provider:
    pass


@overload
def parser(pred: Any, func: Parser, /) -> Provider:
    pass


@overload
def parser(type_or_class_method: Union[type, Parser], /) -> Provider:
    pass


def parser(func_or_pred, func=None):
    pred, func = resolve_pred_and_value(func_or_pred, func)
    return bound(
        pred,
        ValueProvider(ParserRequest, foreign_parser(func))
    )


@overload
def serializer(pred: Type[T], func: Serializer[T], /) -> Provider:
    pass


@overload
def serializer(pred: Any, func: Serializer, /) -> Provider:
    pass


# We can not extract origin class from method
# because at class level it is a simple function.
# There is rare case when method is WrapperDescriptorType,
# nevertheless one arg signature was removed
def serializer(pred, func):
    return bound(
        pred,
        ValueProvider(SerializerRequest, func)
    )


@overload
def constructor(pred: Type[T], func: Callable[..., T], /) -> Provider:
    pass


@overload
def constructor(pred: Any, func: Callable, /) -> Provider:
    pass


@overload
def constructor(type_or_class_method: Callable, /) -> Provider:
    pass


def constructor(func_or_pred, func=None):
    pred, func = resolve_pred_and_value(func_or_pred, func)

    return bound(
        pred,
        ValueProvider(
            InputFigureRequest,
            get_func_input_figure(func, slice(1, None))
        )
    )


def name_mapping(
    pred: Any,
    /,
    *,
    skip: Optional[List[str]] = None,
    only_mapped: bool = False,
    only: Optional[List[str]] = None,
    skip_internal: bool = True,
    map: Optional[Dict[str, str]] = None,  # noqa: A002
    trim_trailing_underscore: bool = True,
    name_style: Optional[NameStyle] = None,
    omit_default: bool = True,
) -> Provider:
    opt_mut_params = {
        k: v for k, v in {'skip': skip, 'map': map}.items()
        if v is not None
    }

    return bound(
        pred,
        NameMapper(
            only_mapped=only_mapped,
            only=only,
            skip_internal=skip_internal,
            trim_trailing_underscore=trim_trailing_underscore,
            name_style=name_style,
            omit_default=omit_default,
            **opt_mut_params,  # type: ignore[arg-type]
        )
    )


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
):
    pass


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
):
    pass


def add_property(
    pred: Any,
    prop: NameOrProp,
    tp: TypeHint = _OMITTED,
    /,
    *,
    default: Default = NoDefault(),
    access_error: Optional[Catchable] = None,
    metadata: Mapping[Any, Any] = MappingProxyType({}),
):
    attr_name = _ensure_attr_name(prop)

    field = OutputField(
        name=attr_name,
        type=tp,
        accessor=PropertyAccessor(attr_name, access_error),
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


def _wrap_enum_provider(preds: Sequence[EnumPred], provider: Provider):
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
