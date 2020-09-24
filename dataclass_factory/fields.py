import inspect
from dataclasses import Field, MISSING, fields, dataclass
from functools import partial
from typing import Sequence, Any, Type, TypeVar, Callable, List, Dict, Union, Optional, cast

from .generics import resolve_hints, resolve_init_hints
from .naming import convert_name
from .path_utils import CleanPath, CleanKey, ellipsis, replace_ellipsis
from .schema import Schema
from .type_detection import is_generic_concrete

T = TypeVar("T")


@dataclass
class BaseFieldInfo:
    field_name: str
    type: Any
    default: Any


@dataclass
class FieldInfo(BaseFieldInfo):
    data_name: Union[CleanKey, CleanPath]


# defaults

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


# all fields
FieldsFilter = Callable[[str], bool]


def all_dataclass_fields(cls, omit_default: Optional[bool], fields_filter: FieldsFilter = None) -> List[BaseFieldInfo]:
    if is_generic_concrete(cls):
        all_fields = fields(cls.__origin__)
    else:
        all_fields = fields(cls)
    hints = resolve_hints(cls)
    return [
        BaseFieldInfo(field_name=f.name, type=hints[f.name], default=get_dataclass_default(f))
        for f in all_fields
        if not fields_filter or fields_filter(f.name) and f.init
    ]


def all_class_fields(cls, omit_default: Optional[bool], fields_filter: FieldsFilter = None) -> List[BaseFieldInfo]:
    all_fields = inspect.signature(cls.__init__).parameters
    hints = resolve_init_hints(cls)
    return [
        BaseFieldInfo(field_name=f.name, type=hints.get(f.name, Any), default=get_func_default(f))
        for f in all_fields.values()
        if not fields_filter or fields_filter(f.name)
    ]


def all_typeddict_fields(cls, omit_default: Optional[bool], fields_filter: FieldsFilter = None) -> List[BaseFieldInfo]:
    all_fields = resolve_hints(cls)
    return [
        BaseFieldInfo(field_name=f, type=t, default=MISSING)
        for f, t in all_fields.items()
        if not fields_filter or fields_filter(f)
    ]


def schema_fields_filter(schema: Schema, name: str):
    """
    Checks if field is allowed by a schema:
    * field is in `only` list (if provided some)
    * field is not excluded
    """
    return (
        (schema.only is None or name in schema.only)
        and
        (schema.exclude is None or name not in schema.exclude)
    )


AllFieldsGetter = Callable[[Any, Optional[bool], FieldsFilter], List[BaseFieldInfo]]


def get_fields(
    all_fields_getter: AllFieldsGetter,
    schema: Schema[T],
    class_: Type[T]
) -> Sequence[FieldInfo]:
    partial_fields_filter: FieldsFilter = partial(schema_fields_filter, schema)  # type: ignore
    all_fields = all_fields_getter(class_, schema.omit_default, partial_fields_filter)
    only_mapped = schema.only_mapped and schema.only is None
    if only_mapped:
        if schema.name_mapping is None:
            raise ValueError("`name_mapping` is None, and `only_mapped` is True")
        fields_dict: Dict[str, BaseFieldInfo] = {f.field_name: f for f in all_fields}
        fields_info: List[FieldInfo] = []
        for field_name, data_name in schema.name_mapping.items():
            if isinstance(field_name, ellipsis):
                raise ValueError("`name_mapping` contains `...`, and `only_mapped` is True")
            if field_name not in fields_dict:
                continue
            fields_info.append(FieldInfo(
                field_name=cast(str, field_name),
                data_name=replace_ellipsis(field_name, data_name),
                type=fields_dict[field_name].type,
                default=fields_dict[field_name].default,
            ))
        return tuple(fields_info)
    whitelisted_fields = set(schema.only or []) | set(schema.name_mapping or [])
    return tuple(
        FieldInfo(
            field_name=f.field_name,
            data_name=convert_name(f.field_name, schema.name_style, schema.name_mapping,
                                   schema.trim_trailing_underscore),
            type=f.type,
            default=f.default,
        )
        for f in all_fields
        if (not schema.skip_internal) or (f.field_name in whitelisted_fields) or (not f.field_name.startswith("_"))
    )


# wrappers
def get_dataclass_fields(schema: Schema[T], class_: Type[T]) -> Sequence[FieldInfo]:
    return get_fields(all_dataclass_fields, schema, class_)


def get_typeddict_fields(schema: Schema[T], class_: Type[T]) -> Sequence[FieldInfo]:
    return get_fields(all_typeddict_fields, schema, class_)


def get_class_fields(schema: Schema[T], class_: Type[T]) -> Sequence[FieldInfo]:
    return get_fields(all_class_fields, schema, class_)
