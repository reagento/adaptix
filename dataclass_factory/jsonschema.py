from dataclasses import is_dataclass, MISSING
import decimal
from typing import Any, Dict, Optional, Type

from .common import AbstractFactory
from .fields import get_dataclass_fields, get_typeddict_fields
from .schema import Schema, Unknown
from .type_detection import (
    hasargs, is_iterable, is_dict, is_enum, is_generic_concrete,
    is_none, is_tuple, is_typeddict, is_union, is_literal,
)


def need_ref(cls) -> bool:
    if cls in (int, str, bool, float, decimal.Decimal):
        return False
    if is_none(cls):
        return False
    if is_literal(cls):
        return False
    if is_union(cls):
        return False
    if is_iterable(cls):
        # TypdeDict is one of heterogeneous structures
        return is_typeddict(cls)
    return True


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
    elif is_tuple(cls) or is_iterable(cls):
        return "array"
    elif is_union(cls) or is_enum(cls):
        return None
    return "object"


def type_or_ref(
    class_, factory: AbstractFactory, json_schema_definitions_path: str,
) -> Dict[str, Any]:
    if need_ref(class_):
        ref = factory.json_schema_ref_name(class_)
        return {"$ref": f"#{json_schema_definitions_path}/{ref}"}
    return factory.json_schema(class_)


def unknown(
    factory: AbstractFactory, schema: Schema, cls: Type,
) -> Dict[str, Any]:
    res: Dict[str, Any] = {}
    if schema.unknown == Unknown.FORBID:
        res["additionalProperties"] = False
    elif schema.unknown in (Unknown.SKIP, Unknown.STORE):
        pass
    else:
        raise NotImplementedError(f"Cannot generate schema with unknown={schema.unknown}")
    return res


def typed_dict_schema(
    factory: AbstractFactory, schema: Schema, cls: Type,
    json_schema_definitions_path: str,
) -> Dict[str, Any]:
    res: Dict[str, Any] = {}
    fields = get_typeddict_fields(schema, cls)
    if schema.name_mapping and any(isinstance(key, tuple) for key in schema.name_mapping.values()):
        raise NotImplementedError("Schema flattening is not yet supported")
    res["properties"] = {}
    res.update(unknown(factory, schema, cls))
    for f in fields:
        res["properties"][f.data_name] = type_or_ref(
            f.type, factory, json_schema_definitions_path,
        )
        if f.default is not MISSING:
            res["properties"][f.data_name]["default"] = f.default
    if cls.__total__:
        res["required"] = [
            f.data_name for f in fields
        ]
    return res


def dataclass_schema(
    factory: AbstractFactory, schema: Schema, cls: Type,
    json_schema_definitions_path: str,
) -> Dict[str, Any]:
    res: Dict[str, Any] = {}
    fields = get_dataclass_fields(schema, cls)
    if schema.name_mapping and any(isinstance(key, tuple) for key in schema.name_mapping.values()):
        raise NotImplementedError("Schema flattening is not yet supported")
    res["properties"] = {}
    res.update(unknown(factory, schema, cls))
    for f in fields:
        res["properties"][f.data_name] = type_or_ref(
            f.type, factory, json_schema_definitions_path,
        )
        if f.default is not MISSING and f.type:
            res["properties"][f.data_name]["default"] = factory.serializer(f.type)(f.default)
    res["required"] = [
        f.data_name for f in fields if f.default is MISSING
    ]
    return res


def create_schema(
    factory: AbstractFactory, schema: Schema, cls: Type,
    json_schema_definitions_path: str,
) -> Dict[str, Any]:  # noqa C901,CCR001
    if cls is Any:
        return {}

    res: Dict[str, Any] = {}
    if schema.name:
        res["title"] = schema.name
    if schema.description:
        res["description"] = schema.description
    type_ = get_type(cls)
    if type_:
        res["type"] = type_

    if cls in (str, ):
        pass
    elif cls in (int, float, complex, bool):
        pass
    elif is_enum(cls):
        res["enum"] = [x.value for x in cls]
    elif is_dict(cls):
        res["additionalProperties"] = type_or_ref(
            cls.__args__[1], factory, json_schema_definitions_path,
        )
    elif is_tuple(cls):
        if hasargs(cls):
            if len(cls.__args__) == 2 and cls.__args__[1] is Ellipsis:
                res["items"] = type_or_ref(
                    cls.__args__[0], factory, json_schema_definitions_path,
                )
            else:
                res["items"] = [
                    type_or_ref(x, factory, json_schema_definitions_path)
                    for x in cls.__args__
                ]
    elif is_typeddict(cls) or (is_generic_concrete(cls) and is_typeddict(cls.__origin__)):
        res.update(typed_dict_schema(factory, schema, cls, json_schema_definitions_path))
    elif is_iterable(cls):
        res["items"] = type_or_ref(
            cls.__args__[0], factory, json_schema_definitions_path,
        )
    elif is_union(cls):
        res["anyOf"] = [
            type_or_ref(x, factory, json_schema_definitions_path)
            for x in cls.__args__
        ]
    elif is_literal(cls):
        res["enum"] = list(factory.serializer(type(x))(x) for x in cls.__args__)
    elif is_dataclass(cls) or (is_generic_concrete(cls) and is_dataclass(cls.__origin__)):
        res.update(dataclass_schema(factory, schema, cls, json_schema_definitions_path))
    return res
