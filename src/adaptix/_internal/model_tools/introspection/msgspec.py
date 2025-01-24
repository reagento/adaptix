from types import MappingProxyType
from typing import Mapping

from msgspec import NODEFAULT
from msgspec.structs import FieldInfo, fields

from ...feature_requirement import HAS_MSGSPEC_PKG, HAS_SUPPORTED_MSGSPEC_PKG
from ...type_tools import get_all_type_hints
from ..definitions import (
    Default,
    DefaultFactory,
    DefaultValue,
    FullShape,
    InputField,
    InputShape,
    IntrospectionError,
    NoDefault,
    NoTargetPackageError,
    OutputField,
    OutputShape,
    Param,
    ParamKind,
    TooOldPackageError,
    create_attr_accessor,
)


def _get_default_from_field_info(fi: FieldInfo) -> Default:
    if fi.default is not NODEFAULT:
        return DefaultValue(fi.default)
    if fi.default_factory is not NODEFAULT:
        return DefaultFactory(fi.default_factory)
    return NoDefault()


def _create_input_field_from_structs_field_info(fi: FieldInfo, type_hints: Mapping) -> InputField:
    default = _get_default_from_field_info(fi)
    return InputField(
        id=fi.name,
        type=type_hints[fi.name],
        default=default,
        is_required=default == NoDefault(),
        original=fi,
        metadata=MappingProxyType({}),
    )


def get_struct_shape(tp) -> FullShape:
    if not HAS_SUPPORTED_MSGSPEC_PKG:
        if not HAS_MSGSPEC_PKG:
            raise NoTargetPackageError(HAS_MSGSPEC_PKG)
        raise TooOldPackageError(HAS_SUPPORTED_MSGSPEC_PKG)

    try:
        fields_info = fields(tp)
    except TypeError:
        raise IntrospectionError

    type_hints = get_all_type_hints(tp)
    return FullShape(
        InputShape(
            constructor=tp,
            fields=tuple(
                _create_input_field_from_structs_field_info(fi, type_hints)
                for fi in fields_info
            ),
            params=tuple(
                Param(
                    field_id=field_id,
                    name=field_id,
                    kind=ParamKind.POS_OR_KW,
                )
                for field_id in type_hints
        ),
            kwargs=None,
            overriden_types=frozenset(tp.__annotations__.keys()),
        ),
        OutputShape(
            fields=tuple(
                OutputField(
                    id=fi.name,
                    type=type_hints[fi.name],
                    original=fi,
                    metadata=MappingProxyType({}),
                    default=_get_default_from_field_info(fi),
                    accessor=create_attr_accessor(attr_name=fi.name, is_required=True),
                ) for fi in fields_info),
            overriden_types=frozenset(tp.__annotations__.keys()),
        ),
    )
