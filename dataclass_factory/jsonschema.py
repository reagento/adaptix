import decimal
from typing import Dict, Optional
from typing import (
    Type
)

from dataclasses import is_dataclass, MISSING

from .fields import get_dataclass_fields, get_typeddict_fields
from .type_detection import (
    is_tuple, is_collection, hasargs, is_none, is_union, is_dict, is_enum,
    is_typeddict,
    is_generic_concrete,
)

definitions = {}
definitions_rev = {}
schemas = {}


def get_ref(cls, factory):
    schemas[cls] = factory.jsonschema(cls)
    return get_ref_only(cls)


def get_ref_only(cls):
    if cls in (int, str, bool, float, decimal.Decimal):
        return
    if is_none(cls):
        return
    if cls in definitions:
        return definitions[cls]
    name = getattr(cls, "__qualname__", "") or getattr(cls, "__name__", "") or str(cls)
    if name in definitions_rev:
        raise ValueError(
            f"Already found type with name `{name}`: {definitions_rev[name]}. Please, specify another name for {cls}")
    definitions_rev[name] = cls
    definitions[cls] = name
    return name


def get_type(cls) -> Optional[str]:
    if is_none(cls):
        return "null"
    if cls in (int,):
        return "integer"
    elif cls in (float, decimal.Decimal):
        return "number"
    elif cls in (str,):
        return "string"
    elif cls in (bool,):
        return "boolean"
    elif is_dict(cls):
        return "object"
    elif is_tuple(cls) or is_collection(cls):
        return "array"
    elif is_union(cls) or is_enum(cls):
        return
    return "object"


def type_or_ref(cls, factory):
    ref = get_ref(cls, factory)
    if ref:
        return {"$ref": f"#/definitions/{ref}"}
    return {"type": get_type(cls)}


def create_schema(factory, schema, cls: Type) -> Dict:
    # TODO fields flattening and unknown
    if cls in schemas:
        return schemas[cls]
    res = {}
    if hasattr(cls, "__name__"):
        res["title"] = cls.__name__
    type = get_type(cls)
    if type:
        res["type"] = type

    if is_enum(cls):
        res["enum"] = [x.value for x in cls]
    elif is_dict(cls):
        res["additionalProperties"] = type_or_ref(cls.__args__[1], factory)
    elif is_tuple(cls):
        if not hasargs(cls):
            pass
        elif len(cls.__args__) == 2 and cls.__args__[1] is Ellipsis:
            res["items"] = type_or_ref(cls.__args__[0], factory)
        else:
            res["items"] = [type_or_ref(x, factory) for x in cls.__args__]
    elif is_typeddict(cls) or (is_generic_concrete(cls) and is_typeddict(cls.__origin__)):
        fields = get_typeddict_fields(schema, cls)
        res["properties"] = {}
        for f in fields:
            res["properties"][f.data_name] = type_or_ref(f.type, factory)
            if f.default is not MISSING:
                res["properties"][f.data_name]["default"] = f.default
        if cls.__total__:
            res["required"] = [
                f.data_name for f in fields
            ]
    elif is_collection(cls):
        res["items"] = type_or_ref(cls.__args__[0], factory)
    elif is_union(cls):
        res["anyOf"] = [type_or_ref(x, factory) for x in cls.__args__]
    elif is_dataclass(cls) or (is_generic_concrete(cls) and is_dataclass(cls.__origin__)):
        fields = get_dataclass_fields(schema, cls)
        res["properties"] = {}
        for f in fields:
            res["properties"][f.data_name] = type_or_ref(f.type, factory)
            if f.default is not MISSING:
                res["properties"][f.data_name]["default"] = f.default
        res["required"] = [
            f.data_name for f in fields if f.default is MISSING
        ]
    return res
