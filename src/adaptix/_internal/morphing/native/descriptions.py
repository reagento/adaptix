from dataclasses import dataclass
from datetime import datetime
from enum import Enum


@dataclass(frozen=True)
class DecimalProgram:
    function: object
    loading: bool


@dataclass(frozen=True)
class ScalarProgram:
    function: object
    types: tuple[type, ...]
    nullable: bool = False
    coerce_int: bool = False


@dataclass(frozen=True)
class Base64Program:
    function: object
    loading: bool


@dataclass(frozen=True)
class DateTimeProgram:
    function: object
    loading: bool
    cls: type = datetime


@dataclass(frozen=True)
class EnumProgram:
    function: object
    mapping: tuple
    enum: type[Enum]
    loading: bool


@dataclass(frozen=True)
class OptionalProgram:
    function: object
    converter: object
    tp: object = None


@dataclass(frozen=True)
class LiteralProgram:
    function: object
    cases: tuple


@dataclass(frozen=True)
class UnionDumperProgram:
    function: object
    variants: tuple


@dataclass(frozen=True)
class UUIDProgram:
    function: object
    loading: bool
