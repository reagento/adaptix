from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TypeVar, Mapping, Collection

from .. import Request
from ..request_cls import TypeHintRM, ParserRequest, SerializerRequest
from ...code_tools import CodeBuilder, PrefixManglerBase, MangledConstant, mangling_method, ContextNamespace
from ...common import Parser, Serializer
from ...model_tools import InputFigure, OutputFigure, BaseField

T = TypeVar('T')


@dataclass(frozen=True)
class InputFigureRequest(TypeHintRM[InputFigure]):
    pass


@dataclass(frozen=True)
class OutputFigureRequest(TypeHintRM[OutputFigure]):
    pass


##################

class VarBinder(PrefixManglerBase):
    data = MangledConstant("data")
    extra = MangledConstant("extra")
    opt_fields = MangledConstant("opt_fields")

    @mangling_method("field_")
    def field(self, field: BaseField) -> str:
        return field.name


@dataclass(frozen=True)
class WithSkippedFields:
    skipped_fields: Collection[str]


class InputExtractionGen(ABC):
    @abstractmethod
    def generate_input_extraction(
        self,
        binder: VarBinder,
        ctx_namespace: ContextNamespace,
        field_parsers: Mapping[str, Parser],
    ) -> CodeBuilder:
        pass


class InputCreationGen(ABC):
    @abstractmethod
    def generate_input_creation(
        self,
        binder: VarBinder,
        ctx_namespace: ContextNamespace,
    ) -> CodeBuilder:
        pass


@dataclass(frozen=True)
class InputExtractionImage(WithSkippedFields):
    extraction_gen: InputExtractionGen


@dataclass(frozen=True)
class InputExtractionImageRequest(Request[InputExtractionImage]):
    figure: InputFigure
    initial_request: ParserRequest


@dataclass(frozen=True)
class InputCreationImage:
    creation_gen: InputCreationGen


@dataclass(frozen=True)
class InputCreationImageRequest(Request[InputCreationImage]):
    figure: InputFigure
    initial_request: ParserRequest


class OutputExtractionGen(ABC):
    @abstractmethod
    def generate_output_extraction(
        self,
        binder: VarBinder,
        ctx_namespace: ContextNamespace,
        field_serializers: Mapping[str, Serializer],
    ) -> CodeBuilder:
        pass


class OutputCreationGen(ABC):
    @abstractmethod
    def generate_output_creation(
        self,
        binder: VarBinder,
        ctx_namespace: ContextNamespace,
    ) -> CodeBuilder:
        pass


@dataclass(frozen=True)
class OutputExtractionImage:
    extraction_gen: OutputExtractionGen


@dataclass(frozen=True)
class OutputExtractionImageRequest(Request[OutputExtractionImage]):
    figure: OutputFigure
    initial_request: SerializerRequest


@dataclass(frozen=True)
class OutputCreationImage(WithSkippedFields):
    creation_gen: OutputCreationGen


@dataclass(frozen=True)
class OutputCreationImageRequest(Request[OutputCreationImage]):
    figure: OutputFigure
    initial_request: SerializerRequest
