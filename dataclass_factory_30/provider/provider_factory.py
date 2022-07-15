from types import BuiltinMethodType, MappingProxyType, MethodType, WrapperDescriptorType
from typing import Any, Callable, Mapping, Optional, Tuple, Type, TypeVar, Union, overload

from ..common import Catchable, Parser, Serializer, TypeHint
from ..model_tools import Default, NoDefault, OutputField, PropertyAccessor, get_func_input_figure
from .essential import Provider
from .model import InputFigureRequest
from .model.figure_provider import PropertyAdder
from .provider_basics import BoundingProvider, ValueProvider, create_req_checker, foreign_parser
from .request_cls import ParserRequest, SerializerRequest

T = TypeVar('T')


def bound(pred: Any, provider: Provider) -> Provider:
    return BoundingProvider(create_req_checker(pred), provider)


def resolve_classmethod(func) -> Tuple[type, Callable]:
    if isinstance(func, (MethodType, BuiltinMethodType)):
        bound = func.__self__
    elif isinstance(func, WrapperDescriptorType):
        bound = func.__objclass__
    else:
        raise ValueError

    if not isinstance(bound, type):
        raise ValueError

    return bound, func


def _resolve_pred_and_value(value_or_pred, value_or_none) -> Tuple[Any, Any]:
    value: Any
    if value_or_none is None:
        if isinstance(value_or_pred, type):
            pred = value_or_pred
            value = value_or_pred
        else:
            pred, value = resolve_classmethod(value_or_pred)
    else:
        pred = value_or_pred
        value = value_or_none

    return pred, value


@overload
def as_parser(func_or_pred: Type[T], func: Parser[T]) -> Provider:
    pass


@overload
def as_parser(func_or_pred: Any, func: Parser) -> Provider:
    pass


@overload
def as_parser(func_or_pred: Union[type, Parser]) -> Provider:
    pass


def as_parser(func_or_pred, func=None):
    pred, func = _resolve_pred_and_value(func_or_pred, func)
    return bound(
        pred,
        ValueProvider(ParserRequest, foreign_parser(func))
    )


@overload
def as_serializer(pred: Type[T], func: Serializer[T]) -> Provider:
    pass


@overload
def as_serializer(pred: Any, func: Serializer) -> Provider:
    pass


# We can not extract origin class from method
# because at class level it is a simple function.
# There is rare case when method is WrapperDescriptorType,
# nevertheless one arg signature was removed
def as_serializer(pred, func):
    return BoundingProvider(
        create_req_checker(pred),
        ValueProvider(
            SerializerRequest,
            func
        )
    )


@overload
def as_constructor(func_or_pred: Type[T], constructor: Callable[..., T]) -> Provider:
    pass


@overload
def as_constructor(func_or_pred: Any, constructor: Callable) -> Provider:
    pass


@overload
def as_constructor(func_or_pred: Callable) -> Provider:
    pass


def as_constructor(func_or_pred, constructor=None):
    pred, func = _resolve_pred_and_value(func_or_pred, constructor)
    return bound(
        pred,
        ValueProvider(
            InputFigureRequest,
            get_func_input_figure(func, slice(1, None))
        )
    )


NameOrProp = Union[str, property]

_OMITTED = object()


@overload
def add_property(
    pred: Any,
    prop: NameOrProp,
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
