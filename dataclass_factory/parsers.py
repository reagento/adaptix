import decimal
from collections import deque
from dataclasses import fields, is_dataclass
from typing import List, Set, FrozenSet, Deque, Any, Callable, Dict, Collection

from dataclass_factory.dataclass_utils import is_dict, is_enum
from .type_detection import is_tuple, is_collection, is_any, hasargs, is_real_optional, is_none, is_union


def parse_stub(data):
    return data


def parse_none(data):
    if data is not None:
        raise ValueError("None expected")


def get_parser_with_check(cls):
    def parser(data):
        if not isinstance(data, cls):
            raise ValueError("data is not str")
        return data

    return parser


def get_collection_parser(collection_factory: Callable, item_parser: Callable):
    return lambda data: collection_factory(
        item_parser(x) for x in data
    )


def get_union_parser(parsers: Collection[Callable]):
    def union_parser(data):
        for p in parsers:
            try:
                return p(data)
            except (ValueError, TypeError):
                continue
        raise ValueError("No suitable parsers in union found for `%s`" % data)

    return union_parser


def tuple_any_parser(data):
    return tuple(data)


def get_tuple_parser(parsers: Collection[Callable]):
    def tuple_parser(data):
        if len(data) != len(parsers):
            raise ValueError("Incorrect length of data, expected %s, got %s" % (len(parsers), len(data)))
        return tuple(parser(x) for x, parser in zip(data, parsers))

    return tuple_parser


def get_dataclass_parser(cls: Callable, parsers: Dict[str, Callable], trim_trailing_underscore: bool):
    field_info = {
        f: (f.rstrip("_") if trim_trailing_underscore else f, p) for f, p in parsers.items()
    }
    return lambda data: cls(**{
        field: info[1](data[info[0]]) for field, info in field_info.items() if info[0] in data
    })


def get_optional_parser(parser):
    return lambda data: parser(data) if data is not None else None


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


def get_dict_parser(key_parser, value_parser):
    return lambda data: {key_parser(k): value_parser(v) for k, v in data.items()}


class ParserFactory:
    def __init__(self, trim_trailing_underscore=True):
        self.cache = {}
        self.trim_trailing_underscore = trim_trailing_underscore

    def get_parser(self, cls):
        if cls not in self.cache:
            self.cache[cls] = self._new_parser(cls)
        return self.cache[cls]

    def _new_parser(self, cls):
        if is_any(cls):
            return parse_stub
        if is_none(cls):
            return parse_none
        if is_real_optional(cls):
            return get_optional_parser(self.get_parser(cls.__args__[0]))
        if cls in (str, bytearray, bytes):
            return get_parser_with_check(cls)
        if cls in (int, float, complex, bool, decimal.Decimal):
            return cls
        if is_enum(cls):
            return cls
        if is_tuple(cls):
            if not hasargs(cls):
                return tuple_any_parser
            elif len(cls.__args__) == 2 and cls.__args__[1] is Ellipsis:
                item_parser = self.get_parser(cls.__args__[0])
                return get_collection_parser(tuple, item_parser)
            else:
                return get_tuple_parser(tuple(self.get_parser(x) for x in cls.__args__))
        if is_dict(cls):
            key_type_arg = cls.__args__[0] if cls.__args__ else Any
            value_type_arg = cls.__args__[1] if cls.__args__ else Any
            return get_dict_parser(self.get_parser(key_type_arg), self.get_parser(value_type_arg))
        if is_collection(cls):
            collection_factory = get_collection_factory(cls)
            item_parser = self.get_parser(cls.__args__[0] if cls.__args__ else Any)
            return get_collection_parser(collection_factory, item_parser)
        if is_union(cls):
            return get_union_parser(tuple(self.get_parser(x) for x in cls.__args__))
        if is_dataclass(cls):
            parsers = {field.name: self.get_parser(field.type) for field in fields(cls)}
            return get_dataclass_parser(cls, parsers, self.trim_trailing_underscore)
