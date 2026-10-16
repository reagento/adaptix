from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any
from weakref import ReferenceType

FunctionReference = Callable[..., Any] | ReferenceType[Callable[..., Any]]


def resolve_function(function: FunctionReference) -> Callable[..., Any]:
    if isinstance(function, ReferenceType):
        resolved = function()
        if resolved is None:
            raise RuntimeError("The native converter is no longer alive")
        return resolved
    return function


@dataclass(frozen=True)
class DecimalProgram:
    function: FunctionReference
    loading: bool


@dataclass(frozen=True)
class ScalarProgram:
    function: FunctionReference
    types: tuple[type, ...]
    nullable: bool = False
    coerce_int: bool = False


@dataclass(frozen=True)
class Base64Program:
    function: FunctionReference
    loading: bool


@dataclass(frozen=True)
class DateTimeProgram:
    function: FunctionReference
    loading: bool
    cls: type = datetime


@dataclass(frozen=True)
class EnumProgram:
    function: FunctionReference
    mapping: tuple
    enum: type[Enum]
    loading: bool


@dataclass(frozen=True)
class OptionalProgram:
    function: FunctionReference
    converter: object
    tp: object = None


@dataclass(frozen=True)
class LiteralProgram:
    function: FunctionReference
    cases: tuple


@dataclass(frozen=True)
class UnionDumperProgram:
    function: FunctionReference
    variants: tuple


@dataclass(frozen=True)
class UUIDProgram:
    function: FunctionReference
    loading: bool
