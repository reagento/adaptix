#!/usr/bin/env python
# -*- coding: utf-8 -*-
from marshal import loads, dumps
from operator import attrgetter, getitem
from typing import Any, Type, List, Dict, Optional, Union, Sequence, Callable

from dataclasses import is_dataclass, MISSING

from .common import Serializer, T, K, AbstractFactory
from .fields import get_dataclass_fields, FieldInfo, get_typeddict_fields
from .path_utils import init_structure, Path
from .schema import Schema
from .type_detection import (
    is_collection, is_tuple, hasargs, is_dict, is_optional,
    is_union, is_any, is_generic_concrete, is_type_var,
    is_enum,
    is_typeddict)


def to_tuple(key: Union[str, Path]) -> Path:
    if isinstance(key, tuple):
        return key
    return key,


def get_complex_serializer(factory: AbstractFactory,
                           schema: Schema[T],
                           fields: Sequence[FieldInfo],
                           getter: Callable[[Any, Any], Any]) -> Serializer[T]:
    has_default = any(f.default != MISSING for f in fields)
    field_info = tuple(
        (f.field_name, factory.serializer(f.type), f.data_name, f.default)
        for f in fields
    )
    if schema.name_mapping and any(isinstance(key, tuple) for key in schema.name_mapping.values()):
        paths = tuple(to_tuple(f.data_name) for f in fields)
        pickled = dumps(init_structure(paths))
        if has_default:
            raise ValueError("Cannot use `omit_default` option with flattening schema")

        def serialize(data):
            container, field_containers = loads(pickled)
            for (inner_container, data_name), (field_name, serializer, *_) in zip(field_containers, field_info):
                inner_container[data_name] = serializer(getter(data, field_name))
            return container
    else:
        if has_default:
            def serialize(data):
                return {
                    field_name: value
                    for field_name, serializer, data_name, default in field_info
                    for value in (serializer(getter(data, field_name)),)
                    if value != default
                }
        else:
            # optimized version
            def serialize(data):
                return {
                    data_name: serializer(getter(data, field_name))
                    for field_name, serializer, data_name, default in field_info
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


def get_dict_serializer(key_serializer: Serializer[K], serializer: Serializer[T]) -> Serializer[Dict[Any, Any]]:
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


def create_serializer_impl(factory, schema: Schema, debug_path: bool, class_: Type) -> Serializer:
    if is_type_var(class_):
        return get_lazy_serializer(factory)
    if is_dataclass(class_) or (is_generic_concrete(class_) and is_dataclass(class_.__origin__)):
        return get_complex_serializer(
            factory,
            schema,
            get_dataclass_fields(schema, class_),
            getattr,
        )
    if is_typeddict(class_) or (is_generic_concrete(class_) and is_typeddict(class_.__origin__)):
        return get_complex_serializer(
            factory,
            schema,
            get_typeddict_fields(schema, class_),
            getitem,
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
    if is_generic_concrete(class_) and is_dict(class_.__origin__):
        key_type_arg = class_.__args__[0] if class_.__args__ else Any
        value_type_arg = class_.__args__[1] if class_.__args__ else Any
        return get_dict_serializer(factory.serializer(key_type_arg), factory.serializer(value_type_arg))
    if is_dict(class_):
        return get_dict_serializer(get_lazy_serializer(factory), get_lazy_serializer(factory))
    if is_generic_concrete(class_) and is_collection(class_.__origin__):
        item_serializer = factory.serializer(class_.__args__[0] if class_.__args__ else Any)
        return get_collection_serializer(item_serializer)
    if is_collection(class_):
        item_serializer = get_lazy_serializer(factory)
        return get_collection_serializer(item_serializer)
    else:
        return stub_serializer
