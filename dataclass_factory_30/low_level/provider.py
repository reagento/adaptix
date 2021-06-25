from abc import ABC, abstractmethod
from typing import Optional, Type, TypeVar, List, final

from ..common import Json, Parser, Serializer
from ..core import Provider, BaseFactory, ProvisionCtx, provision_action
from .pipeline import PipelineEvalMixin, PipeliningMixin

T = TypeVar('T')


class ParserProvider(Provider[Parser], PipelineEvalMixin, PipeliningMixin, ABC):
    @provision_action
    @abstractmethod
    def _provide_parser(self, factory: 'BaseFactory', offset: int, ctx: ProvisionCtx) -> Parser:
        raise NotImplementedError

    @classmethod
    @final
    def eval_pipeline(
        cls: Type[Provider[Parser]],
        providers: List[Provider],
        factory: 'BaseFactory',
        offset: int,
        ctx: ProvisionCtx
    ) -> Parser:
        parsers = [
            prov.provide(cls, factory, offset, ctx) for prov in providers
        ]

        def pipeline_parser(value):
            result = value
            for prs in parsers:
                result = prs(result)
            return result

        return pipeline_parser


class SerializerProvider(Provider, PipelineEvalMixin, PipeliningMixin, ABC):
    @provision_action
    @abstractmethod
    def _provide_serializer(self, factory: 'BaseFactory', offset: int, ctx: ProvisionCtx) -> Serializer:
        raise NotImplementedError

    @classmethod
    @final
    def eval_pipeline(
        cls: Type[Provider[Serializer]],
        providers: List[Provider],
        factory: 'BaseFactory',
        offset: int,
        ctx: ProvisionCtx
    ) -> Serializer:
        serializers = [
            prov.provide(cls, factory, offset, ctx) for prov in providers
        ]

        def pipeline_serializer(value):
            result = value
            for srz in serializers:
                result = srz(result)
            return result

        return pipeline_serializer


class JsonSchemaProvider(Provider[Json], ABC):
    @provision_action
    @abstractmethod
    def _provide_json_schema(self, factory: 'BaseFactory', offset: int, ctx: ProvisionCtx) -> Json:
        raise NotImplementedError


class NameMappingProvider(Provider[Optional[str]], ABC):
    @provision_action
    @abstractmethod
    def _provide_name_mapping(self, factory: 'BaseFactory', offset: int, ctx: ProvisionCtx) -> Optional[str]:
        raise NotImplementedError
