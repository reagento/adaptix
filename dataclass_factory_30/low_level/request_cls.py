from dataclasses import dataclass
from types import MappingProxyType
from typing import TypeVar, List, Generic, Any, Callable, Union

from ..common import TypeHint, Parser, Serializer, Json
from ..core import (
    BaseFactory,
    Provider,
    SearchState,
    Request,
    PipelineEvalMixin
)

T = TypeVar('T')


@dataclass(frozen=True)
class TypeRequest(Request, Generic[T]):
    type: TypeHint


class ParserRequest(TypeRequest[Parser], PipelineEvalMixin):
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


class SerializerRequest(TypeRequest[Serializer], PipelineEvalMixin):
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


class JsonSchemaProvider(TypeRequest[Json]):
    pass


@dataclass(frozen=True)
class NoDefault:
    field_is_required: bool


@dataclass(frozen=True)
class DefaultValue:
    value: Any


@dataclass(frozen=True)
class DefaultFactory:
    factory: Callable[[], Any]


Default = Union[NoDefault, DefaultValue, DefaultFactory]


@dataclass(frozen=True)
class TypeFieldRequest(TypeRequest):
    field_name: str
    default: Default
    metadata: MappingProxyType


class ParserTypeFieldRequest(ParserRequest, TypeFieldRequest):
    pass


class SerializerTypeFieldRequest(SerializerRequest, TypeFieldRequest):
    pass


class NameMappingRequest(TypeFieldRequest):
    pass
