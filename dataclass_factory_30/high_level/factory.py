from dataclasses import dataclass
from typing import Type, TypeVar, Any, Optional

from ..common import Parser, Serializer
from ..core import Request, BaseFactory, SearchState, NoSuitableProvider, CannotProvide
from ..low_level.builtin_factory import BuiltinFactory
from ..low_level.request_cls import ParserRequest, SerializerRequest
from ..low_level.static_provider import StaticProvider, static_provision_action

T = TypeVar('T')

RequestTV = TypeVar('RequestTV', bound=Request)


def create_factory_provision_action(request_cls: Type[RequestTV]):
    # noinspection PyUnusedLocal
    @static_provision_action(request_cls)
    def _provide_factory_proxy(
        self: BaseFactory,
        factory: BaseFactory,
        s_state: SearchState,
        request: ParserRequest
    ):
        try:
            return self.provide(request)
        except NoSuitableProvider:
            raise CannotProvide

    return _provide_factory_proxy


@dataclass(frozen=True)
class ParserFactory(BuiltinFactory, StaticProvider):
    strict_coercion: bool = True
    debug_path: bool = True

    _provide_parser = create_factory_provision_action(ParserRequest)

    def parser(
        self,
        tp: Type[T],
        *,
        strict_coercion: Optional[bool] = None,
        debug_path: Optional[bool] = None
    ) -> Parser[Any, T]:

        if strict_coercion is None:
            strict_coercion = self.strict_coercion
        if debug_path is None:
            debug_path = self.debug_path

        return self.provide(
            ParserRequest(
                tp,
                strict_coercion=strict_coercion,
                debug_path=debug_path
            )
        )


@dataclass(frozen=True)
class SerializerFactory(BuiltinFactory, StaticProvider):
    omit_default: bool = False

    _provide_serializer = create_factory_provision_action(SerializerRequest)

    def serializer(self, tp: Type[T]) -> Serializer[T, Any]:
        return self.provide(SerializerRequest(tp))


# TODO: Add JsonSchemaFactory with new API
class Factory(ParserFactory, SerializerFactory):
    pass
