import inspect
from functools import partial
from typing import Sequence, Tuple, Union, Any, Type, TypeVar, NamedTuple, Callable, List, get_type_hints

from dataclasses import Field, MISSING, fields

from ..schema import Schema, Path, convert_name

T = TypeVar("T")


class FieldInfo(NamedTuple):
    field_name: str
    data_name: str
    default: Any


def get_dataclass_default(field: Field, omit_default: bool) -> Any:
    if not omit_default:
        return MISSING
    # type ignore because of https://github.com/python/mypy/issues/6910
    if field.default_factory != MISSING:  # type: ignore
        return field.default_factory()  # type: ignore
    return field.default


def get_func_default(paramter: inspect.Parameter, omit_default: bool) -> Any:
    if not omit_default:
        return MISSING
    # type ignore because of https://github.com/python/mypy/issues/6910
    if paramter.default is inspect.Parameter.empty:
        return MISSING
    return paramter.default


# all fields
FilterFunc = Callable[[str], bool]


def all_dataclass_fields(cls, omit_default: bool, filter_func: FilterFunc = None) -> List[Tuple[str, Any]]:
    all_fields = fields(cls)
    return [
        (f.name, get_dataclass_default(f, omit_default))
        for f in all_fields
        if not filter_func or filter_func(f.name)
    ]


def all_class_fields(cls, omit_default: bool, filter_func: FilterFunc = None) -> List[Tuple[str, Any]]:
    all_fields = inspect.signature(cls.__init__).parameters
    return [
        (f.name, get_func_default(f, omit_default))
        for f in all_fields
        if not filter_func or filter_func(f.name)
    ]


def all_typeddict_fields(cls, omit_default: bool, filter_func: FilterFunc = None) -> List[Tuple[str, Any]]:
    all_fields = get_type_hints(cls)
    return [
        (f, MISSING)
        for f in all_fields
        if not filter_func or filter_func(f)
    ]


def filter_func(schema: Schema, name: str):
    """
    Checks if field is allowed by schema:
    * field is in `only` list (if provided some)
    * field is not excluded
    """
    return ((schema.only is None or name in schema.only) and
            (schema.exclude is None or name not in schema.exclude))


AllFieldsGetter = Callable[[Any, bool, FilterFunc], List[Tuple[str, Any]]]


def get_fields(
        all_fields_getter: AllFieldsGetter,
        schema: Schema[T],
        class_: Type[T]
) -> Sequence[Tuple[str, Union[str, Path], Any]]:
    partial_filter_func: FilterFunc = partial(filter_func, schema)  # type: ignore
    all_fields = all_fields_getter(class_, schema.omit_default, partial_filter_func)
    only_mapped = schema.only_mapped and schema.only is None
    if only_mapped:
        if schema.name_mapping is None:
            raise ValueError("`name_mapping` is None, and `only_mapped` is True")
        defaults = dict(all_fields)
        return tuple(
            FieldInfo(
                field_name=field_name,
                data_name=data_name,
                default=defaults[field_name]
            )
            for field_name, data_name in schema.name_mapping.items()
            if field_name in defaults
        )

    whitelisted_fields = set(schema.only or []) | set(schema.name_mapping or [])
    return tuple(
        FieldInfo(
            field_name=field_name,
            data_name=convert_name(field_name, schema.name_style, schema.name_mapping, schema.trim_trailing_underscore),
            default=default
        )
        for field_name, default in all_fields
        if (not schema.skip_internal) or (field_name in whitelisted_fields) or (not field_name.startswith("_"))
    )


#
def get_dataclass_fields(schema: Schema[T], class_: Type[T]) -> Sequence[Tuple[str, Union[str, Path], Any]]:
    return get_fields(all_dataclass_fields, schema, class_)
