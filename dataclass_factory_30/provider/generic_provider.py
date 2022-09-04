import collections.abc
from abc import ABC
from dataclasses import dataclass, replace
from enum import EnumMeta, Flag
from inspect import isabstract
from typing import Callable, Collection, Container, Dict, Iterable, Literal, Mapping, Tuple, Union

from ..common import Parser, Serializer, TypeHint
from ..struct_path import append_path
from ..type_tools import BaseNormType, is_new_type, is_subclass_soft, normalize_type, strip_tags
from .definitions import ExcludedTypeParseError, ParseError, TypeParseError, UnionParseError
from .essential import CannotProvide, Mediator, Request
from .provider_basics import foreign_parser
from .provider_template import ParserProvider, SerializerProvider, for_origin
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
@for_origin(Literal)
class LiteralProvider(ParserProvider, SerializerProvider):
    tuple_size_limit: int = 4

    def _get_container(self, args: Collection) -> Container:
        if len(args) > self.tuple_size_limit:
            return set(args)
        return tuple(args)

    def _provide_parser(self, mediator: Mediator, request: ParserRequest) -> Parser:
        norm = normalize_type(request.type)

        # TODO: add support for enum
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


@for_origin(Union)
class UnionProvider(ParserProvider, SerializerProvider):
    def _provide_parser(self, mediator: Mediator, request: ParserRequest) -> Parser:
        norm = normalize_type(request.type)

        parsers = tuple(
            mediator.provide(replace(request, type=tp.source))
            for tp in norm.args
        )

        if request.debug_path:
            return self._get_parser_dp(parsers)

        return self._get_parser_non_dp(parsers)

    def _get_parser_dp(self, parsers: Iterable[Parser]) -> Parser:
        def union_parser_dp(data):
            errors = []
            for prs in parsers:
                try:
                    return prs(data)
                except ParseError as e:
                    errors.append(e)

            raise UnionParseError(errors)

        return union_parser_dp

    def _get_parser_non_dp(self, parsers: Iterable[Parser]) -> Parser:
        def union_parser(data):
            for prs in parsers:
                try:
                    return prs(data)
                except ParseError:
                    pass
            raise ParseError

        return union_parser

    def _is_single_optional(self, norm: BaseNormType) -> bool:
        return len(norm.args) == 2 and None in [case.origin for case in norm.args]

    def _is_class_origin(self, origin) -> bool:
        return (origin is None or isinstance(origin, type)) and not is_subclass_soft(origin, collections.abc.Callable)

    def _provide_serializer(self, mediator: Mediator, request: SerializerRequest) -> Serializer:
        norm = normalize_type(request.type)

        # TODO: allow use Literal[..., None] with non single optional

        if self._is_single_optional(norm):
            non_optional = next(case for case in norm.args if case.origin is not None)
            non_optional_serializer = mediator.provide(replace(request, type=non_optional.source))
            return self._get_single_optional_serializer(non_optional_serializer)

        non_class_origins = [case.source for case in norm.args if not self._is_class_origin(case.origin)]
        if non_class_origins:
            raise ValueError(
                f"Can not create serializer for {request.type}."
                f" All cases of union must be class, but found {non_class_origins}"
            )

        serializers = tuple(
            mediator.provide(replace(request, type=tp.source))
            for tp in norm.args
        )

        serializer_type_map = {case.origin: serializer for case, serializer in zip(norm.args, serializers)}

        return self._get_serializer(serializer_type_map)

    def _get_serializer(self, serializer_type_map: Mapping[type, Serializer]) -> Serializer:
        def union_serializer(data):
            return serializer_type_map[type(data)](data)

        return union_serializer

    def _get_single_optional_serializer(self, serializer: Serializer) -> Serializer:
        # This behavior is slightly different from the generic serializer.
        # If data contains value of invalid type and main serializer does not raise an error,
        # generic serializer will raise exception, but this serializer skips problem
        def union_so_serializer(data):
            if data is None:
                return None
            return serializer(data)

        return union_so_serializer


CollectionsMapping = collections.abc.Mapping


@for_origin(Iterable)
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
        return self._make_parser(request, iter_factory, arg_parser)

    def _create_debug_path_iter_mapper(self, converter):
        def iter_mapper(iterable):
            idx = 0

            for el in iterable:
                try:
                    yield converter(el)
                except Exception as e:
                    append_path(e, idx)
                    raise e

                idx += 1

        return iter_mapper

    def _make_parser(self, request: ParserRequest, iter_factory, arg_parser):
        if request.debug_path:
            iter_mapper = self._create_debug_path_iter_mapper(arg_parser)

            if request.strict_coercion:
                return self._get_dp_sc_parser(iter_factory, iter_mapper)

            return self._get_dp_non_sc_parser(iter_factory, iter_mapper)

        if request.strict_coercion:
            return self._get_non_dp_sc_parser(iter_factory, arg_parser)

        return self._get_non_dp_non_sc_parser(iter_factory, arg_parser)

    def _get_dp_non_sc_parser(self, iter_factory, iter_mapper):
        def iter_parser_dp(value):
            try:
                value_iter = iter(value)
            except TypeError:
                raise TypeParseError(Iterable)

            return iter_factory(iter_mapper(value_iter))

        return iter_parser_dp

    def _get_dp_sc_parser(self, iter_factory, iter_mapper):
        def iter_parser_dp_sc(value):
            if isinstance(value, CollectionsMapping):
                raise ExcludedTypeParseError(Mapping)

            try:
                value_iter = iter(value)
            except TypeError:
                raise TypeParseError(Iterable)

            return iter_factory(iter_mapper(value_iter))

        return iter_parser_dp_sc

    def _get_non_dp_sc_parser(self, iter_factory, arg_parser):
        def iter_parser_sc(value):
            if isinstance(value, CollectionsMapping):
                raise ExcludedTypeParseError(Mapping)

            try:
                map_iter = map(arg_parser, value)
            except TypeError:
                raise TypeParseError(Iterable)

            return iter_factory(map_iter)

        return iter_parser_sc

    def _get_non_dp_non_sc_parser(self, iter_factory, arg_parser):
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
        return self._make_serializer(request, iter_factory, arg_serializer)

    def _make_serializer(self, request: SerializerRequest, iter_factory, arg_serializer):
        if request.debug_path:
            iter_mapper = self._create_debug_path_iter_mapper(arg_serializer)
            return self._get_dp_serializer(iter_factory, iter_mapper)

        return self._get_non_dp_serializer(iter_factory, arg_serializer)

    def _get_dp_serializer(self, iter_factory, iter_mapper):
        def iter_dp_serializer(data):
            return iter_factory(iter_mapper(data))

        return iter_dp_serializer

    def _get_non_dp_serializer(self, iter_factory, arg_serializer: Serializer):
        def iter_serializer(data):
            return iter_factory(map(arg_serializer, data))

        return iter_serializer


@for_origin(Dict)
class DictProvider(ParserProvider, SerializerProvider):
    def _extract_key_value(self, request: TypeHintRM) -> Tuple[BaseNormType, BaseNormType]:
        norm = normalize_type(request.type)
        return norm.args  # type: ignore

    def _provide_parser(self, mediator: Mediator, request: ParserRequest) -> Parser:
        key, value = self._extract_key_value(request)

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

        return self._make_parser(request, key_parser=key_parser, value_parser=value_parser)

    def _make_parser(self, request: ParserRequest, key_parser: Parser, value_parser: Parser):
        if request.debug_path:
            return self._get_parser_dp(
                key_parser=key_parser,
                value_parser=value_parser,
            )

        return self._get_parser_non_dp(
            key_parser=key_parser,
            value_parser=value_parser,
        )

    def _get_parser_dp(self, key_parser: Parser, value_parser: Parser):
        def dict_parser_dp(data):
            try:
                items_method = data.items
            except AttributeError:
                raise TypeParseError(CollectionsMapping)

            result = {}
            for k, v in items_method():
                try:
                    parsed_key = key_parser(k)
                    parsed_value = value_parser(v)
                except Exception as e:
                    append_path(e, k)
                    raise e

                result[parsed_key] = parsed_value

            return result

        return dict_parser_dp

    def _get_parser_non_dp(self, key_parser: Parser, value_parser: Parser):
        def dict_parser(data):
            try:
                items_method = data.items
            except AttributeError:
                raise TypeParseError(CollectionsMapping)

            result = {}
            for k, v in items_method():
                result[key_parser(k)] = value_parser(v)

            return result

        return dict_parser

    def _provide_serializer(self, mediator: Mediator, request: SerializerRequest) -> Serializer:
        key, value = self._extract_key_value(request)

        key_serializer = mediator.provide(
            replace(request, type=key.source),
        )

        value_serializer = mediator.provide(
            replace(request, type=value.source),
        )

        return self._make_serializer(request, key_serializer=key_serializer, value_serializer=value_serializer)

    def _make_serializer(self, request: SerializerRequest, key_serializer: Serializer, value_serializer: Serializer):
        if request.debug_path:
            return self._get_serializer_dp(
                key_serializer=key_serializer,
                value_serializer=value_serializer,
            )

        return self._get_serializer_non_dp(
            key_serializer=key_serializer,
            value_serializer=value_serializer,
        )

    def _get_serializer_dp(self, key_serializer, value_serializer):
        def dict_serializer_dp(data: Mapping):
            result = {}
            for k, v in data.items():
                try:
                    result[key_serializer(k)] = value_serializer(v)
                except Exception as e:
                    append_path(e, k)
                    raise e

            return result

        return dict_serializer_dp

    def _get_serializer_non_dp(self, key_serializer, value_serializer):
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

        if issubclass(enum, Flag):
            raise ValueError(f"Can not use {type(self).__name__} with Flag subclass {enum}")

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
