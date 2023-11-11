import inspect
import warnings
from dataclasses import MISSING as DC_MISSING, Field as DCField, fields as dc_fields, is_dataclass, replace
from inspect import Parameter, Signature
from types import MappingProxyType
from typing import Any, Dict

from ..feature_requirement import HAS_ATTRS_PKG, HAS_PY_39, HAS_PY_310
from ..model_tools.definitions import (
    BaseField,
    Default,
    DefaultFactory,
    DefaultFactoryWithSelf,
    DefaultValue,
    FullShape,
    InputField,
    InputShape,
    IntrospectionImpossible,
    NoDefault,
    NoTargetPackage,
    OutputField,
    OutputShape,
    Param,
    ParamKind,
    ParamKwargs,
    Shape,
    create_attr_accessor,
    create_key_accessor,
)
from ..type_tools import get_all_type_hints, is_named_tuple_class, is_typed_dict_class, normalize_type
from ..type_tools.norm_utils import is_class_var

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


def get_callable_shape(func, params_slice=slice(0, None)) -> Shape[InputShape, None]:
    try:
        signature = inspect.signature(func)
    except TypeError:
        raise IntrospectionImpossible

    params = list(signature.parameters.values())[params_slice]
    kinds = [p.kind for p in params]

    if Parameter.VAR_POSITIONAL in kinds:
        raise IntrospectionImpossible(
            f'Can not create InputShape'
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

    return Shape(
        input=InputShape(
            constructor=func,
            fields=tuple(
                InputField(
                    type=type_hints.get(param.name, Any),
                    id=param.name,
                    is_required=_is_empty(param.default) or param.kind == Parameter.POSITIONAL_ONLY,
                    default=NoDefault() if _is_empty(param.default) else DefaultValue(param.default),
                    metadata=MappingProxyType({}),
                    original=param,
                )
                for param in params
                if param.kind != Parameter.VAR_KEYWORD
            ),
            params=tuple(
                Param(
                    field_id=param.name,
                    kind=_PARAM_KIND_CONV[param.kind],
                    name=param.name,
                )
                for param in params
                if param.kind != Parameter.VAR_KEYWORD
            ),
            kwargs=param_kwargs,
            overriden_types=frozenset(
                param.name
                for param in params
                if param.kind != Parameter.VAR_KEYWORD
            ),
        ),
        output=None,
    )


# ======================
#       NamedTuple
# ======================

def get_named_tuple_shape(tp) -> FullShape:
    # pylint: disable=protected-access
    if not is_named_tuple_class(tp):
        raise IntrospectionImpossible

    type_hints = get_all_type_hints(tp)
    if tuple in tp.__bases__:
        overriden_types = frozenset(tp._fields)
    else:
        overriden_types = frozenset(tp.__annotations__.keys() & set(tp._fields))

    # noinspection PyProtectedMember
    input_shape = InputShape(
        constructor=tp,
        kwargs=None,
        fields=tuple(
            InputField(
                id=field_id,
                type=type_hints.get(field_id, Any),
                default=(
                    DefaultValue(tp._field_defaults[field_id])
                    if field_id in tp._field_defaults else
                    NoDefault()
                ),
                is_required=field_id not in tp._field_defaults,
                metadata=MappingProxyType({}),
                original=None,
            )
            for field_id in tp._fields
        ),
        params=tuple(
            Param(
                field_id=field_id,
                name=field_id,
                kind=ParamKind.POS_OR_KW,
            )
            for field_id in tp._fields
        ),
        overriden_types=overriden_types,
    )

    return Shape(
        input=input_shape,
        output=OutputShape(
            fields=tuple(
                OutputField(
                    id=fld.id,
                    type=fld.type,
                    default=fld.default,
                    metadata=fld.metadata,
                    accessor=create_key_accessor(
                        key=idx,
                        access_error=None,
                    ),
                    original=None,
                )
                for idx, fld in enumerate(input_shape.fields)
            ),
            overriden_types=overriden_types,
        ),
    )


# =====================
#       TypedDict
# =====================

class TypedDictAt38Warning(UserWarning):
    """Runtime introspection of TypedDict at python3.8 does not support inheritance.
    Please update python or consider limitations suppressing this warning
    """

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


def get_typed_dict_shape(tp) -> FullShape:
    # __annotations__ of TypedDict contain also parents' type hints unlike any other classes,
    # so overriden_types always is empty
    if not is_typed_dict_class(tp):
        raise IntrospectionImpossible

    requirement_determinant = _td_make_requirement_determinant(tp)
    type_hints = _get_td_hints(tp)
    return Shape(
        input=InputShape(
            constructor=tp,
            fields=tuple(
                InputField(
                    type=tp,
                    id=name,
                    default=NoDefault(),
                    is_required=requirement_determinant(name),
                    metadata=MappingProxyType({}),
                    original=None,
                )
                for name, tp in type_hints
            ),
            params=tuple(
                Param(
                    field_id=name,
                    name=name,
                    kind=ParamKind.KW_ONLY,
                )
                for name, tp in type_hints
            ),
            kwargs=None,
            overriden_types=frozenset({}),
        ),
        output=OutputShape(
            fields=tuple(
                OutputField(
                    type=tp,
                    id=name,
                    default=NoDefault(),
                    accessor=create_key_accessor(
                        key=name,
                        access_error=None if requirement_determinant(name) else KeyError,
                    ),
                    metadata=MappingProxyType({}),
                    original=None,
                )
                for name, tp in type_hints
            ),
            overriden_types=frozenset({}),
        ),
    )


# ======================
#       Dataclass
# ======================

def all_dc_fields(cls) -> Dict[str, DCField]:
    """Builtin introspection function hides
    some fields like InitVar or ClassVar.
    That function returns full dict
    """
    return cls.__dataclass_fields__


def get_dc_default(field: DCField) -> Default:
    if field.default is not DC_MISSING:
        return DefaultValue(field.default)
    if field.default_factory is not DC_MISSING:
        return DefaultFactory(field.default_factory)
    return NoDefault()


def _create_inp_field_from_dc_fields(dc_field: DCField, type_hints):
    default = get_dc_default(dc_field)
    return InputField(
        type=type_hints[dc_field.name],
        id=dc_field.name,
        default=default,
        is_required=default == NoDefault(),
        metadata=dc_field.metadata,
        original=dc_field,
    )


if HAS_PY_310:
    def _get_dc_param_kind(dc_field: DCField) -> ParamKind:
        return ParamKind.KW_ONLY if dc_field.kw_only else ParamKind.POS_OR_KW
else:
    def _get_dc_param_kind(dc_field: DCField) -> ParamKind:
        return ParamKind.POS_OR_KW


def get_dataclass_shape(tp) -> FullShape:
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
    dc_fields_public = dc_fields(tp)
    init_params = list(
        inspect.signature(tp.__init__).parameters.keys()
    )[1:]
    type_hints = get_all_type_hints(tp)

    return Shape(
        input=InputShape(
            constructor=tp,
            fields=tuple(
                _create_inp_field_from_dc_fields(dc_field, type_hints)
                for dc_field in name_to_dc_field.values()
                if dc_field.init and not is_class_var(normalize_type(type_hints[dc_field.name]))
            ),
            params=tuple(
                Param(
                    field_id=field_id,
                    name=field_id,
                    kind=_get_dc_param_kind(name_to_dc_field[field_id]),
                )
                for field_id in init_params
            ),
            kwargs=None,
            overriden_types=frozenset(
                field_id for field_id in init_params
                if field_id in tp.__annotations__
            ),
        ),
        output=OutputShape(
            fields=tuple(
                OutputField(
                    type=type_hints[dc_field.name],
                    id=dc_field.name,
                    default=get_dc_default(name_to_dc_field[dc_field.name]),
                    accessor=create_attr_accessor(attr_name=dc_field.name, is_required=True),
                    metadata=dc_field.metadata,
                    original=dc_field,
                )
                for dc_field in dc_fields_public
            ),
            overriden_types=frozenset(
                dc_field.name for dc_field in dc_fields_public
                if dc_field.name in tp.__annotations__
            ),
        ),
    )


# ======================
#       ClassInit
# ======================

def get_class_init_shape(tp) -> Shape[InputShape, None]:
    if not isinstance(tp, type):
        raise IntrospectionImpossible

    shape = get_callable_shape(
        tp.__init__,  # type: ignore[misc]
        slice(1, None)
    )
    return replace(
        shape,
        input=replace(
            shape.input,
            constructor=tp,
        )
    )

# =================
#       Attrs
# =================


def _get_attrs_default(attrs_field) -> Default:
    default: Any = attrs_field.default

    if isinstance(default, attrs.Factory):  # type: ignore
        if default.takes_self:
            return DefaultFactoryWithSelf(default.factory)
        return DefaultFactory(default.factory)

    if default is attrs.NOTHING:
        return NoDefault()

    return DefaultValue(default)


def _get_attrs_field_type(attrs_field, type_hints):
    try:
        return type_hints[attrs_field.name]
    except KeyError:
        return Any if attrs_field.type is None else attrs_field.type


NoneType = type(None)


def _process_attr_input_field(
    field: InputField,
    param_name_to_base_field: Dict[str, BaseField],
    has_custom_init: bool,
):
    try:
        base_field = param_name_to_base_field[field.id]
    except KeyError:
        return field

    # When input shape is generating we rely on __init__ signature,
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
        id=base_field.id,
    )


def _get_attrs_param_name(attrs_field):
    if hasattr(attrs_field, 'alias'):
        return attrs_field.alias
    return (
        attrs_field.name[1:]
        if attrs_field.name.startswith("_") and not attrs_field.name.startswith("__") else
        attrs_field.name
    )


def _get_attrs_input_shape(tp, attrs_fields, type_hints) -> InputShape:
    param_name_to_field_from_attrs = {
        _get_attrs_param_name(attrs_fld): InputField(
            id=attrs_fld.name,
            type=_get_attrs_field_type(attrs_fld, type_hints),
            default=_get_attrs_default(attrs_fld),
            metadata=attrs_fld.metadata,
            original=attrs_fld,
            is_required=_get_attrs_default(attrs_fld) == NoDefault(),
        )
        for attrs_fld in attrs_fields
        if attrs_fld.init
    }
    init_shape = get_class_init_shape(tp)

    if hasattr(tp, '__attrs_init__'):
        fields = tuple(
            InputField(
                id=param_name_to_field_from_attrs[fld.id].id,
                type=fld.type,
                default=fld.default,
                is_required=fld.is_required,
                metadata=param_name_to_field_from_attrs[fld.id].metadata,
                original=param_name_to_field_from_attrs[fld.id].original,
            )
            if fld.id in param_name_to_field_from_attrs else
            fld
            for fld in init_shape.input.fields
        )
        overriden_types = (
            frozenset(fld.id for fld in fields)
            if '__attrs_init__' in vars(tp) else
            frozenset()
        )
    else:
        fields = tuple(param_name_to_field_from_attrs.values())
        overriden_types = frozenset(
            attrs_fld.name
            for attrs_fld in attrs_fields
            if not attrs_fld.inherited and attrs_fld.init
        )

    return InputShape(
        constructor=tp,
        fields=fields,
        overriden_types=overriden_types,
        kwargs=init_shape.input.kwargs,
        params=tuple(
            Param(
                field_id=(
                    param_name_to_field_from_attrs[param.name].id
                    if param.name in param_name_to_field_from_attrs else
                    param.name
                ),
                name=param.name,
                kind=param.kind,
            )
            for param in init_shape.input.params
        ),
    )


def _get_attrs_output_shape(attrs_fields, type_hints) -> OutputShape:
    output_fields = tuple(
        OutputField(
            id=attrs_fld.name,
            type=_get_attrs_field_type(attrs_fld, type_hints),
            default=_get_attrs_default(attrs_fld),
            metadata=attrs_fld.metadata,
            original=attrs_fld,
            accessor=create_attr_accessor(attrs_fld.name, is_required=True),
        )
        for attrs_fld in attrs_fields
    )
    return OutputShape(
        fields=output_fields,
        overriden_types=frozenset(
            attrs_fld.name for attrs_fld in attrs_fields if not attrs_fld.inherited
        ),
    )


def get_attrs_shape(tp) -> FullShape:
    # TODO: rework to extras
    if not HAS_ATTRS_PKG:
        raise NoTargetPackage

    try:
        is_attrs = attrs.has(tp)
    except TypeError:
        raise IntrospectionImpossible
    if not is_attrs:
        raise IntrospectionImpossible

    try:
        attrs_fields = attrs.fields(tp)
    except (TypeError, attrs.exceptions.NotAnAttrsClassError):
        raise IntrospectionImpossible

    type_hints = get_all_type_hints(tp)
    return Shape(
        input=_get_attrs_input_shape(tp, attrs_fields, type_hints),
        output=_get_attrs_output_shape(attrs_fields, type_hints),
    )
