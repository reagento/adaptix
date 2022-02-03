from typing import Type, TypeVar, Optional, List, Dict

from .builtin_factory import BuiltinFactory
from .mediator import RecursionResolving, StubsRecursionResolver
from ..common import Parser, Serializer, TypeHint
from ..provider import (
    ExtraPolicy,
    CfgExtraPolicy,
    ExtraSkip,
    ParserRequest,
    SerializerRequest,
    CfgOmitDefault,
    Request,
    Mediator,
    CannotProvide,
    Provider,
    FactoryProvider
)

T = TypeVar('T')

RequestTV = TypeVar('RequestTV', bound=Request)


class FuncWrapper:
    __slots__ = ('__call__',)

    def __init__(self):
        self.__call__ = None

    def set_func(self, func):
        self.__call__ = func.__call__


class FuncRecursionResolver(StubsRecursionResolver):
    def get_stub(self, request):
        return FuncWrapper()

    def saturate_stub(self, actual, stub) -> None:
        stub.set_func(actual)


class NoSuitableProvider(Exception):
    pass


# TODO: Add JsonSchemaFactory with new API
class Factory(BuiltinFactory, Provider):
    def __init__(
        self,
        recipe: Optional[List[Provider]] = None,
        strict_coercion: bool = True,
        debug_path: bool = True,
        default_extra: ExtraPolicy = ExtraSkip(),
        omit_default: bool = False,
    ):
        self._strict_coercion = strict_coercion
        self._debug_path = debug_path
        self._default_extra = default_extra

        self._omit_default = omit_default

        self._parser_cache: Dict[TypeHint, Parser] = {}
        self._serializers_cache: Dict[TypeHint, Serializer] = {}

        super().__init__(recipe)

    def _get_config_recipe(self) -> List[Provider]:
        return [
            FactoryProvider(CfgExtraPolicy, lambda: self._default_extra),
            FactoryProvider(CfgOmitDefault, lambda: self._omit_default),
        ]

    def _get_recursion_resolving(self) -> RecursionResolving:
        return RecursionResolving(
            {
                ParserRequest: FuncRecursionResolver(),
                SerializerRequest: FuncRecursionResolver(),
            }
        )

    def apply_provider(self, mediator: Mediator, request: Request[T]) -> T:
        return self._provide_from_recipe(request)

    def _facade_provide(self, request: Request[T]) -> T:
        try:
            return self._provide_from_recipe(request)
        except CannotProvide:
            raise NoSuitableProvider

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
            return self._facade_provide(SerializerRequest(tp))

    def clear_cache(self):
        self._parser_cache = {}
        self._serializers_cache = {}
