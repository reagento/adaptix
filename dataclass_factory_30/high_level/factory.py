from dataclasses import dataclass
from typing import Type, TypeVar, Any

from ..common import Parser, Serializer
from ..core import Request, BaseFactory, SearchState, NoSuitableProvider, CannotProvide
from ..low_level.builtin_factory import BuiltinFactory
from ..low_level.request_cls import ParserRequest, SerializerRequest
from ..low_level.static_provider import StaticProvider, static_provision_action

T = TypeVar('T')

RequestTV = TypeVar('RequestTV', bound=Request)


def create_factory_provide_method(request_cls: Type[RequestTV]):
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
    type_check: bool = False
    debug_path: bool = True

    _provide_parser = create_factory_provide_method(ParserRequest)

    def parser(self, tp: Type[T]) -> Parser[Any, T]:
        return self.provide(
            ParserRequest(
                tp,
                type_check=self.type_check,
                debug_path=self.debug_path
            )
        )


@dataclass(frozen=True)
class SerializerFactory(BuiltinFactory, StaticProvider):
    omit_default: bool = False

    _provide_serializer = create_factory_provide_method(SerializerRequest)

    def serializer(self, tp: Type[T]) -> Serializer[T, Any]:
        return self.provide(SerializerRequest(tp))


# TODO: Add JsonSchemaFactory with new API
class Factory(ParserFactory, SerializerFactory):
    pass
