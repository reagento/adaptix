from dataclasses import dataclass
from types import MappingProxyType
from typing import TypeVar, List, Generic, Optional

from .definitions import Default
from ..common import TypeHint, Parser, Serializer, Json
from ..core import (
    Mediator,
    Provider,
    Request,
    PipelineEvalMixin
)

T = TypeVar('T')


# RM - Request Mixin


@dataclass(frozen=True)
class TypeHintRM(Request[T], Generic[T]):
    type: TypeHint


@dataclass(frozen=True)
class TypeRM(TypeHintRM[T], Generic[T]):
    type: type


@dataclass(frozen=True)
class FieldNameRM(Request[T], Generic[T]):
    field_name: str


@dataclass(frozen=True)
class FieldRM(TypeHintRM[T], FieldNameRM[T], Generic[T]):
    default: Default
    metadata: MappingProxyType


@dataclass(frozen=True)
class ParserRequest(TypeHintRM[Parser], PipelineEvalMixin):
    strict_coercion: bool
    debug_path: bool

    @classmethod
    def eval_pipeline(
        cls,
        providers: List[Provider],
        mediator: Mediator,
        request: Request
    ):
        parsers = [
            prov.apply_provider(mediator, request) for prov in providers
        ]

        def pipeline_parser(value):
            result = value
            for prs in parsers:
                result = prs(result)
            return result

        return pipeline_parser


class ParserFieldRequest(ParserRequest, FieldRM[Parser]):
    pass


class SerializerRequest(TypeHintRM[Serializer], PipelineEvalMixin):
    @classmethod
    def eval_pipeline(
        cls,
        providers: List[Provider],
        mediator: Mediator,
        request: Request
    ):
        serializers = [
            prov.apply_provider(mediator, request) for prov in providers
        ]

        def pipeline_serializer(value):
            result = value
            for srz in serializers:
                result = srz(result)
            return result

        return pipeline_serializer


@dataclass(frozen=True)
class SerializerFieldRequest(SerializerRequest, FieldRM[Parser]):
    omit_default: bool


class JsonSchemaProvider(TypeHintRM[Json]):
    pass


class NameMappingRequest(FieldNameRM[Optional[str]], PipelineEvalMixin):
    @classmethod
    def eval_pipeline(
        cls,
        providers: List[Provider],
        mediator: Mediator,
        request: Request
    ):
        name = request.field_name  # noqa
        for name_mapper in providers:
            name = name_mapper.apply_provider(mediator, request)
            if name is None:
                return None
        return name


class NameMappingFieldRequest(NameMappingRequest, FieldRM[Optional[str]]):
    pass
