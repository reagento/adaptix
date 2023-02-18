import inspect
import warnings
from dataclasses import MISSING as DC_MISSING, Field as DCField, fields as dc_fields, is_dataclass, replace
from inspect import Parameter, Signature
from types import MappingProxyType
from typing import Any, Dict, Iterable

from ..common import TypeHint
from ..feature_requirement import HAS_ATTRS_PKG, HAS_PY_39
from ..model_tools.definitions import (
    AttrAccessor,
    BaseField,
    Default,
    DefaultFactory,
    DefaultValue,
    Figure,
    FullFigure,
    InputField,
    InputFigure,
    IntrospectionImpossible,
    ItemAccessor,
    NoDefault,
    NoTargetPackage,
    OutputField,
    OutputFigure,
    ParamKind,
    ParamKwargs,
)
from ..type_tools import get_all_type_hints, is_named_tuple_class, is_typed_dict_class

try:
    import attrs
except ImportError:
    attrs = None  # type: ignore[assignment]


# ======================
#       Function
# ======================

_PARAM_KIND_CONV: Dict[Any, ParamKind] = {
    Parameter.POSITIONAL_ONLY: ParamKind.POS_ONLY,
    Parameter.POSITIONAL_OR_KEYWORD: ParamKind.POS_OR_KW,
    Parameter.KEYWORD_ONLY: ParamKind.KW_ONLY,
}


def _is_empty(value):
    return value is Signature.empty


def get_callable_figure(func, params_slice=slice(0, None)) -> Figure[InputFigure, None]:
    try:
        signature = inspect.signature(func)
    except TypeError:
        raise IntrospectionImpossible

    params = list(signature.parameters.values())[params_slice]
    kinds = [p.kind for p in params]

    if Parameter.VAR_POSITIONAL in kinds:
        raise IntrospectionImpossible(
            f'Can not create InputFigure'
            f' from the function that has {Parameter.VAR_POSITIONAL}'
            f' parameter'
        )

    param_kwargs = next(
        (
            ParamKwargs(Any if _is_empty(param.annotation) else param.annotation)
            for param in params if param.kind == Parameter.VAR_KEYWORD
        ),
        None,
    )

    type_hints = get_all_type_hints(func)

    return Figure(
        input=InputFigure(
            constructor=func,
            fields=tuple(
                InputField(
                    type=type_hints.get(param.name, Any),
                    name=param.name,
                    is_required=_is_empty(param.default) or param.kind == Parameter.POSITIONAL_ONLY,
                    default=NoDefault() if _is_empty(param.default) else DefaultValue(param.default),
                    metadata=MappingProxyType({}),
                    param_kind=_PARAM_KIND_CONV[param.kind],
                    param_name=param.name,
                )
                for param in params
                if param.kind != Parameter.VAR_KEYWORD
            ),
            kwargs=param_kwargs,
        ),
        output=None,
    )


# ======================
#       NamedTuple
# ======================

def get_named_tuple_figure(tp) -> FullFigure:
    # pylint: disable=protected-access
    if not is_named_tuple_class(tp):
        raise IntrospectionImpossible

    type_hints = get_all_type_hints(tp)

    # noinspection PyProtectedMember
    input_figure = InputFigure(
        constructor=tp,
        kwargs=None,
        fields=tuple(
            InputField(
                name=field_name,
                type=type_hints.get(field_name, Any),
                default=(
                    DefaultValue(tp._field_defaults[field_name])
                    if field_name in tp._field_defaults else
                    NoDefault()
                ),
                is_required=field_name not in tp._field_defaults,
                param_name=field_name,
                metadata=MappingProxyType({}),
                param_kind=ParamKind.POS_OR_KW,
            )
            for field_name in tp._fields
        )
    )

    return Figure(
        input=input_figure,
        output=OutputFigure(
            fields=tuple(
                OutputField(
                    name=fld.name,
                    type=fld.type,
                    default=fld.default,
                    metadata=fld.metadata,
                    accessor=AttrAccessor(attr_name=fld.name, is_required=True),
                )
                for fld in input_figure.fields
            ),
        )
    )


# =====================
#       TypedDict
# =====================


class TypedDictAt38Warning(UserWarning):
    def __str__(self):
        return (
            "Runtime introspection of TypedDict at python3.8 does not support inheritance."
            " Please, update python or consider limitations suppressing this warning"
        )


if HAS_PY_39:
    def _td_make_requirement_determinant(tp):
        required_fields = tp.__required_keys__
        return lambda name: name in required_fields
else:
    def _td_make_requirement_determinant(tp):
        warnings.warn(TypedDictAt38Warning(), stacklevel=3)
        is_total = tp.__total__
        return lambda name: is_total


def _get_td_hints(tp):
    elements = list(get_all_type_hints(tp).items())
    elements.sort(key=lambda v: v[0])
    return elements


def get_typed_dict_figure(tp) -> FullFigure:
    if not is_typed_dict_class(tp):
        raise IntrospectionImpossible

    requirement_determinant = _td_make_requirement_determinant(tp)

    return Figure(
        input=InputFigure(
            constructor=tp,
            fields=tuple(
                InputField(
                    type=tp,
                    name=name,
                    default=NoDefault(),
                    is_required=requirement_determinant(name),
                    metadata=MappingProxyType({}),
                    param_kind=ParamKind.KW_ONLY,
                    param_name=name,
                )
                for name, tp in _get_td_hints(tp)
            ),
            kwargs=None,
        ),
        output=OutputFigure(
            fields=tuple(
                OutputField(
                    type=tp,
                    name=name,
                    default=NoDefault(),
                    accessor=ItemAccessor(name, requirement_determinant(name)),
                    metadata=MappingProxyType({}),
                )
                for name, tp in _get_td_hints(tp)
            ),
        ),
    )


# ======================
#       Dataclass
# ======================

def all_dc_fields(cls) -> Dict[str, DCField]:
    """Builtin introspection function hides
    some fields like InitVar or ClassVar.
    That function return full dict
    """
    return cls.__dataclass_fields__


def get_dc_default(field: DCField) -> Default:
    if field.default is not DC_MISSING:
        return DefaultValue(field.default)
    if field.default_factory is not DC_MISSING:
        return DefaultFactory(field.default_factory)
    return NoDefault()


def create_inp_field_from_dc_fields(dc_field: DCField, type_hints):
    default = get_dc_default(dc_field)
    return InputField(
        type=type_hints[dc_field.name],
        name=dc_field.name,
        default=default,
        is_required=default == NoDefault(),
        metadata=dc_field.metadata,
        param_kind=ParamKind.POS_OR_KW,
        param_name=dc_field.name,
    )


def get_dataclass_figure(tp) -> FullFigure:
    """This function does not work properly if __init__ signature differs from
    that would be created by dataclass decorator.

    It happens because we can not distinguish __init__ that generated
    by @dataclass and __init__ that created by other ways.
    And we can not analyze only __init__ signature
    because @dataclass uses private constant
    as default value for fields with default_factory
    """

    if not is_dataclass(tp):
        raise IntrospectionImpossible

    name_to_dc_field = all_dc_fields(tp)

    init_params = list(
        inspect.signature(tp.__init__).parameters.keys()
    )[1:]

    type_hints = get_all_type_hints(tp)

    return Figure(
        input=InputFigure(
            constructor=tp,
            fields=tuple(
                create_inp_field_from_dc_fields(name_to_dc_field[field_name], type_hints)
                for field_name in init_params
            ),
            kwargs=None,
        ),
        output=OutputFigure(
            fields=tuple(
                OutputField(
                    type=type_hints[field.name],
                    name=field.name,
                    default=get_dc_default(name_to_dc_field[field.name]),
                    accessor=AttrAccessor(field.name, True),
                    metadata=field.metadata,
                )
                for field in dc_fields(tp)
            ),
        )
    )


# ======================
#       ClassInit
# ======================

def get_class_init_figure(tp) -> Figure[InputFigure, None]:
    if not isinstance(tp, type):
        raise IntrospectionImpossible

    figure = get_callable_figure(
        tp.__init__,  # type: ignore[misc]
        slice(1, None)
    )

    return replace(
        figure,
        input=replace(
            figure.input,
            constructor=tp,
        )
    )

# =================
#       Attrs
# =================


def _get_attrs_default(field) -> Default:
    default: Any = field.default

    if isinstance(default, attrs.Factory):  # type: ignore
        if default.takes_self:  # type: ignore
            # TODO: add support
            raise ValueError("Factory with self parameter does not supported yet")
        return DefaultFactory(default.factory)  # type: ignore

    if default is attrs.NOTHING:
        return NoDefault()

    return DefaultValue(default)


def _get_attrs_field_type(field, type_hints):
    try:
        return type_hints[field.name]
    except KeyError:
        return Any if field.type is None else field.type


def _get_attrs_fields(tp, type_hints: Dict[str, TypeHint]) -> Iterable[BaseField]:
    try:
        fields_iterator = attrs.fields(tp)
    except (TypeError, attrs.exceptions.NotAnAttrsClassError):
        raise IntrospectionImpossible

    return [
        BaseField(
            # if field is not annotated, type attribute will store None value
            type=_get_attrs_field_type(field, type_hints),
            default=_get_attrs_default(field),
            metadata=field.metadata,
            name=field.name,
        )
        for field in fields_iterator
    ]


NoneType = type(None)


def _process_attr_input_field(field: InputField, base_fields_dict: Dict[str, BaseField], has_custom_init: bool):
    try:
        base_field = base_fields_dict[field.name]
    except KeyError:
        return field

    # When input figure is generating we rely on __init__ signature,
    # but when field type is None attrs thinks that there is no type hint,
    # so if there is no custom __init__ (that can do not set type for this attribute),
    # we should use NoneType as type of field
    if not has_custom_init and field.type == Any and base_field.type == NoneType:
        field = replace(field, type=NoneType)

    return replace(
        field,
        default=(
            base_field.default
            if isinstance(field.default, DefaultValue) and field.default.value is attrs.NOTHING else
            field.default
        ),
        metadata=base_field.metadata,
        name=base_field.name,
    )


def _get_attr_param_name(field):
    return (
        field.name[1:]
        if field.name.startswith("_") and not field.name.startswith("__") else
        field.name
    )


def get_attrs_figure(tp) -> FullFigure:
    if not HAS_ATTRS_PKG:
        raise NoTargetPackage

    try:
        is_attrs = attrs.has(tp)
    except TypeError:
        raise IntrospectionImpossible
    if not is_attrs:
        raise IntrospectionImpossible

    type_hints = get_all_type_hints(tp)

    base_fields_dict = {
        _get_attr_param_name(field): field
        for field in _get_attrs_fields(tp, type_hints)
    }

    has_custom_init = hasattr(tp, '__attrs_init__')

    figure = get_class_init_figure(tp)

    input_figure = replace(
        figure.input,
        fields=tuple(
            _process_attr_input_field(field, base_fields_dict, has_custom_init)
            for field in figure.input.fields
        )
    )

    return Figure(
        input=input_figure,
        output=OutputFigure(
            fields=tuple(
                OutputField(
                    name=field.name,
                    type=_get_attrs_field_type(field, type_hints),
                    default=(
                        input_figure.fields_dict[field.name].default
                        if field.name in input_figure.fields_dict else
                        NoDefault()
                    ),
                    metadata=field.metadata,
                    accessor=AttrAccessor(field.name, is_required=True),
                )
                for field in _get_attrs_fields(tp, type_hints)
            ),
        ),
    )
