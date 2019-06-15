import decimal
import inspect
from collections import deque
from dataclasses import fields, is_dataclass

import itertools
from typing import (
    List, Set, FrozenSet, Deque, Any, Callable,
    Dict, Collection, Type, get_type_hints,
)

from .common import Parser
from .exceptions import InvalidFieldError
from .schema import Schema, get_dataclass_fields
from .type_detection import (
    is_tuple, is_collection, is_any, hasargs, is_optional,
    is_none, is_union, is_dict, is_enum,
    is_generic, fill_type_args
)


def element_parser(parser: Callable, data: Any, key: Any):
    try:
        return parser(data)
    except InvalidFieldError as e:
        e._append_path(str(key))
        raise
    except (ValueError, TypeError) as e:
        raise InvalidFieldError(str(e), [str(key)])


def parse_stub(data):
    return data


def parse_none(data):
    if data is not None:
        raise ValueError("None expected")


def get_parser_with_check(cls) -> Parser:
    def parser(data):
        if isinstance(data, cls):
            return data
        raise ValueError("data type is not %s" % cls)

    return parser


def get_collection_parser(collection_factory: Callable, item_parser: Callable, debug_path: bool) -> Parser:
    if debug_path:
        def collection_parser(data):
            return collection_factory(
                element_parser(item_parser, x, i) for i, x in enumerate(data)
            )
    else:
        def collection_parser(data):
            return collection_factory(
                item_parser(x) for x in data
            )
    return collection_parser


def get_union_parser(parsers: Collection[Callable]) -> Parser:
    def union_parser(data):
        for p in parsers:
            try:
                return p(data)
            except (ValueError, TypeError):
                continue
        raise ValueError("No suitable parsers in union found for `%s`" % data)

    return union_parser


tuple_any_parser = tuple


def get_tuple_parser(parsers: Collection[Callable], debug_path: bool) -> Parser:
    if debug_path:
        def tuple_parser(data):
            if len(data) != len(parsers):
                raise ValueError("Incorrect length of data, expected %s, got %s" % (len(parsers), len(data)))
            return tuple(element_parser(parser, x, i) for x, parser, i in zip(data, parsers, itertools.count()))
    else:
        def tuple_parser(data):
            if len(data) != len(parsers):
                raise ValueError("Incorrect length of data, expected %s, got %s" % (len(parsers), len(data)))
            return tuple(parser(x) for x, parser in zip(data, parsers))
    return tuple_parser


def get_dataclass_parser(class_: Type,
                         parsers: Dict[str, Callable],
                         schema: Schema,
                         debug_path: bool, ) -> Parser:
    field_info = tuple(
        (name, item, parsers[name])
        for name, item in get_dataclass_fields(schema, class_)
    )
    if debug_path:
        def dataclass_parser(data):
            return class_(**{
                field: element_parser(parser, data[name], field)
                for field, name, parser in field_info
                if name in data
            })
    else:
        def dataclass_parser(data):
            return class_(**{
                field: parser(data[name]) for field, name, parser in field_info if name in data
            })
    return dataclass_parser


def get_optional_parser(parser) -> Parser:
    return lambda data: parser(data) if data is not None else None


def decimal_parse(data):
    try:
        return decimal.Decimal(data)
    except (decimal.InvalidOperation, TypeError):
        raise ValueError(f'Invalid decimal string representation {data}')


def get_collection_factory(cls):
    origin = cls.__origin__ or cls
    res = {
        List: list,
        list: list,
        Set: set,
        set: set,
        FrozenSet: frozenset,
        frozenset: frozenset,
        Deque: deque,
        deque: deque,
    }.get(origin)
    if not res:
        raise NotImplementedError("Class %s not supported" % cls)
    return res


def get_dict_parser(key_parser, value_parser) -> Parser:
    return lambda data: {key_parser(k): value_parser(v) for k, v in data.items()}


def get_class_parser(cls, parsers: Dict[str, Callable], debug_path: bool) -> Parser:
    if debug_path:
        def class_parser(data):
            return cls(**{
                k: element_parser(parser, data.get(k), k) for k, parser in parsers.items() if k in data
            })
    else:
        def class_parser(data):
            return cls(**{
                k: parser(data.get(k)) for k, parser in parsers.items() if k in data
            })
    return class_parser


def get_lazy_parser(factory, class_):
    def lazy_parser(data):
        return factory.load(data, class_)

    return lazy_parser


def create_parser(factory, schema: Schema, debug_path: bool, cls):
    if is_any(cls):
        return parse_stub
    if is_none(cls):
        return parse_none
    if is_optional(cls):
        return get_optional_parser(factory.parser(cls.__args__[0]))
    if cls in (str, bytearray, bytes):
        return get_parser_with_check(cls)
    if cls in (int, float, complex, bool):
        return cls
    if cls in (decimal.Decimal,):
        return decimal_parse
    if is_enum(cls):
        return cls
    if is_tuple(cls):
        if not hasargs(cls):
            return tuple_any_parser
        elif len(cls.__args__) == 2 and cls.__args__[1] is Ellipsis:
            item_parser = factory.parser(cls.__args__[0])
            return get_collection_parser(tuple, item_parser, debug_path)
        else:
            return get_tuple_parser(tuple(factory.parser(x) for x in cls.__args__), debug_path)
    if is_dict(cls):
        key_type_arg = cls.__args__[0] if cls.__args__ else Any
        value_type_arg = cls.__args__[1] if cls.__args__ else Any
        return get_dict_parser(factory.parser(key_type_arg), factory.parser(value_type_arg))
    if is_collection(cls):
        collection_factory = get_collection_factory(cls)
        item_parser = factory.parser(cls.__args__[0] if cls.__args__ else Any)
        return get_collection_parser(collection_factory, item_parser, debug_path)
    if is_union(cls):
        return get_union_parser(tuple(factory.parser(x) for x in cls.__args__))
    if is_generic(cls) and is_dataclass(cls.__origin__):
        args = dict(zip(cls.__origin__.__parameters__, cls.__args__))
        parsers = {
            field.name: factory.parser(fill_type_args(args, field.type))
            for field in fields(cls.__origin__)
        }
        return get_dataclass_parser(
            cls.__origin__,
            parsers,
            schema,
            debug_path,
        )
    if is_dataclass(cls):
        resolved_hints = get_type_hints(cls)
        parsers = {field.name: factory.parser(resolved_hints[field.name]) for field in fields(cls)}
        return get_dataclass_parser(
            cls,
            parsers,
            schema,
            debug_path,
        )
    try:
        arguments = inspect.signature(cls.__init__).parameters
        parsers = {
            k: factory.parser(v.annotation) for k, v in arguments.items()
        }
        return get_class_parser(cls, parsers, debug_path)
    except AttributeError:
        raise ValueError("Cannot find parser for `%s`" % repr(cls))
