from dataclasses import dataclass
from types import MappingProxyType
from typing import TypeVar, List, Generic, Optional

from .definitions import Default
from ..common import TypeHint, Parser, Serializer, Json
from ..core import (
    BaseFactory,
    Provider,
    SearchState,
    Request,
    PipelineEvalMixin
)

T = TypeVar('T')

# RM - Request Mixin


@dataclass(frozen=True)
class TypeRM(Request[T], Generic[T]):
    type: TypeHint


@dataclass(frozen=True)
class FieldNameRM(Request[T], Generic[T]):
    field_name: str


@dataclass(frozen=True)
class FieldRM(TypeRM[T], FieldNameRM[T], Generic[T]):
    default: Default
    metadata: MappingProxyType


@dataclass(frozen=True)
class ParserRequest(TypeRM[Parser], PipelineEvalMixin):
    type_check: bool
    debug_path: bool

    @classmethod
    def eval_pipeline(
        cls,
        providers: List[Provider],
        factory: BaseFactory,
        s_state: SearchState,
        request: Request
    ):
        parsers = [
            prov.apply_provider(factory, s_state, request) for prov in providers
        ]

        def pipeline_parser(value):
            result = value
            for prs in parsers:
                result = prs(result)
            return result

        return pipeline_parser


class ParserFieldRequest(ParserRequest, FieldRM[Parser]):
    pass


class SerializerRequest(TypeRM[Serializer], PipelineEvalMixin):
    @classmethod
    def eval_pipeline(
        cls,
        providers: List[Provider],
        factory: BaseFactory,
        s_state: SearchState,
        request: Request
    ):
        serializers = [
            prov.apply_provider(factory, s_state, request) for prov in providers
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


class JsonSchemaProvider(TypeRM[Json]):
    pass


class NameMappingRequest(FieldNameRM[Optional[str]], PipelineEvalMixin):
    @classmethod
    def eval_pipeline(
        cls,
        providers: List[Provider],
        factory: BaseFactory,
        s_state: SearchState,
        request: Request
    ):
        name = request.field_name # noqa
        for name_mapper in providers:
            name = name_mapper.apply_provider(factory, s_state, request)
            if name is None:
                return None
        return name


class NameMappingFieldRequest(NameMappingRequest, FieldRM[Optional[str]]):
    pass
