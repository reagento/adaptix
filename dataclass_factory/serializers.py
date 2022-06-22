from dataclasses import is_dataclass, MISSING
from marshal import dumps, loads
from operator import attrgetter, getitem
from typing import Any, Callable, Dict, List, Optional, Sequence, Type, Union

from .common import AbstractFactory, K, Serializer, T
from .fields import (
    FieldInfo, get_dataclass_fields, get_typeddict_fields,
    get_namedtuple_fields,
)
from .generics import fix_generic_alias
from .path_utils import CleanKey, CleanPath, init_structure
from .schema import Schema, Unknown
from .type_detection import (
    hasargs, is_any, is_iterable, is_dict, is_enum, is_generic_concrete,
    is_newtype, is_optional, is_tuple, is_type_var, is_typeddict, is_union,
    is_literal, is_literal36, instance_wont_have_dict, is_none, is_namedtuple,
)


def to_path(key: Union[CleanKey, CleanPath]) -> CleanPath:
    if isinstance(key, tuple):
        return key
    return (key,)


def unpack_fields(dest, fields):
    for f in fields:
        dest.update(dest.pop(f, {}))


def get_complex_serializer(
    factory: AbstractFactory,  # noqa C901,CCR001
    schema: Schema[T],
    fields: Sequence[FieldInfo],
    getter: Callable[[Any, Any], Any],
    omit_missing: bool,
) -> Serializer[T]:
    """
    :param getter: functions used to get data for each field (attribute, key and so on)
    :param omit_missing: omit special MISSING values retrieved from getter. Is applied when all defaults are MISSING.
    """
    has_default = schema.omit_default and any(f.default != MISSING for f in fields)
    if omit_missing:
        has_default = has_default or all(f.default == MISSING for f in fields)
    field_info = tuple(
        (f.field_name, factory.serializer(f.type), f.data_name, f.default)
        for f in fields
    )
    unknown=schema.unknown
    if isinstance(unknown, Unknown):
        unpack_unknown = False
    elif isinstance(unknown, str):
        unpack_unknown = True
        unknown = [unknown]
    else:  # sequence of strings
        unpack_unknown = True

    if schema.name_mapping and any(isinstance(key, tuple) for key in schema.name_mapping.values()):
        paths = tuple(to_path(f.data_name) for f in fields)
        pickled = dumps(init_structure(paths))
        if has_default:
            if schema.omit_default:
                raise ValueError("Cannot use `omit_default` option with flattening schema")
            else:
                raise ValueError("Cannot omit missing values with flattening schema")

        def serialize(data):
            container, field_containers = loads(pickled)
            for (
                (inner_container, data_name), (field_name, serializer, *_)
            ) in zip(field_containers, field_info):
                inner_container[data_name] = serializer(getter(data, field_name))
            if unpack_unknown:
                unpack_fields(container, unknown)
            return container
    else:
        if has_default:
            def serialize(data):
                container = {
                    data_name: value
                    for field_name, serializer, data_name, default in field_info
                    for value in (serializer(getter(data, field_name)),)
                    if value != default
                }
                if unpack_unknown:
                    unpack_fields(container, unknown)
                return container
        else:
            # optimized version
            def serialize(data):
                container = {
                    data_name: serializer(getter(data, field_name))
                    for field_name, serializer, data_name, default in field_info
                }
                if unpack_unknown:
                    unpack_fields(container, unknown)
                return container
    return serialize


def get_collection_serializer(serializer: Serializer[T]) -> Serializer[List[T]]:
    def collection_serializer(data):
        return [serializer(x) for x in data]

    return collection_serializer


def get_tuple_serializer(serializers) -> Serializer[List]:
    def tuple_serializer(data):
        return [serializer(x) for x, serializer in zip(data, serializers)]

    return tuple_serializer


def get_collection_any_serializer() -> Serializer[List[Any]]:
    return lambda data: list(data)


def get_vars_serializer(factory) -> Serializer:
    field_serializer = get_lazy_serializer(factory)

    def vars_serializer(data: Any):
        return {
            k: field_serializer(v)
            for k, v in vars(data).items()
        }

    return vars_serializer


def serialize_none(data: Any) -> None:
    if data is not None:
        raise ValueError("None expected")


def stub_serializer(data: T) -> T:
    return data


def get_dict_serializer(
    key_serializer: Serializer[K], serializer: Serializer[T]
) -> Serializer[Dict[Any, Any]]:
    return lambda data: {
        key_serializer(k): serializer(v) for k, v in data.items()
    }


def get_lazy_serializer(factory) -> Serializer:
    def lazy_serializer(data):
        return factory.serializer(type(data))(data)

    return lazy_serializer


def get_optional_serializer(serializer: Serializer[T]) -> Serializer[Optional[T]]:
    def optional_serializer(data):
        if data is None:
            return None
        else:
            return serializer(data)

    return optional_serializer


def create_serializer(factory, schema: Schema, debug_path: bool, class_: Type) -> Serializer:
    serializer = create_serializer_impl(factory, schema, debug_path, class_)
    pre = schema.pre_serialize
    post = schema.post_serialize
    if pre or post:
        def serializer_with_steps(data):
            if pre:
                data = pre(data)
            data = serializer(data)
            if post:
                return post(data)
            return data

        return serializer_with_steps
    return serializer


def create_serializer_impl(factory, schema: Schema, debug_path: bool,
                           class_: Type) -> Serializer:  # noqa C901,CCR001
    class_ = fix_generic_alias(class_)
    if class_ in (str, bytearray, bytes, int, float, complex, bool):
        return stub_serializer
    if is_none(class_):
        return serialize_none
    if is_literal(class_) or is_literal36(class_) or is_none(class_):
        return stub_serializer
    if is_newtype(class_):
        return create_serializer_impl(factory, schema, debug_path, class_.__supertype__)
    if is_type_var(class_):
        return get_lazy_serializer(factory)
    if is_dataclass(class_) or (is_generic_concrete(class_) and is_dataclass(class_.__origin__)):
        return get_complex_serializer(
            factory,
            schema,
            get_dataclass_fields(schema, class_),
            getattr,
            False,
        )
    if is_namedtuple(class_):
        return get_complex_serializer(
            factory,
            schema,
            get_namedtuple_fields(schema, class_),
            getattr,
            False,
        )
    if is_typeddict(class_) or (is_generic_concrete(class_) and is_typeddict(class_.__origin__)):
        if class_.__total__:
            return get_complex_serializer(
                factory,
                schema,
                get_typeddict_fields(schema, class_),
                getitem,
                False,
            )
        else:
            return get_complex_serializer(
                factory,
                schema,
                get_typeddict_fields(schema, class_),
                lambda obj, key: obj.get(key, MISSING),
                True,
            )
    if is_any(class_):
        return get_lazy_serializer(factory)
    if class_ in (str, bytearray, bytes, int, float, complex, bool):
        return class_
    if is_optional(class_):
        if class_.__args__:
            return get_optional_serializer(class_.__args__[0])
        else:
            return get_lazy_serializer(factory)
    if is_enum(class_):
        return attrgetter("value")
    if is_union(class_):
        # also, check if Union can be converted to Optional[...] or Optional[Union[...]]
        serializers = tuple(factory.serializer(x) for x in class_.__args__ if not is_none(x))
        if len(serializers) == 0:
            return serialize_none
        if len(serializers) == 1:
            serializer = serializers[0]
        else:
            serializer = get_lazy_serializer(factory)
        if len(serializers) < len(class_.__args__):
            return get_optional_serializer(serializer)
        return serializer
    if is_tuple(class_):
        if not hasargs(class_):
            return get_collection_any_serializer()
        elif len(class_.__args__) == 2 and class_.__args__[1] is Ellipsis:
            item_serializer = factory.serializer(class_.__args__[0])
            return get_collection_serializer(item_serializer)
        else:
            return get_tuple_serializer(tuple(factory.serializer(x) for x in class_.__args__))
    if is_generic_concrete(class_) and is_dict(class_.__origin__):
        key_type_arg = class_.__args__[0] if class_.__args__ else Any
        value_type_arg = class_.__args__[1] if class_.__args__ else Any
        return get_dict_serializer(factory.serializer(key_type_arg),
                                   factory.serializer(value_type_arg))
    if is_dict(class_):
        return get_dict_serializer(get_lazy_serializer(factory), get_lazy_serializer(factory))
    if is_generic_concrete(class_) and is_iterable(class_.__origin__):
        item_serializer = factory.serializer(class_.__args__[0] if class_.__args__ else Any)
        return get_collection_serializer(item_serializer)
    if is_iterable(class_):
        item_serializer = get_lazy_serializer(factory)
        return get_collection_serializer(item_serializer)

    if isinstance(class_, type):
        if instance_wont_have_dict(class_):
            raise ValueError(f"Can not create serializer for {class_}")

        if hasattr(class_, '__slots__') and '__dict__' in class_.__slots__:
            raise ValueError(
                f"Can not create serializer for {class_}"
                f" that has __dict__ inside __slots__"
            )

    return get_vars_serializer(factory)
