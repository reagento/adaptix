from dataclasses import dataclass
from typing import get_args

from adaptix._internal.model_tools.definitions import DescriptorAccessor, ParamKind
from adaptix._internal.morphing.model.crown_definitions import (
    ExtraSkip,
    InpDictCrown,
    InpFieldCrown,
    OutDictCrown,
    OutFieldCrown,
)
from adaptix._internal.morphing.native.descriptions import ScalarProgram
from adaptix._internal.morphing.native.plan import IterablePlan, ModelDumperPlan, ModelLoaderPlan
from adaptix._internal.morphing.native.registry import get_program
from adaptix._internal.special_cases_optimization import as_is_stub

JSON_SCALARS = (str, int, float, bool, type(None))


@dataclass(frozen=True)
class ScalarOutput:
    types: tuple[type, ...]


@dataclass(frozen=True)
class ListOutput:
    item: object


@dataclass(frozen=True)
class ModelOutput:
    fields: tuple[tuple[str, str, object], ...]


def scalar_types(tp) -> tuple[type, ...]:
    if tp in JSON_SCALARS:
        return (tp,)
    args = get_args(tp)
    return args if args and all(arg in JSON_SCALARS for arg in args) else JSON_SCALARS


def describe_output(converter, tp=None, pending=None):
    if converter is as_is_stub:
        return ScalarOutput(scalar_types(tp))
    program = get_program(converter)
    if isinstance(program, ScalarProgram) and not program.coerce_int:
        types = (*program.types, type(None)) if program.nullable else program.types
        if types and all(cls in JSON_SCALARS for cls in types):
            return ScalarOutput(types)
    pending = set() if pending is None else pending
    if id(converter) in pending:
        return None
    pending = pending | {id(converter)}
    if isinstance(program, IterablePlan) and not program.loading and program.origin is list:
        args = get_args(tp)
        item = describe_output(program.mapper, args[0] if args else None, pending)
        return None if item is None else ListOutput(item)
    plan = getattr(program, "plan", None)
    if not isinstance(plan, ModelDumperPlan):
        return None
    return describe_model_output(plan, pending)


def describe_model_output(plan, pending):
    crown = plan.name_layout.crown
    if (
        not isinstance(crown, OutDictCrown) or crown.sieves or plan.name_layout.extra_move is not None
        or not all(type(key) is str for key in crown.map)
    ):
        return None
    fields = []
    for key, child in crown.map.items():
        if not isinstance(child, OutFieldCrown):
            return None
        field = plan.shape.fields_dict[child.id]
        if not field.is_required or not isinstance(field.accessor, DescriptorAccessor):
            return None
        output = describe_output(plan.fields_dumpers[field.id], field.type, pending)
        if output is None:
            return None
        fields.append((key, field.accessor.attr_name, output))
    return ModelOutput(tuple(fields))


def describe_model_input(converter):
    plan = getattr(get_program(converter), "plan", None)
    if not isinstance(plan, ModelLoaderPlan):
        return None
    crown = plan.name_layout.crown
    if (
        not isinstance(crown, InpDictCrown) or crown.extra_policy != ExtraSkip()
        or plan.name_layout.extra_move is not None or plan.skipped_fields
        or len(crown.map) != len(plan.shape.fields)
        or not all(isinstance(child, InpFieldCrown) for child in crown.map.values())
        or len({child.id for child in crown.map.values()}) != len(plan.shape.fields)
        or not all(param.kind == ParamKind.POS_OR_KW for param in plan.shape.params)
        or not all(type(key) is str for key in crown.map)
    ):
        return None
    for field_loader in plan.field_loaders.values():
        program = get_program(field_loader)
        if not isinstance(program, ScalarProgram) or not all(tp in JSON_SCALARS for tp in program.types):
            return None
    return plan
