import inspect
from dataclasses import dataclass, Field, fields, MISSING
from functools import partial
from typing import Any, Callable, cast, Dict, List, Sequence, Type, TypeVar, Union

from .generics import resolve_hints, resolve_init_hints
from .naming import convert_name
from .path_utils import CleanKey, CleanPath, Key, Path, replace_ellipsis
from .schema import Schema
from .type_detection import is_generic_concrete

T = TypeVar("T")


@dataclass
class BaseFieldInfo:
    field_name: str
    type: Any  # noqa A003
    default: Any


@dataclass
class FieldInfo(BaseFieldInfo):
    data_name: Union[CleanKey, CleanPath]


def get_dataclass_default(field: Field) -> Any:
    # type ignore because of https://github.com/python/mypy/issues/6910
    if field.default_factory != MISSING:  # type: ignore
        return field.default_factory()  # type: ignore
    return field.default


def get_func_default(parameter: inspect.Parameter) -> Any:
    # type ignore because of https://github.com/python/mypy/issues/6910
    if parameter.default is inspect.Parameter.empty:
        return MISSING
    return parameter.default


def all_dataclass_fields(cls) -> List[BaseFieldInfo]:
    if is_generic_concrete(cls):
        all_fields = fields(cls.__origin__)
    else:
        all_fields = fields(cls)
    hints = resolve_hints(cls)

    return [
        BaseFieldInfo(
            field_name=f.name,
            type=hints[f.name],
            default=get_dataclass_default(f),
        )
        for f in all_fields if f.init
    ]


def all_class_fields(cls) -> List[BaseFieldInfo]:
    all_fields = inspect.signature(cls.__init__).parameters
    hints = resolve_init_hints(cls)
    return [
        BaseFieldInfo(
            field_name=f.name,
            type=hints.get(f.name, Any),
            default=get_func_default(f),
        )
        for f in all_fields.values()
    ]


def all_namedtuple_fields(cls) -> List[BaseFieldInfo]:
    hints = resolve_hints(cls)
    # There is no _field_defaults in python 3.6 for `namedtuple()`
    defaults = getattr(cls, "_field_defaults", {})
    return [
        BaseFieldInfo(
            field_name=fieldname,
            type=hints.get(fieldname, Any),
            default=defaults.get(fieldname, MISSING),
        )
        for fieldname in cls._fields
    ]


def all_typeddict_fields(cls) -> List[BaseFieldInfo]:
    all_fields = resolve_hints(cls)
    return [
        BaseFieldInfo(field_name=f, type=t, default=MISSING)
        for f, t in all_fields.items()
    ]


def schema_fields_filter(schema: Schema, name: str):
    """Check if field is allowed by a schema.

    * field is in `only` list (if provided some)
    * field is not excluded
    """
    return (
        (schema.only is None or name in schema.only) and
        (schema.exclude is None or name not in schema.exclude)
    )


AllFieldsGetter = Callable[[Any], List[BaseFieldInfo]]


def get_fields(
    all_fields_getter: AllFieldsGetter,
    schema: Schema[T],
    class_: Type[T],
) -> Sequence[FieldInfo]:
    all_fields = [
        field for field in all_fields_getter(class_)
        if schema_fields_filter(schema, field.field_name)
    ]
    # `only` has more priority than only_mapped
    if schema.only_mapped and schema.only is None:
        if schema.name_mapping is None:
            raise ValueError("`name_mapping` is None, and `only_mapped` is True")
        if ... in schema.name_mapping:
            raise ValueError("`name_mapping` contains `...`, and `only_mapped` is True")

        return get_only_mapped_fields(
            schema.name_mapping,  # type: ignore
            all_fields,
        )

    if schema.skip_internal:  # remove "internal fields"
        whitelisted_fields = set(schema.only or []) | set(schema.name_mapping or [])
        all_fields = [
            f for f in all_fields
            if f.field_name in whitelisted_fields or not f.field_name.startswith("_")
        ]
    convert_name_func = partial(
        convert_name,
        name_style=schema.name_style,
        name_mapping=schema.name_mapping,
        trim_trailing_underscore=schema.trim_trailing_underscore,
    )
    return tuple(
        FieldInfo(
            field_name=f.field_name,
            data_name=convert_name_func(f.field_name),
            type=f.type,
            default=f.default,
        )
        for f in all_fields
    )


def get_only_mapped_fields(
    name_mapping: Dict[str, Union[Key, Path]],
    all_fields: List[BaseFieldInfo],
):
    fields_dict: Dict[str, BaseFieldInfo] = {f.field_name: f for f in all_fields}

    return tuple(
        FieldInfo(
            field_name=cast(str, field_name),
            data_name=replace_ellipsis(field_name, data_name),
            type=fields_dict[field_name].type,
            default=fields_dict[field_name].default,
        )
        for field_name, data_name in name_mapping.items()
        if field_name in fields_dict
    )


# wrappers
def get_dataclass_fields(schema: Schema[T], class_: Type[T]) -> Sequence[FieldInfo]:
    return get_fields(all_dataclass_fields, schema, class_)


def get_namedtuple_fields(schema: Schema[T], class_: Type[T]) -> Sequence[FieldInfo]:
    return get_fields(all_namedtuple_fields, schema, class_)


def get_typeddict_fields(schema: Schema[T], class_: Type[T]) -> Sequence[FieldInfo]:
    return get_fields(all_typeddict_fields, schema, class_)


def get_class_fields(schema: Schema[T], class_: Type[T]) -> Sequence[FieldInfo]:
    return get_fields(all_class_fields, schema, class_)
