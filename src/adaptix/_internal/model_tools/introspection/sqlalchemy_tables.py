from inspect import getfullargspec
from typing import Any, Optional

from sqlalchemy import inspect
from sqlalchemy.sql.schema import CallableColumnDefault, ScalarElementColumnDefault

from adaptix._internal.model_tools.definitions import (
    DefaultFactory,
    DefaultValue,
    FullShape,
    InputField,
    InputShape,
    NoDefault,
    OutputField,
    OutputShape,
    Param,
    ParamKind,
    Shape,
    create_attr_accessor,
)
from adaptix._internal.type_tools import get_all_type_hints


class ColumnPropertyWrapper:
    def __init__(self, column_property):
        self.column_property = column_property


def _is_context_sensitive(default):
    try:
        wrapped_callable = default.arg.__wrapped__
    except AttributeError:
        return True

    spec = getfullargspec(wrapped_callable)
    return len(spec.args) > 0


def _get_sqlalchemy_type_for_column(column, type_hints):
    try:
        return type_hints[column.name].__args__[0]
    except KeyError:
        if column.nullable:
            return Optional[column.type.python_type]
        return column.type.python_type


def _get_sqlalchemy_type_for_relationship(relationship, type_hints):
    try:
        return type_hints[str(relationship).split(".")[1]].__args__[0]
    except KeyError:
        return Any


def _get_sqlalchemy_default(column_default):
    if isinstance(column_default, CallableColumnDefault) and not _is_context_sensitive(column_default):
        return DefaultFactory(factory=column_default.arg.__wrapped__)
    if isinstance(column_default, ScalarElementColumnDefault):
        return DefaultValue(value=column_default.arg)
    return NoDefault()


def _get_sqlalchemy_required(column):
    return not (
        column.default or column.nullable or column.server_default
        or (column.primary_key and column.autoincrement and column.type.python_type is int)
    )


def _get_sqlalchemy_input_shape(tp, columns, relationships, type_hints) -> InputShape:
    param_name_to_field = {
        column.name: InputField(
            id=column.name,
            type=_get_sqlalchemy_type_for_column(column, type_hints),
            default=_get_sqlalchemy_default(column.default),
            is_required=_get_sqlalchemy_required(column),
            metadata=column.info,
            original=ColumnPropertyWrapper(column_property=column)
        )
        for column in columns
    }

    for relationship in relationships:
        name = str(relationship).split(".")[1]
        param_name_to_field[name] = InputField(
            id=name,
            type=_get_sqlalchemy_type_for_relationship(relationship, type_hints),
            default=NoDefault(),
            is_required=False,
            metadata={},
            original=relationship
        )

    fields = tuple(param_name_to_field.values())

    return InputShape(
        constructor=tp,
        fields=fields,
        overriden_types=frozenset(),
        kwargs=None,
        params=tuple(
            Param(
                field_id=column.name,
                name=column.name,
                kind=ParamKind.KW_ONLY
            )
            for column in columns
        )
    )


def _get_sqlalchemy_output_shape(columns, relationships, type_hints) -> OutputShape:
    output_fields = [
        OutputField(
            id=column.name,
            type=_get_sqlalchemy_type_for_column(column, type_hints),
            default=_get_sqlalchemy_default(column.default),
            metadata=column.info,
            original=ColumnPropertyWrapper(column_property=column),
            accessor=create_attr_accessor(column.name, is_required=True)
        )
        for column in columns
    ]

    for relationship in relationships:
        name = str(relationship).split(".")[1]
        output_fields.append(
            OutputField(
                id=name,
                type=_get_sqlalchemy_type_for_relationship(relationship, type_hints),
                default=NoDefault(),
                metadata={},
                original=relationship,
                accessor=create_attr_accessor(name, is_required=False)
            )
        )

    return OutputShape(
        fields=tuple(output_fields),
        overriden_types=frozenset()
    )


def get_sqlalchemy_shape(tp) -> FullShape:
    columns = inspect(tp).columns
    relationships = inspect(tp).relationships
    type_hints = get_all_type_hints(tp)
    return Shape(
        input=_get_sqlalchemy_input_shape(tp, columns, relationships, type_hints),
        output=_get_sqlalchemy_output_shape(columns, relationships, type_hints)
    )
