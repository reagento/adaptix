from dataclasses import dataclass, field
from typing import Type, TypeVar, Any, List, Tuple

from ..common import Parser, Serializer
from ..core import BaseFactory, Provider, ProvisionCtx, PipeliningMixin
from ..low_level import ProvCtxChecker, FromFactoryProvider, ParserProvider, SerializerProvider

T = TypeVar('T')


def _provider_from_factory(
    allows: List[Tuple[Type[Provider], Type[BaseFactory]]],
    pred,
    value
):
    prov_tmpl_list = []
    for provider_template, factory_type in allows:
        if isinstance(value, factory_type):
            prov_tmpl_list.append(provider_template)

    if prov_tmpl_list:
        return FromFactoryProvider(
            prov_tmpl_list, ProvCtxChecker(pred), value
        )
    return None


@dataclass(frozen=True)
class BuiltinFactory(BaseFactory, PipeliningMixin):
    recipe: list = field(default_factory=list)

    def ensure_provider(self, value) -> Provider:
        if isinstance(value, Provider):
            return value

        if isinstance(value, tuple) and len(value) == 2:
            pred, factory = value

            result = _provider_from_factory(
                [
                    (ParserProvider, ParserFactory),
                    (SerializerProvider, SerializerFactory),
                ],
                pred,
                factory,
            )
            if result is not None:
                return result

        if isinstance(value, type):
            raise ValueError(
                f'Can not create provider from {value}.'
                'You should pass instance instead of class'
            )

        raise ValueError(f'Can not create provider from {value}')


@dataclass(frozen=True)
class ParserFactory(BuiltinFactory):
    type_check: bool = False
    debug_path: bool = True

    def parser(self, type_: Type[T]) -> Parser[Any, T]:
        ctx = ProvisionCtx(type_)
        return self.provide(
            ParserProvider, 0, ctx
        )


@dataclass(frozen=True)
class SerializerFactory(BuiltinFactory):
    omit_default: bool = False

    def serializer(self, type_: Type[T]) -> Serializer[T, Any]:
        ctx = ProvisionCtx(type_)
        return self.provide(
            SerializerProvider, 0, ctx
        )


# TODO: Add JsonSchemaFactory with new API
class Factory(ParserFactory, SerializerFactory):
    pass
