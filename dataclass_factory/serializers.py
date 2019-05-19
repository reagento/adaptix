#!/usr/bin/env python
# -*- coding: utf-8 -*-
from dataclasses import is_dataclass, fields

from typing import Callable, Any, Dict, Type

from .naming import NameStyle, convert_name
from .type_detection import is_collection, is_tuple, hasargs, is_dict

Serializer = Callable[[Any], Any]


def get_dataclass_serializer(serializers, trim_trailing_underscore, name_style) -> Serializer:
    field_info = tuple(
        (f, convert_name(f, trim_trailing_underscore, name_style), s) for f, s in serializers.items()
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


class SerializerFactory:
    def __init__(self,
                 trim_trailing_underscore: bool = True,
                 debug_path: bool = False,
                 type_serializers: Dict[Type, Serializer] = None,
                 name_styles: Dict[Type, NameStyle] = None,
                 ):
        """
        :param trim_trailing_underscore: allows to trim trailing underscore in dataclass field names when looking them in corresponding dictionary.
            For example field `id_` can be stored is `id`
        :param debug_path: allows to see path to an element, that cannot be parsed in raised Exception.
            This causes some performance decrease
        :param type_serializers: dictionary with type as a key and functions that can be used to serialize data of corresponding type
        :param name_styles: policy for names in dict made from dataclasses (snake_case, CamelCase, etc.)
        """
        self.cache = {}
        if type_serializers:
            self.cache.update(type_serializers)
        self.trim_trailing_underscore = trim_trailing_underscore
        self.debug_path = debug_path
        if name_styles is None:
            name_styles = {}
        self.name_styles = name_styles

    def get_serializer(self, cls: Any) -> Serializer:
        if cls not in self.cache:
            self.cache[cls] = self._new_serializer(cls)
        return self.cache[cls]

    def _new_serializer(self, class_) -> Serializer:
        if is_dataclass(class_):
            return get_dataclass_serializer(
                {field.name: self.get_serializer(field.type) for field in fields(class_)},
                trim_trailing_underscore=self.trim_trailing_underscore,
                name_style=self.name_styles.get(class_)
            )
        if class_ in (str, bytearray, bytes, int, float, complex, bool):
            return class_
        if is_tuple(class_):
            if not hasargs(class_):
                return get_collection_any_serializer
            elif len(class_.__args__) == 2 and class_.__args__[1] is Ellipsis:
                item_serializer = self.get_serializer(class_.__args__[0])
                return get_collection_serializer(item_serializer)
            else:
                return get_tuple_serializer(tuple(self.get_serializer(x) for x in class_.__args__))
        if is_dict(class_):
            key_type_arg = class_.__args__[0] if class_.__args__ else Any
            if key_type_arg != str:
                raise TypeError("Cannot use <%s> as dict key in serializer" % key_type_arg.__name__)
            value_type_arg = class_.__args__[1] if class_.__args__ else Any
            return get_dict_serializer(self.get_serializer(value_type_arg))
        if is_collection(class_):
            item_serializer = self.get_serializer(class_.__args__[0] if class_.__args__ else Any)
            return get_collection_serializer(item_serializer)
        else:
            return stub_serializer
