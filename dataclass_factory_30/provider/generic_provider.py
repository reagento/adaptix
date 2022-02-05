import collections.abc
from abc import ABC
from dataclasses import replace, dataclass
from enum import EnumMeta
from inspect import isabstract
from typing import Literal, Collection, Container, Union, Iterable, Callable, Optional

from .definitions import ParseError, UnionParseError
from .essential import Mediator, CannotProvide, Request
from .provider_basics import foreign_parser
from .provider_template import ParserProvider, SerializerProvider, for_type
from .request_cls import TypeHintRM, SerializerRequest, ParserRequest
from .static_provider import StaticProvider, static_provision_action
from ..common import Parser, Serializer, TypeHint
from ..type_tools import is_new_type, strip_tags, normalize_type


def stub(arg):
    return arg


class NewTypeUnwrappingProvider(StaticProvider):
    @static_provision_action(TypeHintRM)
    def _provide_unwrapping(self, mediator: Mediator, request: TypeHintRM) -> Parser:
        if not is_new_type(request.type):
            raise CannotProvide

        return mediator.provide(replace(request, type=request.type.__supertype__))


class TypeHintTagsUnwrappingProvider(StaticProvider):
    @static_provision_action(TypeHintRM)
    def _provide_unwrapping(self, mediator: Mediator, request: TypeHintRM) -> Parser:
        unwrapped = strip_tags(normalize_type(request.type))
        if unwrapped.source == request.type:  # type does not changed, continue search
            raise CannotProvide

        return mediator.provide(replace(request, type=unwrapped))


@dataclass
@for_type(Literal)
class LiteralProvider(ParserProvider, SerializerProvider):
    tuple_size_limit: int = 4

    def _get_container(self, args: Collection) -> Container:
        if len(args) > self.tuple_size_limit:
            return set(args)
        else:
            return tuple(args)

    def _provide_parser(self, mediator: Mediator, request: ParserRequest) -> Parser:
        norm = normalize_type(request.type)

        if request.strict_coercion and any(isinstance(arg, bool) for arg in norm.args):
            allowed_values = self._get_container(
                [(type(el), el) for el in norm.args]
            )

            # True == 1 and False == 0
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

        else:
            def union_parser(value):
                for prs in parsers:
                    try:
                        return prs(value)
                    except ParseError:
                        pass
                raise ParseError

            return union_parser


@for_type(Iterable)
class IterableProvider(ParserProvider, SerializerProvider):
    ABC_TO_IMPL = {
        collections.abc.Iterable: tuple,
        collections.abc.Reversible: tuple,
        collections.abc.Collection: tuple,
        collections.abc.Sequence: tuple,
        collections.abc.MutableSequence: list,
        collections.abc.ByteString: bytes,  # this abc is generalization of bytes and bytearray
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
        elif callable(origin):
            return origin
        else:
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
            except ParseError as e:
                e.append_path(idx_and_elem[0])
                raise e

        if strict_coercion:
            def iter_parser_dp_sc(value):
                if type(value) == dict:
                    raise ParseError

                return iter_factory(map(element_parser_dp, enumerate(value)))

            return iter_parser_dp_sc

        def iter_parser_dp(value):
            return iter_factory(map(element_parser_dp, enumerate(value)))

        return iter_parser_dp

    def _make_non_dp_parser(self, iter_factory, arg_parser, strict_coercion: bool):
        if strict_coercion:
            def iter_parser_sc(value):
                if type(value) == dict:
                    raise ParseError

                return iter_factory(map(arg_parser, value))

            return iter_parser_sc

        def iter_parser(value):
            return iter_factory(map(arg_parser, value))

        return iter_parser

    def _provide_serializer(self, mediator: Mediator, request: SerializerRequest) -> Serializer:
        norm, arg = self._fetch_norm_and_arg(request)

        iter_factory = self._get_iter_factory(norm.origin)
        arg_serializer = mediator.provide(replace(request, type=arg))

        def iter_serializer(value):
            return iter_factory(map(arg_serializer, value))

        return iter_serializer


class BaseEnumProvider(ParserProvider, SerializerProvider, ABC):
    def __init__(self, bounds: Optional[Iterable[EnumMeta]] = None):
        if bounds is None:
            bounds = None
        else:
            bounds = tuple(bounds)

        self._bounds = bounds

    def _check_request(self, request: Request) -> None:
        if not isinstance(request, TypeHintRM):
            raise CannotProvide

        norm = normalize_type(request.type)

        if not isinstance(norm.origin, EnumMeta):
            raise CannotProvide

        if self._bounds is not None and norm.origin not in self._bounds:
            raise CannotProvide


def _enum_name_serializer(data):
    return data.name


class EnumNameProvider(BaseEnumProvider):
    def _provide_parser(self, mediator: Mediator, request: ParserRequest) -> Parser:
        enum = request.type

        def enum_parser(data):
            return enum[data]

        return foreign_parser(enum_parser)

    def _provide_serializer(self, mediator: Mediator, request: SerializerRequest) -> Serializer:
        return _enum_name_serializer


class EnumValueProvider(BaseEnumProvider):
    def __init__(self, bounds: Iterable[EnumMeta], value_type: TypeHint):
        self.value_type = value_type
        super().__init__(bounds)

    def _provide_parser(self, mediator: Mediator, request: ParserRequest) -> Parser:
        enum = request.type
        value_parser = mediator.provide(replace(request, type=self.value_type))

        def enum_parser(data):
            return enum(value_parser(data))

        return foreign_parser(enum_parser)

    def _provide_serializer(self, mediator: Mediator, request: SerializerRequest) -> Serializer:
        value_serializer = mediator.provide(replace(request, type=self.value_type))

        def enum_serializer(data):
            return value_serializer(data.value)

        return enum_serializer


def _enum_exact_value_serializer(data):
    return data.value


class EnumExactValueProvider(BaseEnumProvider):
    def _provide_parser(self, mediator: Mediator, request: ParserRequest) -> Parser:
        enum = request.type

        def enum_exact_parser(data):
            return enum(data)

        return foreign_parser(enum_exact_parser)

    def _provide_serializer(self, mediator: Mediator, request: SerializerRequest) -> Serializer:
        return _enum_exact_value_serializer
