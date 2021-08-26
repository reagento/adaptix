from dataclasses import dataclass
from typing import Type, TypeVar, Any

from ..common import Parser, Serializer
from ..core import Request, provision_action, BaseFactory, SearchState, NoSuitableProvider, CannotProvide, Provider
from ..low_level.builtin_factory import BuiltinFactory
from ..low_level.request_cls import ParserRequest, SerializerRequest

T = TypeVar('T')

RequestTV = TypeVar('RequestTV', bound=Request)


def create_factory_provide_method(request_cls: Type[RequestTV]):
    # noinspection PyUnusedLocal
    @provision_action(request_cls)
    def _provide_factory_proxy(self: BaseFactory, factory: BaseFactory, s_state: SearchState, request: ParserRequest):
        try:
            return self.provide(self.create_init_search_state(), request)
        except NoSuitableProvider:
            raise CannotProvide

    return _provide_factory_proxy


@dataclass(frozen=True)
class ParserFactory(BuiltinFactory, Provider):
    type_check: bool = False
    debug_path: bool = True

    _provide_parser = create_factory_provide_method(ParserRequest)

    def parser(self, type_: Type[T]) -> Parser[Any, T]:
        return self.provide(
            self.create_init_search_state(), ParserRequest(type_)
        )


@dataclass(frozen=True)
class SerializerFactory(BuiltinFactory, Provider):
    omit_default: bool = False

    _provide_serializer = create_factory_provide_method(SerializerRequest)

    def serializer(self, type_: Type[T]) -> Serializer[T, Any]:
        return self.provide(
            self.create_init_search_state(), SerializerRequest(type_)
        )


# TODO: Add JsonSchemaFactory with new API
class Factory(ParserFactory, SerializerFactory):
    pass
