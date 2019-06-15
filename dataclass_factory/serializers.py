#!/usr/bin/env python
# -*- coding: utf-8 -*-
from dataclasses import is_dataclass, fields

from typing import Any, Type, get_type_hints

from .common import Serializer
from .schema import Schema, get_dataclass_fields
from .type_detection import (
    is_collection, is_tuple, hasargs, is_dict, is_optional,
    is_union, is_any, is_generic, is_type_var,
)


def get_dataclass_serializer(class_: Type, serializers, schema: Schema) -> Serializer:
    field_info = tuple(
        (name, item, serializers[name])
        for name, item in get_dataclass_fields(schema, class_)
    )

    def serialize(data):
        return {
            n: v(getattr(data, k)) for k, n, v in field_info
        }

    return serialize


def get_collection_serializer(serializer) -> Serializer:
    return lambda data: [serializer(x) for x in data]


def get_tuple_serializer(serializers) -> Serializer:
    return lambda data: [serializer(x) for x, serializer in zip(data, serializers)]


def get_collection_any_serializer() -> Serializer:
    return lambda data: [x for x in data]


def stub_serializer(data):
    return data


def get_dict_serializer(serializer):
    return lambda data: {
        k: serializer(v) for k, v in data.items()
    }


def lazy_serializer(factory):
    return lambda data: factory.serializer(type(data))(data)


def optional_serializer(serializer):
    return lambda data: None if data is None else serializer(data)


def create_serializer(factory, schema: Schema, debug_path: bool, class_) -> Serializer:
    if is_type_var(class_):
        return lazy_serializer(factory)
    if is_dataclass(class_):
        resolved_hints = get_type_hints(class_)
        return get_dataclass_serializer(
            class_,
            {field.name: factory.serializer(resolved_hints[field.name]) for field in fields(class_)},
            schema,
        )
    if is_any(class_):
        return lazy_serializer(factory)
    if class_ in (str, bytearray, bytes, int, float, complex, bool):
        return class_
    if is_optional(class_):
        if class_.__args__:
            return optional_serializer(class_.__args__[0])
        else:
            return lazy_serializer(factory)
    if is_union(class_):
        # create serializers:
        for type_ in class_.__args__:
            factory.serializer(type_)
        return lazy_serializer(factory)
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
