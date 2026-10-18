from dataclasses import replace
from datetime import date, datetime, time
from decimal import Decimal
from types import BuiltinFunctionType, FunctionType
from typing import Any
from uuid import UUID
from weakref import ReferenceType, WeakKeyDictionary, ref

from adaptix._internal.morphing.concrete_provider import (
    bool_strict_coercion_loader,
    decimal_strict_coercion_loader,
    float_strict_coercion_loader,
    int_strict_coercion_loader,
    none_loader,
    str_strict_coercion_loader,
)
from adaptix._internal.morphing.native.descriptions import (
    DateTimeProgram,
    DecimalProgram,
    EnumProgram,
    ScalarProgram,
    UUIDProgram,
)
from adaptix._internal.special_cases_optimization import as_is_stub

IDENTITY_LOADERS = (
    (int_strict_coercion_loader, int),
    (str_strict_coercion_loader, str),
    (bool_strict_coercion_loader, bool),
    (float_strict_coercion_loader, float),
)
PROGRAMS: WeakKeyDictionary[FunctionType, ReferenceType[Any]] = WeakKeyDictionary()


def register_program(function, program):
    # Programs can refer back to the function through recursive converters.
    # Keep their lifetime with the function; the registry owns neither end.
    program = replace(program, function=ref(function))
    function.adaptix_native_program = program
    PROGRAMS[function] = ref(program)
    return function


def identity_spec(function):
    if function is as_is_stub:
        return (), False
    if function is none_loader:
        return (), True
    for loader, cls in IDENTITY_LOADERS:
        if function is loader:
            return (cls,), False
    program = get_program(function)
    if isinstance(program, ScalarProgram) and not program.coerce_int:
        return program.types, program.nullable
    return None


def describe_scalar_union(function, loaders):
    specs = []
    for loader in loaders:
        program = get_program(loader)
        specs.append((program.types, program.nullable) if isinstance(program, ScalarProgram) else identity_spec(loader))
    if any(spec is None or (not spec[0] and not spec[1]) for spec in specs):
        return function
    types = tuple(dict.fromkeys(cls for spec in specs for cls in spec[0]))
    if float in types:
        # A float loader can accept an int and change its type before the int
        # alternative is reached. Leave all int inputs to the original union.
        types = tuple(cls for cls in types if cls is not int)
    return register_program(
        function,
        ScalarProgram(
            function,
            types,
            nullable=any(spec[1] for spec in specs),
            coerce_int=float in types,
        ),
    )


def get_program(function):  # noqa: PLR0911

    if type(function) is BuiltinFunctionType:
        from adaptix._internal.code_tools.native_callable import NativeCode  # noqa: PLC0415

        if isinstance(function.__self__, NativeCode):
            return function.__self__.program
    if function is none_loader:
        return ScalarProgram(function, (), nullable=True)
    if function is UUID or function is UUID.__str__:
        return UUIDProgram(function, loading=function is UUID)

    if function is decimal_strict_coercion_loader or function is Decimal.__str__:
        return DecimalProgram(function, loading=function is decimal_strict_coercion_loader)

    for cls in (date, time, datetime):
        if function is cls.isoformat:
            return DateTimeProgram(function, loading=False, cls=cls)
    for loader, cls in IDENTITY_LOADERS:
        if function is loader:
            return ScalarProgram(function, (cls,), coerce_int=cls is float)
    reference = PROGRAMS.get(function) if type(function) is FunctionType else None
    return reference() if reference is not None else None


def describe_enum(function, mapping, enum, *, loading):
    return register_program(function, EnumProgram(function, tuple(mapping.items()), enum, loading))
