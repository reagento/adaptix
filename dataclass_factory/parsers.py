import decimal
import inspect
from collections import deque
from dataclasses import fields, is_dataclass

import itertools
from typing import List, Set, FrozenSet, Deque, Any, Callable, Dict, Collection, ClassVar, Type

from .exceptions import InvalidFieldError
from .naming import NamingPolicy, convert_name
from .type_detection import (
    is_tuple, is_collection, is_any, hasargs, is_optional, is_none, is_union, is_dict, is_enum
)

Parser = Callable[[Any], Any]


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
        raise ValueError("data type is not " + cls)

    return parser


def get_collection_parser(collection_factory: Callable, item_parser: Callable, debug_path: bool) -> Parser:
    if debug_path:
        return lambda data: collection_factory(
            element_parser(item_parser, x, i) for i, x in enumerate(data)
        )
    else:
        return lambda data: collection_factory(
            item_parser(x) for x in data
        )


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


def get_dataclass_parser(cls: Callable,
                         parsers: Dict[str, Callable],
                         trim_trailing_underscore: bool,
                         debug_path: bool,
                         naming_policy: NamingPolicy) -> Parser:
    field_info = tuple(
        (f, convert_name(f, trim_trailing_underscore, naming_policy), p) for f, p in parsers.items()
    )
    if debug_path:
        return lambda data: cls(**{
            field: element_parser(parser, data[name], field)
            for field, name, parser in field_info
            if name in data
        })
    else:
        return lambda data: print(data) or cls(**{
            field: parser(data[name]) for field, name, parser in field_info if name in data
        })


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
        return lambda data: cls(**{
            k: element_parser(parser, data.get(k), k) for k, parser in parsers.items() if k in data
        })
    else:
        return lambda data: cls(**{
            k: parser(data.get(k)) for k, parser in parsers.items() if k in data
        })


class ParserFactory:
    def __init__(self,
                 trim_trailing_underscore: bool = True,
                 debug_path: bool = False,
                 type_factories: Dict[Type, Parser] = None,
                 naming_policies: Dict[Type, NamingPolicy] = None,
                 ):
        """
        :param trim_trailing_underscore: allows to trim trailing underscore in dataclass field names when looking them in corresponding dictionary.
            For example field `id_` can be stored is `id`
        :param debug_path: allows to see path to an element, that cannot be parsed in raised Exception.
            This causes some performance decrease
        :param type_factories: dictionary with type as a key and functions that can be used to create instances of corresponding types as value
        :param naming_policy: policy for names in dict (snake_case, CamelCase, etc.)
        """
        self.cache = {}
        if type_factories:
            self.cache.update(type_factories)
        self.trim_trailing_underscore = trim_trailing_underscore
        self.debug_path = debug_path
        self.naming_policies = naming_policies
        if self.naming_policies is None:
            self.naming_policies = {}

    def get_parser(self, cls: ClassVar) -> Parser:
        if cls not in self.cache:
            self.cache[cls] = self._new_parser(cls)
        return self.cache[cls]

    def _new_parser(self, cls):
        if is_any(cls):
            return parse_stub
        if is_none(cls):
            return parse_none
        if is_optional(cls):
            return get_optional_parser(self.get_parser(cls.__args__[0]))
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
                item_parser = self.get_parser(cls.__args__[0])
                return get_collection_parser(tuple, item_parser, self.debug_path)
            else:
                return get_tuple_parser(tuple(self.get_parser(x) for x in cls.__args__), self.debug_path)
        if is_dict(cls):
            key_type_arg = cls.__args__[0] if cls.__args__ else Any
            value_type_arg = cls.__args__[1] if cls.__args__ else Any
            return get_dict_parser(self.get_parser(key_type_arg), self.get_parser(value_type_arg))
        if is_collection(cls):
            collection_factory = get_collection_factory(cls)
            item_parser = self.get_parser(cls.__args__[0] if cls.__args__ else Any)
            return get_collection_parser(collection_factory, item_parser, self.debug_path)
        if is_union(cls):
            return get_union_parser(tuple(self.get_parser(x) for x in cls.__args__))
        if is_dataclass(cls):
            parsers = {field.name: self.get_parser(field.type) for field in fields(cls)}
            return get_dataclass_parser(
                cls,
                parsers,
                self.trim_trailing_underscore,
                self.debug_path,
                self.naming_policies.get(cls),
            )
        try:
            arguments = inspect.signature(cls.__init__).parameters
            parsers = {
                k: self.get_parser(v.annotation) for k, v in arguments.items()
            }
            return get_class_parser(cls, parsers, self.debug_path)
        except AttributeError:
            raise ValueError("Cannot find parser for `%s`" % repr(cls))
