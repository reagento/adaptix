from dataclasses import dataclass
from typing import Generic, Iterable, TypeVar

from ..common import Parser, Serializer, TypeHint
from ..model_tools import BaseField, InputField, OutputField
from .essential import Mediator, PipelineEvalMixin, Provider, Request

T = TypeVar('T')


# RM - Request Mixin


@dataclass(frozen=True)
class TypeHintRM(Request[T], Generic[T]):
    type: TypeHint


@dataclass(frozen=True)
class FieldRM(TypeHintRM[T], BaseField, Generic[T]):
    pass


@dataclass(frozen=True)
class InputFieldRM(FieldRM[T], InputField, Generic[T]):
    pass


@dataclass(frozen=True)
class OutputFieldRM(FieldRM[T], OutputField, Generic[T]):
    pass


@dataclass(frozen=True)
class ParserRequest(TypeHintRM[Parser], PipelineEvalMixin[Parser]):
    strict_coercion: bool
    debug_path: bool

    @classmethod
    def eval_pipeline(
        cls,
        providers: Iterable[Provider],
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


@dataclass(frozen=True)
class ParserFieldRequest(ParserRequest, InputFieldRM[Parser]):
    pass


@dataclass(frozen=True)
class SerializerRequest(TypeHintRM[Serializer], PipelineEvalMixin[Serializer]):
    debug_path: bool

    @classmethod
    def eval_pipeline(
        cls,
        providers: Iterable[Provider],
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
class SerializerFieldRequest(SerializerRequest, OutputFieldRM[Serializer]):
    pass
