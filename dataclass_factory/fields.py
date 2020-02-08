import inspect
from functools import partial
from typing import Sequence, Any, Type, TypeVar, Callable, List, Dict, Union, Optional

from dataclasses import Field, MISSING, fields, dataclass

from .generics import resolve_hints, resolve_init_hints
from .schema import Schema, Path
from .naming import convert_name
from .type_detection import is_generic_concrete

T = TypeVar("T")


@dataclass
class BaseFieldInfo:
    field_name: str
    type: Any
    default: Any


@dataclass
class FieldInfo(BaseFieldInfo):
    data_name: Union[str, Path]


# defaults

def get_dataclass_default(field: Field, omit_default: Optional[bool]) -> Any:
    if not omit_default:
        return MISSING
    # type ignore because of https://github.com/python/mypy/issues/6910
    if field.default_factory != MISSING:  # type: ignore
        return field.default_factory()  # type: ignore
    return field.default


def get_func_default(paramter: inspect.Parameter, omit_default: Optional[bool]) -> Any:
    if not omit_default:
        return MISSING
    # type ignore because of https://github.com/python/mypy/issues/6910
    if paramter.default is inspect.Parameter.empty:
        return MISSING
    return paramter.default


# all fields
FilterFunc = Callable[[str], bool]


def all_dataclass_fields(cls, omit_default: Optional[bool], filter_func: FilterFunc = None) -> List[BaseFieldInfo]:
    if is_generic_concrete(cls):
        all_fields = fields(cls.__origin__)
    else:
        all_fields = fields(cls)
    hints = resolve_hints(cls)
    return [
        BaseFieldInfo(field_name=f.name, type=hints[f.name], default=get_dataclass_default(f, omit_default))
        for f in all_fields
        if not filter_func or filter_func(f.name)
    ]


def all_class_fields(cls, omit_default: Optional[bool], filter_func: FilterFunc = None) -> List[BaseFieldInfo]:
    all_fields = inspect.signature(cls.__init__).parameters
    hints = resolve_init_hints(cls)
    return [
        BaseFieldInfo(field_name=f.name, type=hints.get(f.name, Any), default=get_func_default(f, omit_default))
        for f in all_fields.values()
        if not filter_func or filter_func(f.name)
    ]


def all_typeddict_fields(cls, omit_default: Optional[bool], filter_func: FilterFunc = None) -> List[BaseFieldInfo]:
    all_fields = resolve_hints(cls)
    return [
        BaseFieldInfo(field_name=f, type=t, default=MISSING)
        for f, t in all_fields.items()
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


AllFieldsGetter = Callable[[Any, Optional[bool], FilterFunc], List[BaseFieldInfo]]


def get_fields(
        all_fields_getter: AllFieldsGetter,
        schema: Schema[T],
        class_: Type[T]
) -> Sequence[FieldInfo]:
    partial_filter_func: FilterFunc = partial(filter_func, schema)  # type: ignore
    all_fields = all_fields_getter(class_, schema.omit_default, partial_filter_func)
    only_mapped = schema.only_mapped and schema.only is None
    if only_mapped:
        if schema.name_mapping is None:
            raise ValueError("`name_mapping` is None, and `only_mapped` is True")
        fields: Dict[str, BaseFieldInfo] = {f.field_name: f for f in all_fields}
        return tuple(
            FieldInfo(
                field_name=field_name,
                data_name=data_name,
                type=fields[field_name].type,
                default=fields[field_name].default,
            )
            for field_name, data_name in schema.name_mapping.items()
            if field_name in fields
        )

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
