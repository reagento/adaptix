from dataclasses import replace, dataclass
from typing import Literal, Collection, Container, Union

from .definitions import ParseError, UnionParseError
from . import Mediator, CannotProvide
from .static_provider import StaticProvider, static_provision_action
from .basic_provider import ParserProvider, SerializerProvider, for_origin
from .request_cls import TypeHintRM, SerializerRequest, ParserRequest
from ..common import Parser
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
@for_origin(Literal)
class LiteralProvider(ParserProvider, SerializerProvider):
    tuple_size_limit: int = 4

    def _get_container(self, args: Collection) -> Container:
        if len(args) > self.tuple_size_limit:
            return set(args)
        else:
            return tuple(args)

    def _provide_parser(self, mediator: Mediator, request: ParserRequest):
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

    def _provide_serializer(self, mediator: Mediator, request: SerializerRequest):
        return stub


@for_origin(Union)
class UnionProvider(ParserProvider):
    def _provide_parser(self, mediator: Mediator, request: ParserRequest):
        norm = normalize_type(request.type)

        parsers = [
            mediator.provide(replace(request, type=tp)) for tp in norm.args
        ]

        if request.debug_path:
            def union_parser_dp(value):
                errors = []
                for prs in parsers:
                    try:
                        return prs(value)
                    except ParseError as e:
                        errors.append(e)

                return UnionParseError(sub_errors=errors)

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
