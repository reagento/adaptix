#!/usr/bin/env python
# -*- coding: utf-8 -*-
from dataclasses import is_dataclass, fields
from marshal import loads, dumps
from typing import Any, Type, get_type_hints, List, Dict, Optional, Union

from .common import Serializer, T
from .path_utils import init_structure, Path
from .schema import Schema, get_dataclass_fields
from .type_detection import (
    is_collection, is_tuple, hasargs, is_dict, is_optional,
    is_union, is_any, is_generic, is_type_var,
)


def to_tuple(key: Union[str, Path]) -> Path:
    if isinstance(key, tuple):
        return key
    return key,


def get_dataclass_serializer(class_: Type[T], serializers, schema: Schema[T]) -> Serializer[T]:
    if schema.name_mapping and any(isinstance(key, tuple) for key in schema.name_mapping.values()):
        field_info_ex = tuple(
            (i, name, to_tuple(path), serializers[name])
            for i, (name, path) in enumerate(get_dataclass_fields(schema, class_))
        )
        pickled = dumps(init_structure((path for _, _, path, _ in field_info_ex)))

        def serialize(data):
            container, field_containers = loads(pickled)
            for i, name, path, serializer in field_info_ex:
                c, x = field_containers[i]
                c[x] = serializer(getattr(data, name))
            return container
    else:
        field_info = tuple(
            (name, item, serializers[name])
            for name, item in get_dataclass_fields(schema, class_)
        )

        def serialize(data):
            return {
                n: v(getattr(data, k)) for k, n, v in field_info
            }
    return serialize


def get_collection_serializer(serializer: Serializer[T]) -> Serializer[List[T]]:
    return lambda data: [serializer(x) for x in data]


def get_tuple_serializer(serializers) -> Serializer[List]:
    return lambda data: [serializer(x) for x, serializer in zip(data, serializers)]


def get_collection_any_serializer() -> Serializer[List[Any]]:
    return lambda data: [x for x in data]


def stub_serializer(data: T) -> T:
    return data


def get_dict_serializer(serializer: Serializer[T]) -> Serializer[Dict[Any, T]]:
    return lambda data: {
        k: serializer(v) for k, v in data.items()
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
    if is_type_var(class_):
        return get_lazy_serializer(factory)
    if is_dataclass(class_):
        resolved_hints = get_type_hints(class_)
        return get_dataclass_serializer(
            class_,
            {field.name: factory.serializer(resolved_hints[field.name]) for field in fields(class_)},
            schema,
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
    if is_union(class_):
        # create serializers:
        for type_ in class_.__args__:
            factory.serializer(type_)
        return get_lazy_serializer(factory)
    if is_tuple(class_):
        if not hasargs(class_):
            return get_collection_any_serializer()
        elif len(class_.__args__) == 2 and class_.__args__[1] is Ellipsis:
            item_serializer = factory.serializer(class_.__args__[0])
            return get_collection_serializer(item_serializer)
        else:
            return get_tuple_serializer(tuple(factory.serializer(x) for x in class_.__args__))
    if is_dict(class_):
        key_type_arg = class_.__args__[0] if class_.__args__ else Any
        if key_type_arg != str:
            raise TypeError("Cannot use <%s> as dict key in serializer" % key_type_arg.__name__)
        value_type_arg = class_.__args__[1] if class_.__args__ else Any
        return get_dict_serializer(factory.serializer(value_type_arg))
    if is_collection(class_):
        item_serializer = factory.serializer(class_.__args__[0] if class_.__args__ else Any)
        return get_collection_serializer(item_serializer)
    if is_generic(class_) and is_dataclass(class_.__origin__):
        args = dict(zip(class_.__origin__.__parameters__, class_.__args__))
        serializers = {
            field.name: factory.serializer(args.get(field.type, field.type))
            for field in fields(class_.__origin__)
        }
        return get_dataclass_serializer(
            class_.__origin__,
            serializers,
            schema,
        )
    else:
        return stub_serializer
