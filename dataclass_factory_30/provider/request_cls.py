from dataclasses import dataclass, replace
from typing import Generic, TypeVar

from ..common import Parser, Serializer, TypeHint
from ..model_tools import BaseField, InputField, OutputField
from .essential import Request

T = TypeVar('T')


# RM - Request Mixin


@dataclass(frozen=True)
class TypeHintRM(Request[T], Generic[T]):
    type: TypeHint


@dataclass(frozen=True)
class FieldRM(TypeHintRM[T], Generic[T]):
    field: BaseField

    def __post_init__(self):
        # This behavior allows using replace() in code that knows nothing about fields
        if self.type != self.field.type:
            super().__setattr__('field', replace(self.field, type=self.type))


@dataclass(frozen=True)
class InputFieldRM(FieldRM[T], Generic[T]):
    field: InputField


@dataclass(frozen=True)
class OutputFieldRM(FieldRM[T], Generic[T]):
    field: OutputField


@dataclass(frozen=True)
class ParserRequest(TypeHintRM[Parser]):
    strict_coercion: bool
    debug_path: bool


@dataclass(frozen=True)
class ParserFieldRequest(ParserRequest, InputFieldRM[Parser]):
    pass


@dataclass(frozen=True)
class SerializerRequest(TypeHintRM[Serializer]):
    debug_path: bool


@dataclass(frozen=True)
class SerializerFieldRequest(SerializerRequest, OutputFieldRM[Serializer]):
    pass
