from dataclasses import dataclass
from typing import TypeVar, Type, Union, List, Callable

from .fields import FieldsProvisionCtx
from .provider_tmpl import ParserProvider
from ..common import Parser
from ..core import Provider, BaseFactory, ProvisionCtx, CannotProvide, NoSuitableProvider

T = TypeVar('T')


class ProvCtxChecker:
    ALLOWS = Union[type, str]

    # TODO: Add support for type hint as pred
    def __init__(self, pred: ALLOWS):
        if not isinstance(pred, (str, type)):
            raise TypeError(f'Expected {self.ALLOWS}')

        self.pred = pred

    def __call__(self, ctx: ProvisionCtx) -> bool:
        if isinstance(self.pred, str):
            if isinstance(ctx, FieldsProvisionCtx):
                return self.pred == ctx.field_name
            raise CannotProvide

        return issubclass(ctx.type, self.pred)


@dataclass
class AsProvider(Provider[T]):
    provider_tmpl: Type[Provider[T]]
    ctx_checker: ProvCtxChecker
    provision: T

    def _provide_other(
        self,
        provider_tmpl: 'Type[Provider[T]]',
        factory: 'BaseFactory',
        offset: int,
        ctx: ProvisionCtx
    ) -> T:
        if self.provider_tmpl == provider_tmpl:
            raise CannotProvide

        if self.ctx_checker(ctx):
            return self.provision

        raise CannotProvide


class NextProvider(Provider):
    def _provide_other(
        self,
        provider_tmpl: 'Type[Provider[T]]',
        factory: 'BaseFactory',
        offset: int,
        ctx: ProvisionCtx
    ) -> T:
        return factory.provide(provider_tmpl, offset + 1, ctx)


@dataclass
class FromFactoryProvider(Provider[T]):
    provider_tmpl_list: List[Type[Provider[T]]]
    ctx_checker: ProvCtxChecker
    factory: BaseFactory

    def _provide_other(
        self,
        provider_tmpl: 'Type[Provider[T]]',
        factory: 'BaseFactory',
        offset: int,
        ctx: ProvisionCtx
    ) -> T:
        if provider_tmpl not in self.provider_tmpl_list:
            raise CannotProvide

        if not self.ctx_checker(ctx):
            raise CannotProvide

        try:
            return self.factory.provide(provider_tmpl, offset, ctx)
        except NoSuitableProvider:
            raise CannotProvide


@dataclass
class ConstructorParserProvider(ParserProvider):
    ctx_checker: ProvCtxChecker
    constructor: Callable

    def _provide_parser(self, factory: 'BaseFactory', offset: int, ctx: ProvisionCtx) -> Parser:
        if not self.ctx_checker(ctx):
            raise CannotProvide

        # TODO: finish up
        raise RuntimeError
