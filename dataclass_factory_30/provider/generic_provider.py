import collections.abc
from abc import ABC
from dataclasses import dataclass, replace
from enum import EnumMeta
from inspect import isabstract
from typing import Callable, Collection, Container, Dict, Iterable, Literal, Mapping, Tuple, Union

from ..common import Parser, Serializer, TypeHint
from ..struct_path import append_path
from ..type_tools import BaseNormType, is_new_type, normalize_type, strip_tags
from .definitions import ExcludedTypeParseError, ParseError, TypeParseError, UnionParseError
from .essential import CannotProvide, Mediator, Request
from .provider_basics import foreign_parser
from .provider_template import ParserProvider, SerializerProvider, for_type
from .request_cls import ParserRequest, SerializerRequest, TypeHintRM
from .static_provider import StaticProvider, static_provision_action


def stub(arg):
    return arg


class NewTypeUnwrappingProvider(StaticProvider):
    @static_provision_action
    def _provide_unwrapping(self, mediator: Mediator, request: TypeHintRM) -> Parser:
        if not is_new_type(request.type):
            raise CannotProvide

        return mediator.provide(replace(request, type=request.type.__supertype__))


class TypeHintTagsUnwrappingProvider(StaticProvider):
    @static_provision_action
    def _provide_unwrapping(self, mediator: Mediator, request: TypeHintRM) -> Parser:
        unwrapped = strip_tags(normalize_type(request.type))
        if unwrapped.source == request.type:  # type has not changed, continue search
            raise CannotProvide

        return mediator.provide(replace(request, type=unwrapped))


def _is_exact_zero_or_one(arg):
    return type(arg) == int and arg in (0, 1)  # pylint: disable=unidiomatic-typecheck


@dataclass
@for_type(Literal)
class LiteralProvider(ParserProvider, SerializerProvider):
    tuple_size_limit: int = 4

    def _get_container(self, args: Collection) -> Container:
        if len(args) > self.tuple_size_limit:
            return set(args)
        return tuple(args)

    def _provide_parser(self, mediator: Mediator, request: ParserRequest) -> Parser:
        norm = normalize_type(request.type)

        if request.strict_coercion and any(
            isinstance(arg, bool) or _is_exact_zero_or_one(arg)
            for arg in norm.args
        ):
            allowed_values = self._get_container(
                [(type(el), el) for el in norm.args]
            )

            # since True == 1 and False == 0
            def literal_parser_tc(data):
                if (type(data), data) in allowed_values:
                    return data
                raise ParseError

            return literal_parser_tc

        allowed_values = self._get_container(norm.args)

        def literal_parser(data):
            if data in allowed_values:
                return data
            raise ParseError

        return literal_parser

    def _provide_serializer(self, mediator: Mediator, request: SerializerRequest) -> Serializer:
        return stub


@for_type(Union)
class UnionProvider(ParserProvider):
    def _provide_parser(self, mediator: Mediator, request: ParserRequest) -> Parser:
        norm = normalize_type(request.type)

        parsers = tuple(
            mediator.provide(replace(request, type=tp.source))
            for tp in norm.args
        )

        if request.debug_path:
            def union_parser_dp(value):
                errors = []
                for prs in parsers:
                    try:
                        return prs(value)
                    except ParseError as e:
                        errors.append(e)

                raise UnionParseError(sub_errors=errors)

            return union_parser_dp

        def union_parser(value):
            for prs in parsers:
                try:
                    return prs(value)
                except ParseError:
                    pass
            raise ParseError

        return union_parser


CollectionsMapping = collections.abc.Mapping


@for_type(Iterable)
class IterableProvider(ParserProvider, SerializerProvider):
    ABC_TO_IMPL = {
        collections.abc.Iterable: tuple,
        collections.abc.Reversible: tuple,
        collections.abc.Collection: tuple,
        collections.abc.Sequence: tuple,
        collections.abc.MutableSequence: list,
        # exclude ByteString, because it does not process as Iterable
        collections.abc.Set: frozenset,
        collections.abc.MutableSet: set,
    }

    def _get_abstract_impl(self, abstract) -> Callable[[Iterable], Iterable]:
        try:
            return self.ABC_TO_IMPL[abstract]
        except KeyError:
            raise CannotProvide

    def _get_iter_factory(self, origin) -> Callable[[Iterable], Iterable]:
        if isabstract(origin):
            return self._get_abstract_impl(origin)
        if callable(origin):
            return origin
        raise CannotProvide

    def _fetch_norm_and_arg(self, request: TypeHintRM):
        try:
            norm = normalize_type(request.type)
        except ValueError:
            raise CannotProvide

        if len(norm.args) != 1:
            raise CannotProvide

        try:
            arg = norm.args[0].source
        except AttributeError:
            raise CannotProvide

        if issubclass(norm.origin, collections.abc.Mapping):
            raise CannotProvide

        return norm, arg

    def _provide_parser(self, mediator: Mediator, request: ParserRequest) -> Parser:
        norm, arg = self._fetch_norm_and_arg(request)

        iter_factory = self._get_iter_factory(norm.origin)
        arg_parser = mediator.provide(replace(request, type=arg))
        strict_coercion = request.strict_coercion

        if request.debug_path:
            parser = self._make_debug_path_parser(iter_factory, arg_parser, strict_coercion)
        else:
            parser = self._make_non_dp_parser(iter_factory, arg_parser, strict_coercion)

        return foreign_parser(parser)

    def _make_debug_path_parser(self, iter_factory, arg_parser, strict_coercion: bool):
        def element_parser_dp(idx_and_elem):
            try:
                return arg_parser(idx_and_elem[1])
            except Exception as e:
                append_path(e, idx_and_elem[0])
                raise e

        if strict_coercion:
            def iter_parser_dp_sc(value):
                if isinstance(value, CollectionsMapping):
                    raise ExcludedTypeParseError(Mapping)

                try:
                    enum_iter = enumerate(value)
                except TypeError:
                    raise TypeParseError(Iterable)

                return iter_factory(map(element_parser_dp, enum_iter))

            return iter_parser_dp_sc

        def iter_parser_dp(value):
            try:
                enum_iter = enumerate(value)
            except TypeError:
                raise TypeParseError(Iterable)

            return iter_factory(map(element_parser_dp, enum_iter))

        return iter_parser_dp

    def _make_non_dp_parser(self, iter_factory, arg_parser, strict_coercion: bool):
        if strict_coercion:
            def iter_parser_sc(value):
                if isinstance(value, CollectionsMapping):
                    raise ExcludedTypeParseError(Mapping)

                try:
                    map_iter = map(arg_parser, value)
                except TypeError:
                    raise TypeParseError(Iterable)

                return iter_factory(map_iter)

            return iter_parser_sc

        def iter_parser(value):
            try:
                map_iter = map(arg_parser, value)
            except TypeError:
                raise TypeParseError(Iterable)

            return iter_factory(map_iter)

        return iter_parser

    def _provide_serializer(self, mediator: Mediator, request: SerializerRequest) -> Serializer:
        norm, arg = self._fetch_norm_and_arg(request)

        iter_factory = self._get_iter_factory(norm.origin)
        arg_serializer = mediator.provide(replace(request, type=arg))

        def iter_serializer(value):
            return iter_factory(map(arg_serializer, value))

        return iter_serializer


@for_type(Dict)
class DictProvider(ParserProvider, SerializerProvider):
    def _fetch_key_value(self, request: TypeHintRM) -> Tuple[BaseNormType, BaseNormType]:
        norm = normalize_type(request.type)
        return norm.args  # type: ignore

    def _provide_parser(self, mediator: Mediator, request: ParserRequest) -> Parser:
        key, value = self._fetch_key_value(request)

        key_parser = mediator.provide(
            ParserRequest(
                type=key.source,
                strict_coercion=request.strict_coercion,
                debug_path=request.debug_path
            )
        )

        value_parser = mediator.provide(
            ParserRequest(
                type=value.source,
                strict_coercion=request.strict_coercion,
                debug_path=request.debug_path
            )
        )

        if request.debug_path:
            def dict_parser_dp(data):
                try:
                    items_method = data.items
                except AttributeError:
                    raise TypeParseError(Mapping)

                result = {}
                for k, v in items_method():
                    try:
                        parsed_key = key_parser(k)
                    except Exception as e:
                        append_path(e, k)
                        raise e

                    try:
                        parsed_value = value_parser(v)
                    except Exception as e:
                        append_path(e, k)  # yes, it's a key
                        raise e

                    result[parsed_key] = parsed_value

                return result

            return dict_parser_dp

        def dict_parser(data):
            try:
                items_method = data.items
            except AttributeError:
                raise TypeParseError(Mapping)

            result = {}
            for k, v in items_method():
                result[key_parser(k)] = value_parser(v)

            return result

        return dict_parser

    def _provide_serializer(self, mediator: Mediator, request: SerializerRequest) -> Serializer:
        key, value = self._fetch_key_value(request)

        key_serializer = mediator.provide(
            replace(request, type=key.source),
        )

        value_serializer = mediator.provide(
            replace(request, type=value.source),
        )

        def dict_serializer(data: Mapping):
            result = {}
            for k, v in data.items():
                result[key_serializer(k)] = value_serializer(v)

            return result

        return dict_serializer


class BaseEnumProvider(ParserProvider, SerializerProvider, ABC):
    def _check_request(self, mediator: Mediator, request: Request) -> None:
        if not isinstance(request, TypeHintRM):
            raise CannotProvide

        norm = normalize_type(request.type)

        if not isinstance(norm.origin, EnumMeta):
            raise CannotProvide


def _enum_name_serializer(data):
    return data.name


class EnumNameProvider(BaseEnumProvider):
    """This provider represents enum members to the outside world by their name"""

    def _provide_parser(self, mediator: Mediator, request: ParserRequest) -> Parser:
        enum = request.type

        def enum_parser(data):
            return enum[data]

        return foreign_parser(enum_parser)

    def _provide_serializer(self, mediator: Mediator, request: SerializerRequest) -> Serializer:
        return _enum_name_serializer


class EnumValueProvider(BaseEnumProvider):
    """This provider represents enum members to the outside world by their value.
    Input data will be parsed and then interpreted as one of enum member value.
    At serializing value of enum member will be serialized.
    """

    def __init__(self, value_type: TypeHint):
        """Create value provider for Enum.

        :param value_type: Type of enum member value
            that will be used to create parser and serializer of member value
        """
        self._value_type = value_type

    def _provide_parser(self, mediator: Mediator, request: ParserRequest) -> Parser:
        enum = request.type
        value_parser = mediator.provide(replace(request, type=self._value_type))

        def enum_parser(data):
            return enum(value_parser(data))

        return foreign_parser(enum_parser)

    def _provide_serializer(self, mediator: Mediator, request: SerializerRequest) -> Serializer:
        value_serializer = mediator.provide(replace(request, type=self._value_type))

        def enum_serializer(data):
            return value_serializer(data.value)

        return enum_serializer


def _enum_exact_value_serializer(data):
    return data.value


class EnumExactValueProvider(BaseEnumProvider):
    """This provider represents enum members to the outside world
    by their value without any processing
    """

    def _provide_parser(self, mediator: Mediator, request: ParserRequest) -> Parser:
        enum = request.type

        def enum_exact_parser(data):
            # since MyEnum(MyEnum.MY_CASE) == MyEnum.MY_CASE
            if isinstance(data, enum):
                raise ParseError
            return enum(data)

        return foreign_parser(enum_exact_parser)

    def _provide_serializer(self, mediator: Mediator, request: SerializerRequest) -> Serializer:
        return _enum_exact_value_serializer
