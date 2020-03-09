import decimal
from collections import deque
from typing import (
    List, Set, FrozenSet, Deque, Any, Callable,
    Collection, Type, Optional, Tuple, Union, Sequence
)

from dataclasses import is_dataclass

from .common import Parser, T, AbstractFactory
from .exceptions import InvalidFieldError
from .fields import FieldInfo, get_dataclass_fields, get_typeddict_fields, get_class_fields
from .path_utils import Path
from .schema import Schema
from .type_detection import (
    is_tuple, is_collection, is_any, hasargs, is_optional,
    is_none, is_union, is_dict, is_enum,
    args_unspecified,
    is_literal, is_literal36, is_typeddict,
    is_generic_concrete)

PARSER_EXCEPTIONS = (ValueError, TypeError, AttributeError, LookupError)


def get_element_parser(parser: Parser[T], key: Any) -> Parser[T]:
    def element_parser(data: Any) -> T:
        try:
            return parser(data)
        except InvalidFieldError as e:
            e._append_path(str(key))
            raise
        except PARSER_EXCEPTIONS as e:
            raise InvalidFieldError(str(e), [str(key)])

    return element_parser


def element_parser(parser: Parser[T], data: Any, key: Any) -> T:
    try:
        return parser(data)
    except InvalidFieldError as e:
        e._append_path(str(key))
        raise
    except PARSER_EXCEPTIONS as e:
        raise InvalidFieldError(str(e), [str(key)])


def parse_stub(data: T) -> T:
    return data


def parse_none(data: Any) -> None:
    if data is not None:
        raise ValueError("None expected")


def get_parser_with_check(cls: Type[T]) -> Parser[T]:
    def parser(data):
        if isinstance(data, cls):
            return data
        raise ValueError("data type is not %s" % cls)

    return parser


def get_collection_parser(
        collection_factory: Callable,
        item_parser: Parser[T],
        debug_path: bool
) -> Parser[Collection[T]]:
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
            except PARSER_EXCEPTIONS as e:
                continue
        raise ValueError("No suitable parsers in union found for `%s`" % data)

    return union_parser


tuple_any_parser = tuple


def get_tuple_parser(parsers: Collection[Callable], debug_path: bool) -> Parser[Tuple]:
    if debug_path:
        parsers = [get_element_parser(parser, i) for i, parser in enumerate(parsers)]

    def tuple_parser(data):
        if len(data) != len(parsers):
            raise ValueError("Incorrect length of data, expected %s, got %s" % (len(parsers), len(data)))
        return tuple(parser(x) for x, parser in zip(data, parsers))

    return tuple_parser


def get_path_parser(parser: Parser[T], path: Path) -> Parser[T]:
    def path_parser(data):
        if data is None:
            return parser(data)
        for x in path:
            data = data[x]
            if data is None:
                return parser(data)
        return parser(data)

    return path_parser


def get_field_parser(item: Union[str, int, Path], parser: Parser[T]) -> Tuple[Union[str, int], Parser[T]]:
    if isinstance(item, tuple):
        if len(item) == 1:
            return item[0], parser
        return item[0], get_path_parser(parser, item[1:])
    else:
        return item, parser


def get_complex_parser(class_: Type[T],
                       factory: AbstractFactory,
                       fields: Sequence[FieldInfo],
                       debug_path: bool, ) -> Parser[T]:
    field_info = tuple(
        (f.field_name, *get_field_parser(f.data_name, factory.parser(f.type)))
        for f in fields
    )

    list_mode = any(isinstance(name, int) for _, name, _ in field_info)
    field_info = tuple(
        (f.field_name, *get_field_parser(f.data_name, factory.parser(f.type)))
        for f in fields
    )
    if debug_path:
        field_info = tuple(
            (field_name, data_name, get_element_parser(parser, field_name))
            for field_name, data_name, parser in field_info
        )

    if list_mode:
        def complex_parser(data):
            count = len(data)
            return class_(**{
                field_name: parser(data[item_idx])
                for field_name, item_idx, parser in field_info
                if item_idx < count
            })
    else:
        def complex_parser(data):
            return class_(**{
                field_name: parser(data[item_name])
                for field_name, item_name, parser in field_info
                if item_name in data
            })

    return complex_parser


def get_typed_dict_parser(class_: Type,
                          factory: AbstractFactory,
                          fields: Sequence[FieldInfo],
                          debug_path: bool, ) -> Parser:
    complex_parser = get_complex_parser(class_, factory, fields, debug_path)
    requires_fieds = set(f.field_name for f in fields)
    if class_.__total__:
        def total_parser(data):
            res = complex_parser(data)
            if not set(res) == requires_fieds:
                raise ValueError("Not all fields provided for %s" % (class_))
            return res

        return total_parser
    return complex_parser


def get_optional_parser(parser: Parser[T]) -> Parser[Optional[T]]:
    def optional_parser(data):
        return parser(data) if data is not None else None

    return optional_parser


def decimal_parse(data) -> decimal.Decimal:
    try:
        return decimal.Decimal(data)
    except (decimal.InvalidOperation, TypeError, ValueError):
        raise ValueError(f'Invalid decimal string representation {data}')


def get_collection_factory(cls) -> Type:
    if is_generic_concrete(cls):
        origin = cls.__origin__ or cls
    else:
        origin = cls
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


def get_literal_parser(factory, values: Sequence[Any]) -> Parser:
    def literal_parser(data: Any):
        for v in values:
            if (type(v), v) == (type(data), data):
                return data
        raise ValueError("Invalid literal data")

    return literal_parser


def get_lazy_parser(factory, class_: Type) -> Parser:
    # return partial(factory.load, class_=class_)
    def lazy_parser(data):
        return factory.load(data, class_)

    return lazy_parser


def create_parser(factory, schema: Schema, debug_path: bool, cls: Type) -> Parser:
    parser = create_parser_impl(factory, schema, debug_path, cls)
    pre = schema.pre_parse
    post = schema.post_parse
    if pre or post:
        def parser_with_steps(data):
            if pre:
                data = pre(data)
            data = parser(data)
            if post:
                return post(data)
            return data

        return parser_with_steps
    return parser


def create_parser_impl(factory, schema: Schema, debug_path: bool, cls: Type) -> Parser:
    if is_any(cls):
        return parse_stub
    if is_none(cls):
        return parse_none
    if is_literal(cls):
        return get_literal_parser(factory, cls.__args__)
    if is_literal36(cls):
        return get_literal_parser(factory, cls.__values__)
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
        if args_unspecified(cls):
            key_type_arg = Any
            value_type_arg = Any
        else:
            key_type_arg = cls.__args__[0]
            value_type_arg = cls.__args__[1]
        return get_dict_parser(factory.parser(key_type_arg), factory.parser(value_type_arg))
    if is_typeddict(cls) or (is_generic_concrete(cls) and is_typeddict(cls.__origin__)):
        return get_typed_dict_parser(
            cls,
            factory,
            get_typeddict_fields(schema, cls),
            debug_path,
        )
    if is_collection(cls):
        if args_unspecified(cls):
            value_type_arg = Any
        else:
            value_type_arg = cls.__args__[0]
        collection_factory = get_collection_factory(cls)
        item_parser = factory.parser(value_type_arg)
        return get_collection_parser(collection_factory, item_parser, debug_path)
    if is_union(cls):
        return get_union_parser(tuple(factory.parser(x) for x in cls.__args__))
    if is_dataclass(cls) or (is_generic_concrete(cls) and is_dataclass(cls.__origin__)):
        return get_complex_parser(
            cls,
            factory,
            get_dataclass_fields(schema, cls),
            debug_path,
        )
    try:
        return get_complex_parser(
            cls,
            factory,
            get_class_fields(schema, cls),
            debug_path,
        )
    except PARSER_EXCEPTIONS:
        raise ValueError("Cannot find parser for `%s`" % repr(cls))
