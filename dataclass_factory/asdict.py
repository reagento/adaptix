#!/usr/bin/env python
# -*- coding: utf-8 -*-
from typing import Any

from dataclasses import is_dataclass, fields

from dataclass_factory.parsers import get_collection_factory
from dataclass_factory.type_detection import is_collection

serializers = {}


def get_dataclass_serializer(serializers):
    def serialize(data):
        return {
            k: v(getattr(data, k)) for k, v in serializers.items()
        }

    return serialize


def get_collection_serializer(class_, serializer):
    return lambda data: class_(serializer(x) for x in data)


def asis(data):
    return data


def get_serializer(class_):
    if class_ in serializers:
        return serializers[class_]
    s = get_serializer_imp(class_)
    serializers[class_] = s
    return s


def get_serializer_imp(class_):
    if is_dataclass(class_):
        return get_dataclass_serializer({
            field.name: get_serializer(field.type) for field in fields(class_)
        })
    elif is_collection(class_):
        collection_factory = get_collection_factory(class_)
        item_serializer = get_serializer(class_.__args__[0] if class_.__args__ else Any)
        return get_collection_serializer(collection_factory, item_serializer)
    else:
        return asis
