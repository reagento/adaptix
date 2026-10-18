import ctypes
import struct
import sys
from dataclasses import dataclass
from functools import cache
from types import BuiltinFunctionType

from adaptix._internal.code_tools.cpython_layout.selection import get_cpython_layout
from adaptix._internal.code_tools.native_callable import NativeCode
from adaptix._internal.code_tools.native_dictionary import guard_dictionary_value
from adaptix._internal.compat import CompatExceptionGroup
from adaptix._internal.definitions import DebugTrail
from adaptix._internal.morphing.load_error import LoadError, UnionLoadError
from adaptix._internal.morphing.native import descriptions
from adaptix._internal.morphing.native.plan import ModelLoaderPlan, UnionPlan
from adaptix._internal.morphing.native.registry import identity_spec
from adaptix._internal.morphing.native.x86_64.scalar import get_program

LAYOUT = get_cpython_layout()

@dataclass(frozen=True)
class LiteralProgram(descriptions.LiteralProgram):
    def emit(self, c):
        function = descriptions.resolve_function(self.function)
        if sys.version_info[:2] not in {(3, 13), (3, 14), (3, 15)}:
            return c.call(function, c.data)
        from adaptix._internal.code_tools.native_access import supports_dictionary_cache  # noqa: PLC0415

        if not supports_dictionary_cache():
            return c.call(function, c.data)
        generic, accepted, done = c.label("literal_slow"), c.label("literal_ok"), c.label("literal_done")
        result = c.slot(owned=True)
        integers = all(type(value) is int for value in self.cases)
        if integers and not integer_layout_supported():
            return c.call(function, c.data)
        c.branch_if_type(c.data, int if integers else str, generic, invert=True)
        for value in self.cases:
            next_case = c.label("next_literal")
            c.branch_if(c.data, value, accepted)
            if integers:
                match_integer(c, value, next_case)
            else:
                c.asm.load(0, c.data)
                c.match_ascii_key(value, next_case)
            c.asm.jump(accepted)
            c.asm.label(next_case)
        c.asm.jump(generic)
        c.asm.label(accepted)
        value = c.copy_reference(c.data)
        c.transfer(value, result)
        c.asm.jump(done)
        return c.fallback_result(result, function, generic, done)


@cache
def integer_layout_supported():
    if (
        LAYOUT is None or sys.version_info[:2] not in {(3, 13), (3, 14), (3, 15)}
        or sys.int_info.bits_per_digit != 30  # noqa: PLR2004
    ):
        return False
    for value in (0, 1, -1, (1 << 30) - 1):
        tag = ctypes.c_size_t.from_address(id(value) + LAYOUT.long_tag).value & ~4
        expected = 1 if value == 0 else 8 if value > 0 else 10
        if tag != expected:
            return False
        if value and ctypes.c_uint32.from_address(id(value) + LAYOUT.long_digits).value != abs(value):
            return False
    return True


def match_integer(c, value, failed):
    c.asm.load(0, c.data)
    c.asm.emit(
        b"\x48\x8b\x48" + bytes([c.layout.long_tag]) + b"\x48\x83\xe1\xfb",
        "load compact integer tag, excluding immortal flag",
    )
    tag = 1 if value == 0 else 8 if value > 0 else 10
    c.asm.emit(b"\x48\x83\xf9" + bytes([tag]), "check integer sign and digit count")
    c.asm.jump(failed, "nz")
    if value:
        c.asm.emit(b"\x81\x78" + bytes([c.layout.long_digits]) + struct.pack("<I", abs(value)), "compare integer digit")
        c.asm.jump(failed, "nz")


def resume_union(loaders, selected, tp, debug_trail, data, selected_error):
    errors = []
    unexpected = False
    for index, function in enumerate(loaders):
        try:
            if index == selected:
                raise selected_error  # noqa: TRY301
            result = function(data)
        except LoadError as error:
            errors.append(error)
        except Exception as error:
            if debug_trail != DebugTrail.ALL:
                raise
            errors.append(error)
            unexpected = True
        else:
            if not unexpected:
                return result
    if unexpected:
        raise CompatExceptionGroup(f"while loading {tp}", errors)
    if debug_trail == DebugTrail.DISABLE:
        raise LoadError
    raise UnionLoadError(f"while loading {tp}", errors)


@dataclass(frozen=True)
class TaggedUnionProgram(UnionPlan):
    variants: tuple
    tag: str

    def emit(self, c):
        from functools import partial  # noqa: PLC0415

        generic, done = c.label("union_slow"), c.label("union_done")
        result = c.slot(owned=True)
        tag_value = c.slot(owned=True)
        c.branch_if_type(c.data, dict, generic, invert=True)
        c.asm.load(0, c.data)
        c.asm.emit(
            b"\x48\x8b\x40" + bytes([c.layout.dict_keys]) + b"\x80\x78" + bytes([c.layout.keys_kind]) + b"\x00",
            "check Unicode dictionary keys",
        )
        c.asm.jump(generic, "z")
        missing = object()
        value = c.dict_lookup(c.data, self.tag, missing)
        c.transfer(value, tag_value)
        c.branch_if_type(tag_value, str, generic, invert=True)
        for index, cases in self.variants:
            matched, next_variant = c.label("union_variant"), c.label("next_union_variant")
            for case in cases:
                next_case = c.label("next_union_tag")
                c.branch_if(tag_value, case, matched)
                c.asm.load(0, tag_value)
                c.match_ascii_key(case, next_case)
                c.asm.jump(matched)
                c.asm.label(next_case)
            c.asm.jump(next_variant)
            c.asm.label(matched)
            c.release(tag_value, retained=True)
            value = c.inline_call(
                self.loaders[index], c.data,
                partial(resume_union, self.loaders, index, self.tp, self.debug_trail), c.data,
            )
            c.transfer(value, result)
            c.asm.jump(done)
            c.asm.label(next_variant)
        return c.fallback_result(result, self.fallback, generic, done, cleanup=(tag_value,))


@dataclass(frozen=True)
class UnionDumperProgram(descriptions.UnionDumperProgram):
    supports_consuming = True
    supports_borrowing = True

    def emit(self, c, *, consume=False, borrowed=False):
        from adaptix._internal.special_cases_optimization import as_is_stub  # noqa: PLC0415

        generic, done = c.label("union_dump_slow"), c.label("union_dump_done")
        result = c.data if consume else c.slot(owned=True)
        c.asm.load(0, c.data)
        c.asm.emit(b"\x48\x8b\x50" + bytes([c.layout.object_type]), "load union value type once")
        for cls, function in self.variants:
            next_case = c.label("next_dump_case")
            c.load(11, c.constant(cls))
            c.asm.emit(b"\x4c\x39\xda", "check union value type")
            c.asm.jump(next_case, "nz")
            if function is not as_is_stub or not consume:
                value = self.dump_variant(
                    c, cls, function, borrowed=borrowed, destination=None if consume else result,
                )
                if consume:
                    c.replace_reference(value, result)
                elif value != result:
                    c.transfer(value, result)
            c.asm.jump(done)
            c.asm.label(next_case)
        c.asm.label(generic)
        function = descriptions.resolve_function(self.function)
        held = c.copy_reference(c.data) if borrowed else None
        value = c.call(function, held if held is not None else c.data)
        if held is not None:
            c.release(held)
        if consume:
            c.replace_reference(value, result)
        else:
            c.transfer(value, result)
        c.asm.label(done)
        return result

    @staticmethod
    def dump_variant(c, cls, function, *, borrowed, destination):
        from adaptix._internal.special_cases_optimization import as_is_stub  # noqa: PLC0415

        if function is as_is_stub:
            return c.copy_reference(c.data)
        if not borrowed or is_container_copy(cls, function):
            return emit_dump_variant(c, cls, function, destination=destination)
        held = c.copy_reference(c.data)
        data, c.data = c.data, held
        value = emit_dump_variant(c, cls, function, destination=destination)
        c.data = data
        c.release(held)
        return value


def is_container_copy(cls, function):
    from adaptix._internal.morphing.native.x86_64.dict import DictCopyProgram  # noqa: PLC0415
    from adaptix._internal.morphing.native.x86_64.iterable import ListProgram  # noqa: PLC0415
    from adaptix._internal.special_cases_optimization import as_is_stub  # noqa: PLC0415

    program = get_program(function)
    return (
        (cls is dict and isinstance(program, DictCopyProgram) and not program.loading)
        or (
            cls is list and isinstance(program, ListProgram) and not program.loading
            and program.mapper is as_is_stub and program.dump_as in (list, tuple)
        )
    )


def emit_dump_variant(c, cls, function, *, destination=None):
    from adaptix._internal.morphing.native.x86_64.dict import DictCopyProgram  # noqa: PLC0415
    from adaptix._internal.morphing.native.x86_64.iterable import ListProgram, copy_identity_sequence  # noqa: PLC0415
    from adaptix._internal.special_cases_optimization import as_is_stub  # noqa: PLC0415

    program = get_program(function)
    if cls is dict and isinstance(program, DictCopyProgram) and not program.loading:
        return c.call_c("PyDict_Copy", c.data, destination=destination)
    if (
        cls is list and isinstance(program, ListProgram) and not program.loading
        and program.mapper is as_is_stub and program.dump_as in (list, tuple)
    ):
        return copy_identity_sequence(c, list, program.dump_as, destination=destination)
    return c.inline_call(function, c.data)


@dataclass(frozen=True)
class ContainerUnionProgram(UnionPlan):
    variants: tuple

    def emit(self, c):
        from functools import partial  # noqa: PLC0415

        generic, done = c.label("container_union_slow"), c.label("container_union_done")
        result = c.slot(owned=True)
        self.mapping_guard(c, generic)
        for index, classes in self.variants:
            selected, next_case = c.label("container_union_case"), c.label("container_union_next")
            for cls in classes:
                c.branch_if_type(c.data, cls, selected)
            c.asm.jump(next_case)
            c.asm.label(selected)
            value = c.inline_call(
                self.loaders[index], c.data,
                partial(resume_union, self.loaders, index, self.tp, self.debug_trail), c.data,
            )
            c.transfer(value, result)
            c.asm.jump(done)
            c.asm.label(next_case)
        return c.fallback_result(result, self.fallback, generic, done)

    def mapping_guard(self, c, generic):
        import collections.abc  # noqa: PLC0415

        from adaptix._internal.code_tools.native_access import LOOKUP, get_type_version  # noqa: PLC0415
        from adaptix._internal.morphing import iterable_provider  # noqa: PLC0415

        mapping = collections.abc.Mapping
        if (
            iterable_provider.CollectionsMapping is not mapping
            or type(mapping).__instancecheck__.__module__ != "abc"
            or mapping.__subclasshook__.__module__ != "collections.abc"
        ):
            c.asm.jump(generic)
            return
        guard_dictionary_value(c, vars(iterable_provider), "CollectionsMapping", mapping, None, generic)
        for cls, method in ((mapping, "__subclasshook__"), (type(mapping), "__instancecheck__")):
            LOOKUP(cls, method)
            c.load(0, c.constant(cls))
            c.asm.emit(
                b"\x81\xb8" + struct.pack("<iI", c.layout.type_version, get_type_version(cls)),
                "check Mapping method version",
            )
            c.asm.jump(generic, "nz")


def container_union_program(plan: UnionPlan):
    from adaptix._internal.morphing.native.x86_64.dict import DictCopyProgram  # noqa: PLC0415
    from adaptix._internal.morphing.native.x86_64.dict_mapper import DictProgram  # noqa: PLC0415
    from adaptix._internal.morphing.native.x86_64.iterable import ListProgram  # noqa: PLC0415
    from adaptix._internal.morphing.native.x86_64.scalar import ScalarProgram  # noqa: PLC0415

    variants = []
    has_container = False
    for index, loader in enumerate(plan.loaders):
        program = get_program(loader)
        if isinstance(program, ScalarProgram) and not program.coerce_int:
            classes = (*program.types, *((type(None),) if program.nullable else ()))
        elif isinstance(program, ListProgram) and program.origin is list and program.strict_coercion:
            classes = list, tuple
            has_container = True
        elif isinstance(program, (DictProgram, DictCopyProgram)):
            classes = (dict,)
            has_container = True
        else:
            return None
        variants.append((index, classes))
    return ContainerUnionProgram(variants=tuple(variants), **vars(plan)) if has_container else None


def build_union_program(plan: UnionPlan, c):  # noqa: C901, PLR0911, PLR0912
    from adaptix._internal.code_tools.native_access import supports_dictionary_cache  # noqa: PLC0415
    from adaptix._internal.morphing.native.x86_64.optional import OptionalProgram  # noqa: PLC0415
    from adaptix._internal.morphing.native.x86_64.scalar import ScalarProgram  # noqa: PLC0415

    scalar = get_program(plan.fallback)
    program = (
        scalar
        if isinstance(scalar, (ScalarProgram, OptionalProgram))
        else container_union_program(plan)
    )
    if isinstance(program, ContainerUnionProgram) and not supports_dictionary_cache():
        return None
    if program is not None:
        c.name = "native_scalar_union_loader"
        return program if c.has_validated_object_header else None
    if sys.version_info[:2] not in {(3, 13), (3, 14), (3, 15)}:
        return None
    from adaptix._internal.morphing.model.crown_definitions import InpDictCrown, InpFieldCrown  # noqa: PLC0415
    from adaptix._internal.morphing.native.x86_64.model import ModelProgram  # noqa: PLC0415

    if not supports_dictionary_cache():
        return None
    candidates = []
    for function in plan.loaders:
        if type(function) is not BuiltinFunctionType or not isinstance(function.__self__, NativeCode):
            return None
        program = function.__self__.program
        if not isinstance(program, ModelProgram):
            return None
        model = program.plan
        if not isinstance(model, ModelLoaderPlan):
            return None
        crown = model.name_layout.crown
        if not isinstance(crown, InpDictCrown) or not all(field.is_required for field in model.shape.fields):
            return None
        tags = {}
        for key, child in crown.map.items():
            if not isinstance(child, InpFieldCrown):
                return None
            mapper = model.field_loaders[child.id]
            literal = get_program(mapper)
            if isinstance(literal, LiteralProgram):
                tags[key] = literal.cases
            elif identity_spec(mapper) is None:
                return None
        candidates.append(tags)
    common = set(candidates[0]).intersection(*candidates[1:])
    for tag in sorted(common):
        cases = [candidate[tag] for candidate in candidates]
        flattened = [value for values in cases for value in values]
        if len(flattened) != len(set(flattened)):
            continue
        if not c.has_validated_object_header:
            return None
        return TaggedUnionProgram(
            variants=tuple(enumerate(cases)), tag=tag, **vars(plan),
        )
    return None
