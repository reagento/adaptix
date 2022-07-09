from dataclasses import dataclass
from typing import Type, TypeVar, Optional, List, Dict, Sequence

from .builtin_factory import BuiltinFactory
from ..common import Parser, Serializer, TypeHint
from ..provider import (
    ParserRequest,
    SerializerRequest,
    Request,
    Mediator,
    CannotProvide,
    Provider,
    FactoryProvider,
    CfgExtraPolicy,
)
from ..provider.model import ExtraPolicy, ExtraSkip

T = TypeVar('T')

RequestTV = TypeVar('RequestTV', bound=Request)


@dataclass
class NoSuitableProvider(Exception):
    important_error: Optional[CannotProvide]

    def __str__(self):
        return repr(self.important_error)


# TODO: Add JsonSchemaFactory with new API
class Factory(BuiltinFactory, Provider):
    def __init__(
        self,
        recipe: Optional[List[Provider]] = None,
        strict_coercion: bool = True,
        debug_path: bool = True,
        extra_policy: ExtraPolicy = ExtraSkip(),
    ):
        self._strict_coercion = strict_coercion
        self._debug_path = debug_path
        self._extra_policy = extra_policy

        self._parser_cache: Dict[TypeHint, Parser] = {}
        self._serializers_cache: Dict[TypeHint, Serializer] = {}

        super().__init__(recipe)

    def _get_config_recipe(self) -> List[Provider]:
        return [
            FactoryProvider(CfgExtraPolicy, lambda: self._extra_policy),
        ]

    def apply_provider(self, mediator: Mediator, request: Request[T]) -> T:
        return self._provide_from_recipe(request)

    def _facade_provide(self, request: Request[T]) -> T:
        try:
            return self._provide_from_recipe(request)
        except CannotProvide as e:
            important_error = e if e.is_important() else None
            raise NoSuitableProvider(important_error=important_error)

    def parser(self, tp: Type[T]) -> Parser[T]:
        try:
            return self._parser_cache[tp]
        except KeyError:
            return self._facade_provide(
                ParserRequest(
                    tp,
                    strict_coercion=self._strict_coercion,
                    debug_path=self._debug_path
                )
            )

    def serializer(self, tp: Type[T]) -> Serializer[T]:
        try:
            return self._serializers_cache[tp]
        except KeyError:
            return self._facade_provide(SerializerRequest(tp, debug_path=self._debug_path))

    def clear_cache(self):
        self._parser_cache = {}
        self._serializers_cache = {}
