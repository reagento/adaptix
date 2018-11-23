import decimal
import itertools
from collections import deque
from dataclasses import Field, fields, is_dataclass
from typing import List, Set, Tuple, FrozenSet, Deque, Any, Callable, Dict

from .type_detection import is_tuple, is_collection, is_any, hasargs


def parse_stub(data):
    return data


def parse_collection(data, collection_factory, item_parser):
    return collection_factory(
        item_parser(x) for x in data
    )


def parse_tuple(data, parsers):
    return tuple(
        parser(x) for x, parser in zip(data, parsers)
    )


def parse_dataclass(data, cls, parsers: Dict[str, Callable]):
    return cls(**{
        field: parser(data[field]) for field, parser in parsers.items()
    })


def get_collection_factory(cls):
    origin = cls.__origin__ or cls
    res = {
        List: list,
        list: list,
        Set: set,
        set: set,
        Tuple: tuple,
        tuple: tuple,
        FrozenSet: frozenset,
        frozenset: frozenset,
        Deque: deque,
        deque: deque
    }.get(origin)
    if not res:
        raise NotImplementedError("Class %s not supported" % cls)
    return res


class ParserFactory:
    def __init__(self):
        self.cache = {}

    def get_parser(self, cls):
        if cls not in self.cache:
            self.cache[cls] = self._new_parser(cls)
        return self.cache[cls]

    def _new_parser(self, cls):
        if is_any(cls):
            return parse_stub
        if cls in (int, float, complex, bool, decimal.Decimal, str):
            return cls
        if is_tuple(cls):
            if not hasargs(cls):
                parsers = itertools.cycle([parse_stub])
            elif len(cls.__args__) == 2 and cls.__args__[1] is Ellipsis:
                parsers = itertools.cycle([self.get_parser(cls.__args__[0])])
            else:
                parsers = tuple(self.get_parser(x) for x in cls.__args__)
            return lambda data: tuple(
                parser(x) for x, parser in zip(data, parsers)
            )
        if is_collection(cls):
            collection_factory = get_collection_factory(cls)
            item_parser = self.get_parser(cls.__args__[0] if cls.__args__ else Any)
            return lambda data: collection_factory(
                item_parser(x) for x in data
            )
        if is_dataclass(cls):
            parsers = {field.name: self.get_parser(field.type) for field in fields(cls)}
            return lambda data: cls(**{
                field: parser(data[field]) for field, parser in parsers.items()
            })
