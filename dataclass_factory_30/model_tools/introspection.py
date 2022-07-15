import inspect
from dataclasses import MISSING as DC_MISSING
from dataclasses import Field as DCField
from dataclasses import fields as dc_fields
from dataclasses import is_dataclass, replace
from inspect import Parameter, Signature
from types import MappingProxyType
from typing import Any, Callable, Dict, Iterable, get_type_hints

from ..type_tools import is_named_tuple_class, is_typed_dict_class
from .definitions import (
    AttrAccessor,
    Default,
    DefaultFactory,
    DefaultValue,
    ExtraKwargs,
    InputField,
    InputFigure,
    IntrospectionError,
    ItemAccessor,
    NoDefault,
    OutputField,
    OutputFigure,
    ParamKind
)

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


def get_func_input_figure(func, params_slice=slice(0, None)) -> InputFigure:
    params = list(
        inspect.signature(func).parameters.values()
    )[params_slice]

    return params_to_input_figure(func, params)


def params_to_input_figure(constructor: Callable, params: Iterable[Parameter]) -> InputFigure:
    kinds = [p.kind for p in params]

    if Parameter.VAR_POSITIONAL in kinds:
        raise IntrospectionError(
            f'Can not create InputFigure'
            f' from the function that has {Parameter.VAR_POSITIONAL}'
            f' parameter'
        )

    extra = (
        ExtraKwargs()
        if Parameter.VAR_KEYWORD in kinds else
        None
    )

    return InputFigure(
        constructor=constructor,
        fields=tuple(
            InputField(
                type=Any if _is_empty(param.annotation) else param.annotation,
                name=param.name,
                is_required=_is_empty(param.default),
                default=NoDefault() if _is_empty(param.default) else DefaultValue(param.default),
                metadata=MappingProxyType({}),
                param_kind=_PARAM_KIND_CONV[param.kind],
            )
            for param in params
            if param.kind != Parameter.VAR_KEYWORD
        ),
        extra=extra,
    )


# ======================
#       NamedTuple
# ======================

def get_named_tuple_input_figure(tp) -> InputFigure:
    if not is_named_tuple_class(tp):
        raise IntrospectionError

    input_figure = get_func_input_figure(tp.__new__, slice(1, None))

    type_hints = get_type_hints(tp)

    # At <3.9 namedtuple does not generate typehints at __new__
    return InputFigure(
        constructor=tp,
        extra=input_figure.extra,  # maybe for custom __init__?
        fields=tuple(
            replace(
                fld,
                type=type_hints.get(fld.name, Any)
            )
            for fld in input_figure.fields
        )
    )


def get_named_tuple_output_figure(tp) -> OutputFigure:
    return OutputFigure(
        fields=tuple(
            OutputField(
                name=fld.name,
                type=fld.type,
                default=fld.default,
                metadata=fld.metadata,
                accessor=AttrAccessor(attr_name=fld.name, is_required=True),
            )
            for fld in get_named_tuple_input_figure(tp).fields
        ),
        extra=None,
    )


# =====================
#       TypedDict
# =====================

def _get_fields_are_required(tp) -> bool:
    if not is_typed_dict_class(tp):
        raise IntrospectionError

    return tp.__total__


def get_typed_dict_input_figure(tp) -> InputFigure:
    are_required = _get_fields_are_required(tp)

    return InputFigure(
        constructor=tp,
        fields=tuple(
            InputField(
                type=tp,
                name=name,
                default=NoDefault(),
                is_required=are_required,
                metadata=MappingProxyType({}),
                param_kind=ParamKind.KW_ONLY,
            )
            for name, tp in get_type_hints(tp).items()
        ),
        extra=None,
    )


def get_typed_dict_output_figure(tp) -> OutputFigure:
    are_required = _get_fields_are_required(tp)

    return OutputFigure(
        fields=tuple(
            OutputField(
                type=tp,
                name=name,
                default=NoDefault(),
                accessor=ItemAccessor(name, are_required),
                metadata=MappingProxyType({}),
            )
            for name, tp in get_type_hints(tp).items()
        ),
        extra=None,
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


def create_inp_field_from_dc_fields(dc_field: DCField):
    default = get_dc_default(dc_field)
    return InputField(
        type=dc_field.type,
        name=dc_field.name,
        default=default,
        is_required=default == NoDefault(),
        metadata=dc_field.metadata,
        param_kind=ParamKind.POS_OR_KW,
    )


def get_dataclass_input_figure(tp) -> InputFigure:
    """This provider does not work properly if __init__ signature differs from
    that would be created by dataclass decorator.

    It happens because we can not distinguish __init__ that generated
    by @dataclass and __init__ that created by other ways.
    And we can not analyze only __init__ signature
    because @dataclass uses private constant
    as default value for fields with default_factory
    """

    if not is_dataclass(tp):
        raise IntrospectionError

    name_to_dc_field = all_dc_fields(tp)

    init_params = list(
        inspect.signature(tp.__init__).parameters.keys()
    )[1:]

    return InputFigure(
        constructor=tp,
        fields=tuple(
            create_inp_field_from_dc_fields(name_to_dc_field[field_name])
            for field_name in init_params
        ),
        extra=None,
    )


def get_dataclass_output_figure(tp) -> OutputFigure:
    if not is_dataclass(tp):
        raise IntrospectionError

    name_to_dc_field = all_dc_fields(tp)

    return OutputFigure(
        fields=tuple(
            OutputField(
                type=field.type,
                name=field.name,
                default=get_dc_default(name_to_dc_field[field.name]),
                accessor=AttrAccessor(field.name, True),
                metadata=field.metadata,
            )
            for field in dc_fields(tp)
        ),
        extra=None,
    )


# ======================
#       ClassInit
# ======================

def get_class_init_input_figure(tp) -> InputFigure:
    if not isinstance(tp, type):
        raise IntrospectionError

    input_figure = get_func_input_figure(
        tp.__init__,  # type: ignore[misc]
        slice(1, None)
    )

    return replace(
        input_figure,
        constructor=tp,
    )
