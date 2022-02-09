from dataclasses import dataclass, field
from enum import Enum
from typing import TypeVar, List, Generic, Mapping, Any

from .definitions import Default
from .essential import (
    Mediator,
    Provider,
    Request,
    PipelineEvalMixin
)
from ..common import TypeHint, Parser, Serializer

T = TypeVar('T')


# RM - Request Mixin


@dataclass(frozen=True)
class TypeHintRM(Request[T], Generic[T]):
    type: TypeHint


@dataclass(frozen=True)
class FieldNameRM(Request[T], Generic[T]):
    field_name: str


@dataclass(frozen=True)
class FieldRM(TypeHintRM[T], FieldNameRM[T], Generic[T]):
    default: Default
    is_required: bool
    # Mapping almost never defines __hash__,
    # so it will be more convenient to exclude this field
    # from hash computation
    metadata: Mapping[Any, Any] = field(hash=False)


class ParamKind(Enum):
    POS_ONLY = 0
    POS_OR_KW = 1
    KW_ONLY = 3  # 2 is for VAR_POS


@dataclass(frozen=True)
class InputFieldRM(FieldRM[T], Generic[T]):
    param_kind: ParamKind


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


@dataclass(frozen=True)
class ParserFieldRequest(ParserRequest, InputFieldRM[Parser]):
    pass


@dataclass(frozen=True)
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


@dataclass(frozen=True)
class CfgOmitDefault(Request[bool]):
    pass
