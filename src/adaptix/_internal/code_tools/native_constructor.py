import ctypes
import dis
import inspect
import struct
import sys
from contextlib import suppress
from functools import cache
from threading import RLock
from types import CellType, FunctionType, MemberDescriptorType

from adaptix._internal.code_tools.cpython_layout.selection import get_cpython_layout
from adaptix._internal.code_tools.native_access import (
    DICT,
    GENERIC_GETTER,
    GET_SLOT,
    INLINE,
    IS_SUBTYPE,
    LOOKUP,
    SHARED_KEYS_LIMIT,
    SLOT,
    api,
    api_address,
    dictionary_attributes_supported,
    get_type_version,
    inline_index,
    member_offset,
    pointer,
    size,
)

TP_ALLOC = 47
TP_NEW = 65
TP_SETATTRO = 69
GET_TSTATE = api("PyThreadState_Get", ctypes.c_void_p)
GENERIC_SETTER = api_address("PyObject_GenericSetAttr")
GENERIC_ALLOCATOR = api_address("PyType_GenericAlloc")
DEFAULT_EVAL = api_address("_PyEval_EvalFrameDefault") or 0
GET_EVAL = api("_PyInterpreterState_GetEvalFrameFunc", ctypes.c_void_p, ctypes.c_void_p)

LAYOUT = get_cpython_layout()
EVAL_MASK = ~255


@cache
def interpreter_eval_offset() -> int | None:
    if LAYOUT is None or not DEFAULT_EVAL or GET_EVAL is None or GET_TSTATE is None:
        return None
    offset = LAYOUT.interpreter_eval_frame
    if offset is None:
        return None
    # A default evaluator may correspond to NULL in several nearby fields.
    # Verify that the actual getter loads this field before bypassing the API.
    address = ctypes.cast(GET_EVAL, ctypes.c_void_p).value
    if address is None:
        return None
    code = ctypes.string_at(address, 32)
    if code.startswith(b"\xf3\x0f\x1e\xfa"):
        code = code[4:]
    if (
        not code.startswith(b"\x55\x48\x89\xe5\x48\x8b\x8f")
        or code[11:15] != b"\x48\x85\xc9\xb8" or code[19:25] != b"\x48\x0f\x45\xc1\x5d\xc3"
        or struct.unpack("<i", code[7:11])[0] != offset
        or struct.unpack("<I", code[15:19])[0] != DEFAULT_EVAL
    ):
        return None
    tstate = GET_TSTATE()
    interpreter = pointer(tstate + LAYOUT.thread_interpreter)
    observed = pointer(interpreter + offset) or DEFAULT_EVAL
    return offset if observed == GET_EVAL(interpreter) else None


def initializer_fields(  # noqa: C901, PLR0911, PLR0912
    function, parameters: tuple[str, ...], code=None,
) -> tuple[str, ...] | None:
    if LAYOUT is None or type(function) is not FunctionType:
        return None
    code = function.__code__ if code is None else code
    frozen = object_setter_cell(function, code) is not None
    tuple_probe = (object(), object())
    if (
        code.co_cellvars
        or code.co_exceptiontable
        or code.co_flags & (inspect.CO_VARARGS | inspect.CO_VARKEYWORDS | inspect.CO_GENERATOR | inspect.CO_COROUTINE)
        or code.co_argcount + code.co_kwonlyargcount != len(parameters) + 1
        or code.co_varnames[1 : len(parameters) + 1] != parameters
        or pointer(id(function) + LAYOUT.offset("function_code")) != id(code)
        or pointer(id(function) + LAYOUT.offset("function_defaults"))
        != (0 if function.__defaults__ is None else id(function.__defaults__))
        or size(id(tuple_probe) + LAYOUT.var_size) != len(tuple_probe)
        or pointer(id(tuple_probe) + LAYOUT.tuple_items) != id(tuple_probe[0])
    ):
        return None
    path = explicit_initializer_path(function, parameters, code) if not frozen else None
    if code.co_freevars and not frozen and path is None:
        return None
    operations: list[tuple[str, object]] = []
    for instruction in (path[0] if path is not None else dis.get_instructions(code, adaptive=False)):
        if instruction.opname in {"RESUME", "NOP", "EXTENDED_ARG"}:
            continue
        if frozen and instruction.opname == "COPY_FREE_VARS" and instruction.argval == 1:
            continue
        if instruction.opname in {"LOAD_FAST_BORROW_LOAD_FAST_BORROW", "LOAD_FAST_LOAD_FAST"}:
            operations.extend(("LOAD_FAST", name) for name in instruction.argval)
        else:
            if instruction.opname in {"LOAD_FAST_BORROW", "LOAD_FAST_CHECK"}:
                operation = "LOAD_FAST"
            elif instruction.opname == "LOAD_COMMON_CONSTANT":
                operation = "LOAD_CONST"
            else:
                operation = instruction.opname
            operations.append((operation, instruction.argval))
    if operations[-2:] == [("LOAD_CONST", None), ("RETURN_VALUE", None)]:
        operations = operations[:-2]
    elif operations[-1:] == [("RETURN_CONST", None)]:
        operations = operations[:-1]
    else:
        return None
    stride = 7 if frozen else 3
    if len(operations) != len(parameters) * stride:
        return None
    fields = []
    for index, parameter in enumerate(parameters):
        if frozen:
            receiver, method, self_load, name, value, call, pop = operations[index * stride:index * stride + stride]
            if (
                receiver != ("LOAD_DEREF", code.co_freevars[0]) or method != ("LOAD_ATTR", "__setattr__")
                or self_load != ("LOAD_FAST", code.co_varnames[0])
                or name[0] != "LOAD_CONST" or type(name[1]) is not str
                or value != ("LOAD_FAST", parameter) or call != ("CALL", 3) or pop != ("POP_TOP", None)
            ):
                return None
            fields.append(name[1])
            continue
        load, self_load, store = operations[index * 3:index * 3 + 3]
        if load != ("LOAD_FAST", parameter) or self_load != ("LOAD_FAST", code.co_varnames[0]):
            return None
        if store[0] != "STORE_ATTR" or type(store[1]) is not str:
            return None
        fields.append(store[1])
    return tuple(fields) if len(set(fields)) == len(fields) else None


def explicit_initializer_path(function, parameters, code):  # noqa: C901, PLR0911
    if not code.co_freevars or not function.__closure__ or CellType.__basicsize__ != LAYOUT.cell_size:
        return None
    instructions = list(dis.get_instructions(code, adaptive=False))
    offsets = {instruction.offset: index for index, instruction in enumerate(instructions)}
    cells = dict(zip(code.co_freevars, function.__closure__, strict=True))
    selected, checks, index = [], {}, 0
    while index < len(instructions):
        instruction = instructions[index]
        index += 1
        if instruction.opname in {"COPY_FREE_VARS", "RESUME", "NOP", "EXTENDED_ARG", "NOT_TAKEN"}:
            continue
        if instruction.opname in {"POP_JUMP_IF_FALSE", "POP_JUMP_FORWARD_IF_FALSE"}:
            if len(selected) < 3:  # noqa: PLR2004
                return None
            argument, sentinel, comparison = selected[-3:]
            if (
                argument.opname not in {"LOAD_FAST", "LOAD_FAST_BORROW", "LOAD_FAST_CHECK"}
                or argument.argval not in parameters or sentinel.opname != "LOAD_DEREF"
                or sentinel.argval not in cells or comparison.opname != "IS_OP" or comparison.argval != 0
                or instruction.argval not in offsets or instruction.argval <= instruction.offset
            ):
                return None
            cell = cells[sentinel.argval]
            if type(cell) is not CellType:
                return None
            argument_index = parameters.index(argument.argval)
            if argument_index in checks and checks[argument_index] is not cell:
                return None
            checks[argument_index] = cell
            del selected[-3:]
            index = offsets[instruction.argval]
        elif instruction.opname == "JUMP_FORWARD":
            if instruction.argval not in offsets or instruction.argval <= instruction.offset:
                return None
            index = offsets[instruction.argval]
        else:
            selected.append(instruction)
            if instruction.opname in {"RETURN_VALUE", "RETURN_CONST"}:
                break
    return (selected, checks) if checks else None


def object_setter_cell(function, code):
    if not code.co_freevars or len(code.co_freevars) != 1 or not function.__closure__:
        return None
    cell = function.__closure__[0]
    if (
        type(cell) is not CellType
        or CellType.__basicsize__ != LAYOUT.cell_size
        or pointer(id(cell) + LAYOUT.cell_contents) != id(object)
    ):
        return None
    return cell


def monitoring_disabled(function, tstate: int) -> bool:
    monitoring = getattr(sys, "monitoring", None)
    if LAYOUT is None or monitoring is None or GET_EVAL is None or not DEFAULT_EVAL:
        return False
    if pointer(tstate + LAYOUT.offset("thread_profile")) or pointer(tstate + LAYOUT.offset("thread_trace")):
        return False
    if GET_EVAL(pointer(tstate + LAYOUT.offset("thread_interpreter"))) != DEFAULT_EVAL:
        return False
    for tool in range(6):
        if monitoring.get_events(tool) or monitoring.get_local_events(tool, function.__code__):
            return False
    return True


class SimpleConstructorCache(ctypes.Structure):
    _fields_ = [
        ("type_pointer", ctypes.c_void_p), ("version", ctypes.c_uint32), ("kind", ctypes.c_uint32),
        ("init_pointer", ctypes.c_void_p), ("code_pointer", ctypes.c_void_p),
        ("offsets_pointer", ctypes.c_void_p), ("basic_size", ctypes.c_ssize_t),
        ("eval_version", ctypes.c_size_t), ("misses", ctypes.c_uint32), ("max_index", ctypes.c_uint32),
        ("indices_pointer", ctypes.c_void_p),
        ("setter_cell", ctypes.c_void_p),
        ("branch_cells_pointer", ctypes.c_void_p),
    ]

    def __init__(self, cls: type, parameters: tuple[str, ...]):
        super().__init__()
        self.cls = cls
        self.parameters = parameters
        with suppress(ValueError):
            self.field_names = initializer_fields(LOOKUP(cls, "__init__"), parameters)
        self.offsets = (ctypes.c_ssize_t * len(parameters))()
        self.indices = (ctypes.c_uint8 * len(parameters))()
        self.offsets_pointer = ctypes.addressof(self.offsets)
        self.indices_pointer = ctypes.addressof(self.indices)
        self.branch_cells = (ctypes.c_void_p * len(parameters))()
        self.init_owner = None
        self.code_owner = None
        self.update_lock = RLock()

    def __call__(self, model):
        state = self.specialize(model)
        with self.update_lock:
            self.kind = 0
            self.misses += 1
            if state is None:
                return
            function, code, version, kind, basic_size, offsets, indices, eval_version, branches = state
            self.init_owner = function
            self.code_owner = code
            cell = object_setter_cell(function, code)
            if code.co_freevars and cell is None and not branches:
                return
            self.setter_cell = id(cell) if cell is not None else 0
            self.type_pointer = id(self.cls)
            self.version = version
            self.init_pointer = id(function)
            self.code_pointer = id(self.code_owner)
            self.basic_size = basic_size
            self.eval_version = eval_version
            self.max_index = max(indices, default=0)
            self.branch_cells_pointer = ctypes.addressof(self.branch_cells) if branches else 0
            for index in range(len(self.parameters)):
                self.branch_cells[index] = id(branches[index]) if index in branches else 0
            for index, offset in enumerate(offsets):
                self.offsets[index] = offset
            for index, value in enumerate(indices):
                self.indices[index] = value
            self.kind = kind

    def specialize(self, model):  # noqa: C901, PLR0911
        cls = self.cls
        if (
            LAYOUT is None or GET_TSTATE is None or GET_SLOT is None or LOOKUP is None
            or type(model) is not cls or type(cls) is not type
            or GET_SLOT(cls, TP_NEW) != GET_SLOT(object, TP_NEW)
            or GET_SLOT(cls, TP_ALLOC) != GENERIC_ALLOCATOR
            or pointer(id(cls) + LAYOUT.type_getattro) != GENERIC_GETTER
        ):
            return None
        function = LOOKUP(cls, "__init__")
        version = get_type_version(cls)
        if not version:
            return None
        code = getattr(function, "__code__", None)
        if GET_SLOT(cls, TP_SETATTRO) != GENERIC_SETTER and (
            type(function) is not FunctionType or object_setter_cell(function, code) is None
        ):
            return None
        names = initializer_fields(function, self.parameters, code)
        path = explicit_initializer_path(function, self.parameters, code) if type(function) is FunctionType else None
        branches = path[1] if path is not None else {}
        tstate = GET_TSTATE()
        eval_version = size(tstate + LAYOUT.thread_eval_breaker) & EVAL_MASK if tstate else 0
        if names is None or not tstate or not monitoring_disabled(function, tstate):
            return None
        if branches and len(names) > SHARED_KEYS_LIMIT:
            return None
        basic_size = size(id(cls) + LAYOUT.type_basic_size)
        if (
            len(names) > SHARED_KEYS_LIMIT and names == getattr(self, "field_names", None)
            and dictionary_attributes_supported(cls, names)
        ):
            return function, code, version, DICT, basic_size, [0] * len(names), [], eval_version, branches
        offsets, indices = [], []
        kind = SLOT
        for name in names:
            descriptor = None
            with suppress(ValueError):
                descriptor = LOOKUP(cls, name)
            offset = member_offset(descriptor, basic_size)
            if offset is not None:
                member = pointer(id(descriptor) + LAYOUT.member_descriptor_member)
                if (
                    type(descriptor) is not MemberDescriptorType or not IS_SUBTYPE(cls, descriptor.__objclass__)
                    or ctypes.c_int.from_address(member + LAYOUT.member_flags).value
                ):
                    return None
            else:
                # Reuse the guarded reader's descriptor and inline-values checks.
                from adaptix._internal.code_tools.native_access import AttributeCache  # noqa: PLC0415

                storage = AttributeCache(name).specialize(cls, version)
                index = inline_index(cls, name)
                if storage is None or storage[3] != INLINE or index is None:
                    return None
                kind = INLINE
                offset = storage[1]
                indices.append(index)
            offsets.append(offset)
        # Mixed slot/dictionary layouts use the ordinary initializer.
        if kind == INLINE and len(indices) != len(names):
            return None
        return function, code, version, kind, basic_size, offsets, indices, eval_version, branches
