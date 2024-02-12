from inspect import getfullargspec
from typing import List, Optional

try:
    from sqlalchemy import inspect
    from sqlalchemy.exc import NoInspectionAvailable
    from sqlalchemy.orm import Mapper
    from sqlalchemy.sql.schema import CallableColumnDefault, ScalarElementColumnDefault
except ImportError:
    pass

from ...feature_requirement import HAS_SQLALCHEMY_PKG, HAS_SUPPORTED_SQLALCHEMY_PKG
from ...type_tools import get_all_type_hints
from ..definitions import (
    DefaultFactory,
    DefaultValue,
    FullShape,
    InputField,
    InputShape,
    IntrospectionImpossible,
    NoDefault,
    NoTargetPackage,
    OutputField,
    OutputShape,
    PackageIsTooOld,
    Param,
    ParamKind,
    Shape,
    create_attr_accessor,
)


class ColumnWrapper:
    def __init__(self, column):
        self.column = column


def _is_context_sensitive(default):
    try:
        wrapped_callable = default.arg.__wrapped__
    except AttributeError:
        return True

    spec = getfullargspec(wrapped_callable)
    return len(spec.args) > 0


def _get_type_for_column(column, type_hints):
    try:
        return type_hints[column.name]
    except KeyError:
        if column.nullable:
            return Optional[column.type.python_type]
        return column.type.python_type


def _get_type_for_relationship(relationship, type_hints):
    try:
        return type_hints[relationship.key]
    except KeyError:
        if relationship.uselist:
            return List[relationship.entity.class_]
        return Optional[relationship.entity.class_]


def _get_default(column_default):
    if isinstance(column_default, CallableColumnDefault) and not _is_context_sensitive(column_default):
        return DefaultFactory(factory=column_default.arg.__wrapped__)
    if isinstance(column_default, ScalarElementColumnDefault):
        return DefaultValue(value=column_default.arg)
    return NoDefault()


def _is_input_required_for_column(column):
    return not (
        #  columns constrainted by FK are not required since they can be specified by instances
        column.default or column.nullable or column.server_default or column.foreign_keys
        or (column.primary_key and column.autoincrement and column.type.python_type is int)
    )


def _is_output_required_for_column(column):
    return not column.nullable


def _is_output_required_for_relationship(relationship):
    if relationship.uselist:
        return True
    for column in relationship.local_columns:
        if column.nullable:
            return False
    return True


def _get_input_shape(tp, columns, relationships, type_hints) -> InputShape:
    fields = []
    params = []
    for column in columns:
        fields.append(
            InputField(
                id=column.name,
                type=_get_type_for_column(column, type_hints),
                default=_get_default(column.default),
                is_required=_is_input_required_for_column(column),
                metadata=column.info,
                original=ColumnWrapper(column=column)
            )
        )
        params.append(
            Param(
                field_id=column.name,
                name=column.name,
                kind=ParamKind.KW_ONLY
            )
        )

    for relationship in relationships:
        fields.append(
            InputField(
                id=relationship.key,
                type=_get_type_for_relationship(relationship, type_hints),
                default=NoDefault(),
                is_required=False,
                metadata={},
                original=relationship
            )
        )
        params.append(
            Param(
                field_id=relationship.key,
                name=relationship.key,
                kind=ParamKind.KW_ONLY
            )
        )

    return InputShape(
        constructor=tp,
        fields=tuple(fields),
        overriden_types=frozenset(),
        kwargs=None,
        params=tuple(params)
    )


def _get_output_shape(columns, relationships, type_hints) -> OutputShape:
    output_fields = [
        OutputField(
            id=column.name,
            type=_get_type_for_column(column, type_hints),
            default=_get_default(column.default),
            metadata=column.info,
            original=ColumnWrapper(column=column),
            accessor=create_attr_accessor(column.name, is_required=_is_output_required_for_column(column))
        )
        for column in columns
    ]

    for relationship in relationships:
        name = str(relationship).split(".")[1]
        output_fields.append(
            OutputField(
                id=name,
                type=_get_type_for_relationship(relationship, type_hints),
                default=NoDefault(),
                metadata={},
                original=relationship,
                accessor=create_attr_accessor(name, is_required=relationship.uselist)
            )
        )

    return OutputShape(
        fields=tuple(output_fields),
        overriden_types=frozenset()
    )


def get_sqlalchemy_shape(tp) -> FullShape:
    if not HAS_SUPPORTED_SQLALCHEMY_PKG:
        if not HAS_SQLALCHEMY_PKG:
            raise NoTargetPackage
        raise PackageIsTooOld(HAS_SUPPORTED_SQLALCHEMY_PKG.min_version)

    try:
        mapper = inspect(tp)
    except NoInspectionAvailable:
        raise IntrospectionImpossible

    if not isinstance(mapper, Mapper):
        raise IntrospectionImpossible

    columns = mapper.columns
    relationships = mapper.relationships
    type_hints = get_all_type_hints(tp)
    return Shape(
        input=_get_input_shape(tp, columns, relationships, type_hints),
        output=_get_output_shape(columns, relationships, type_hints)
    )
