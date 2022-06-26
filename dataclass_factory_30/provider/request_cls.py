from dataclasses import dataclass, field
from enum import Enum
from typing import TypeVar, List, Generic, Mapping, Any

from .definitions import Default, Accessor
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
class FieldRM(TypeHintRM[T], Generic[T]):
    name: str
    default: Default
    # Mapping almost never defines __hash__,
    # so it will be more convenient to exclude this field
    # from hash computation
    metadata: Mapping[Any, Any] = field(hash=False)

    def __post_init__(self):
        if not self.name.isidentifier():
            raise ValueError("Name of field must be python identifier")


class ParamKind(Enum):
    POS_ONLY = 0
    POS_OR_KW = 1
    KW_ONLY = 3  # 2 is for VAR_POS


@dataclass(frozen=True)
class InputFieldRM(FieldRM[T], Generic[T]):
    is_required: bool
    param_kind: ParamKind

    @property
    def is_optional(self):
        return not self.is_required


@dataclass(frozen=True)
class OutputFieldRM(FieldRM[T], Generic[T]):
    accessor: Accessor

    @property
    def is_optional(self) -> bool:
        return not self.is_optional

    @property
    def is_required(self) -> bool:
        return self.accessor.access_error is None


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
    debug_path: bool

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
class SerializerFieldRequest(SerializerRequest, OutputFieldRM[Serializer]):
    pass
