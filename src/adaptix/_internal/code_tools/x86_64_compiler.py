import ctypes
import platform
import struct
import sys
import sysconfig
from collections.abc import Callable
from functools import partial
from keyword import iskeyword
from types import BuiltinFunctionType
from typing import Any, Literal, cast, overload

from adaptix._internal.code_tools.cpython_layout.selection import get_cpython_layout, require_cpython_layout
from adaptix._internal.code_tools.native_callable import NativeClosure, NativeCode
from adaptix._internal.code_tools.x86_64_assembler import (
    ARG_REGISTERS,
    REGISTERS,
    Address,
    Immediate,
    Slot,
    X86Assembler,
)
from adaptix._internal.code_tools.x86_64_dictionary import (
    emit_match_ascii_key,
    emit_ordered_dictionary_row,
    emit_ordered_key_compare,
    emit_probe_dictionary,
)

MAX_STACK_SIZE = 65536
MAX_INLINE_STACK_SIZE = 16384
MAX_INLINE_CODE_SIZE = 65536
INLINE_FIELD_LIMIT = 30


def bind_native_arguments(parameters, defaults, /, *args, **kwargs):
    if len(args) > len(parameters):
        raise TypeError(f"Expected at most {len(parameters)} positional arguments")
    missing = object()
    required = len(parameters) - len(defaults)
    values = [*args, *([missing] * (len(parameters) - len(args)))]
    for name, value in kwargs.items():
        try:
            index = parameters.index(name)
        except ValueError:
            raise TypeError(f"Unexpected keyword argument {name!r}") from None
        if index < len(args):
            raise TypeError(f"Multiple values for argument {name!r}")
        values[index] = value
    for index, value in enumerate(values):
        if value is missing:
            if index < required:
                raise TypeError(f"Missing required argument {parameters[index]!r}")
            values[index] = defaults[index - required]
    return tuple(values)


def omitted_kwargs(parameters, omitted, *values):
    return {name: value for name, value in zip(parameters, values, strict=True) if value is not omitted}


def construct_omitted(cls, parameters, omitted, *values):
    return cls(**omitted_kwargs(parameters, omitted, *values))


def inline_refcount_mode() -> str | None:
    layout = get_cpython_layout()
    if layout is None:
        return None
    probe = object()
    # Python tracing can retain another reference in the frame's locals dict.
    references = ctypes.c_ssize_t.from_address(id(probe) + layout.object_refcount).value
    # 3.14 can pass a borrowed argument to getrefcount, avoiding the temporary
    # reference added by earlier interpreters.
    if (
        references < 1 or sys.getrefcount(probe) not in (references, references + 1)
        or ctypes.c_void_p.from_address(id(probe) + layout.object_type).value != id(object)
    ):
        return None
    mode = "legacy"
    if sys.version_info >= (3, 14):
        mode = "immortal32"
    elif sys.version_info >= (3, 12):
        mode = "immortal64"
    return mode


def check_native_platform() -> None:
    if (
        sys.implementation.name != "cpython"
        or sys.platform != "linux"
        or platform.machine().lower() not in {"x86_64", "amd64"}
        or ctypes.sizeof(ctypes.c_void_p) != 8  # noqa: PLR2004
        or sysconfig.get_config_var("Py_GIL_DISABLED")
    ):
        raise RuntimeError("The x86-64 backend requires a GIL-enabled CPython on Linux x86-64")
    require_cpython_layout()


class X86Compiler:
    """Lower object programs to x86-64 System V instructions.

    Every non-null owned slot contains one new reference. All exits release
    these references; the exception indicator is saved during error cleanup.
    The assembler factory creates every independent fragment, including error
    recovery and function entries. It must implement the x86 encoding contract;
    other architectures supply a complete NativeCodeGenerator implementation.
    """

    def __init__(
        self, name: str, *, assembler_factory: Callable[[], X86Assembler] = X86Assembler,
        parameters: tuple[str, ...] = ("data",), defaults: tuple[Any, ...] = (),
        bound_context: bool = False,
    ):
        check_native_platform()
        if len(defaults) > len(parameters) or len(set(parameters)) != len(parameters):
            raise ValueError("Invalid native function parameters")
        if any(not parameter.isidentifier() or iskeyword(parameter) for parameter in parameters):
            raise ValueError("Native parameter names must be identifiers")
        self.parameters = parameters
        self.defaults = defaults
        self.layout = get_cpython_layout()
        self.name = name
        self.program_resolver: Callable[[Any], Any] | None = None
        self.callable_wrapper_type: type | None = None
        self.assembler_factory = assembler_factory
        self.asm = self.assembler_factory()
        self.constants: list[Any] = []
        self.owned: list[Slot] = []
        self.lazy: dict[Slot, tuple[Any, tuple[Slot | Immediate, ...], bool]] = {}
        self.local_owned: list[Slot] | None = None
        self.call_error_label = "error"
        self.cold_handlers: list[Callable[[], None]] = []
        self.context_pointers: dict[str, Slot] = {}
        self.saved_registers: dict[int, Slot] = {}
        self.loop_suspensions: list[tuple[dict[int, Slot], str, str] | None] = []
        self.loop_registers_in_use = False
        self.refcount_mode = inline_refcount_mode()
        self.dealloc_address = (
            ctypes.cast(ctypes.pythonapi._Py_Dealloc, ctypes.c_void_p).value
            if self.refcount_mode is not None and hasattr(ctypes.pythonapi, "_Py_Dealloc") else None
        )
        self.dict_from_items = (
            sys.version_info[:2] in {(3, 12), (3, 13), (3, 14), (3, 15)}
            and hasattr(ctypes.pythonapi, "_PyDict_FromItems")
        )
        self.slot_count = 0
        self.label_count = 0
        self.data = self.slot()
        self.bound_context = self.slot() if bound_context else None
        if self.bound_context is not None:
            offset = require_cpython_layout().tuple_items + NativeClosure._fields.index("bound_context") * 8
            self.asm.emit_memory(b"\x48\x8b", 0x07, offset, "load native closure context from owner")
            self.asm.store(self.bound_context)
        self.arguments = (self.data, *(self.slot() for _ in parameters[1:])) if parameters else ()
        if parameters == ("data",) and not defaults:
            self.parse_argument()
        else:
            self.parse_arguments()
        self.body_offset = len(self.asm.code)

    def offset(self, name: str) -> int:
        if self.layout is None:
            raise RuntimeError("No CPython layout is available for native code generation")
        return self.layout.offset(name)

    def parse_arguments(self) -> None:
        slow, ready = self.label("bind_arguments"), self.label("arguments_ready")
        self.asm.test_jump(1, slow, "nz")
        required = len(self.parameters) - len(self.defaults)
        self.asm.emit(b"\x48\x81\xfa" + struct.pack("<I", required), f"cmp rdx, {required}")
        self.asm.jump(slow, "b")
        self.asm.emit(b"\x48\x81\xfa" + struct.pack("<I", len(self.parameters)), f"cmp rdx, {len(self.parameters)}")
        self.asm.jump(slow, "a")
        for index, target in enumerate(self.arguments):
            if index >= required:
                self.load(0, self.constant(self.defaults[index - required]))
                self.asm.store(target)
                absent = self.label("default_argument")
                self.asm.emit(b"\x48\x81\xfa" + struct.pack("<I", index + 1), f"cmp rdx, {index + 1}")
                self.asm.jump(absent, "b")
            self.asm.emit(b"\x48\x8b\x86" + struct.pack("<i", index * 8), f"load argument {index}")
            self.asm.store(target)
            if index >= required:
                self.asm.label(absent)
        self.asm.label(ready)
        self.argument_ready = ready
        self.cold_handlers.append(lambda: self.bind_arguments(slow, ready))

    def bind_arguments(self, entry: str, ready: str) -> None:
        args, nargs, keywords = self.slot(), self.slot(), self.slot()
        self.asm.label(entry)
        self.asm.store(args, 6)
        self.asm.store(nargs, 2)
        self.asm.store(keywords, 1)
        binder = self.constant(partial(bind_native_arguments, self.parameters, self.defaults))
        if hasattr(ctypes.pythonapi, "PyObject_Vectorcall"):
            bound = self.call_c("PyObject_Vectorcall", binder, args, nargs, keywords)
        else:
            kwargs = self.vectorcall_keywords(args, nargs, keywords)
            bound = self.call_c("PyObject_VectorcallDict", binder, args, nargs, kwargs)
            self.release(kwargs, nonnull=True)
        for index, target in enumerate(self.arguments):
            value = self.call_c("PyTuple_GetItem", bound, Immediate(index), result="pointer")
            self.asm.load(0, value)
            self.asm.store(target)
        self.release(bound, nonnull=True)
        self.asm.jump(ready)

    def vectorcall_keywords(self, args: Slot, nargs: Slot, keywords: Slot) -> Slot:
        """Build a keyword dictionary for CPython 3.10's exported call API."""
        kwargs = self.call_c("PyDict_New")
        done, loop = self.label("keywords_ready"), self.label("copy_keyword")
        self.branch_if_null(keywords, done)
        count = self.call_c("PyTuple_Size", keywords, result="pointer")
        index = self.slot()
        self.load(0, Immediate(0))
        self.asm.store(index)
        self.asm.label(loop)
        self.asm.load(0, index)
        self.asm.load(11, count)
        self.asm.emit(b"\x4c\x39\xd8", "cmp rax, r11  # keyword count")
        self.asm.jump(done, "ae")
        key = self.call_c("PyTuple_GetItem", keywords, index, result="pointer")
        self.asm.load(0, nargs)
        self.asm.load(11, index)
        self.asm.emit(b"\x4c\x01\xd8", "add rax, r11  # keyword argument index")
        self.asm.load(11, args)
        self.asm.emit(b"\x49\x8b\x04\xc3", "mov rax, [r11+rax*8]  # keyword value")
        value = self.slot()
        self.asm.store(value)
        self.call_c("PyDict_SetItem", kwargs, key, value, result="int")
        self.asm.load(0, index)
        self.asm.emit(b"\x48\xff\xc0", "inc rax")
        self.asm.store(index)
        self.asm.jump(loop)
        self.asm.label(done)
        return kwargs

    def parse_argument(self) -> None:
        keywords, invalid, ready = (
            self.label("keyword_call"), self.label("invalid_arguments"), self.label("argument_ready"),
        )
        self.asm.test_jump(1, keywords, "nz")
        self.asm.emit(b"\x48\x83\xfa\x01", "cmp rdx, 1")
        self.asm.jump(invalid, "nz")
        self.asm.emit(b"\x48\x8b\x06", "mov rax, [rsi]")
        self.asm.store(self.data)
        self.asm.label(ready)
        self.argument_ready = ready
        self.cold_handlers.append(lambda: self.parse_keyword_argument(keywords, invalid, ready))

    def parse_keyword_argument(self, entry: str, invalid: str, ready: str) -> None:
        args, nargs, keywords = self.slot(), self.slot(), self.slot()
        self.asm.label(entry)
        self.asm.store(args, 6)
        self.asm.store(nargs, 2)
        self.asm.store(keywords, 1)
        positional, matched = self.label("positional_argument"), self.label("matched_keyword")
        self.call_c("PyTuple_Size", keywords, result="pointer")
        self.asm.test_jump(0, positional)
        self.asm.emit(b"\x48\x83\xf8\x01", "cmp rax, 1")
        self.asm.jump(invalid, "nz")
        self.asm.load(0, nargs)
        self.asm.test_jump(0, invalid, "nz")
        key = self.call_c("PyTuple_GetItem", keywords, Immediate(0), result="pointer")
        self.branch_if(key, "data", matched)
        keyword = ctypes.create_string_buffer(b"data")
        self.constants.append(keyword)
        self.call_c(
            "PyUnicode_CompareWithASCIIString", key, Immediate(ctypes.addressof(keyword)), result="pointer",
        )
        self.asm.test_jump(0, invalid, "nz", bits=32)
        self.asm.label(matched)
        self.asm.load(0, args)
        self.asm.emit(b"\x48\x8b\x00", "mov rax, [rax]")
        self.asm.store(self.data)
        self.asm.jump(ready)
        self.asm.label(positional)
        self.asm.load(0, nargs)
        self.asm.emit(b"\x48\x83\xf8\x01", "cmp rax, 1")
        self.asm.jump(invalid, "nz")
        self.asm.load(0, args)
        self.asm.emit(b"\x48\x8b\x00", "mov rax, [rax]")
        self.asm.store(self.data)
        self.asm.jump(ready)
        self.asm.label(invalid)
        message = ctypes.create_string_buffer(f"{self.name}() takes exactly one argument named 'data'".encode())
        self.constants.append(message)
        self.call_c("PyErr_SetString", self.constant(TypeError), Immediate(ctypes.addressof(message)), result="void")
        self.asm.jump("error")

    def slot(self, *, owned: bool = False) -> Slot:
        slot = Slot(self.slot_count)
        self.slot_count += 1
        if owned:
            (self.owned if self.local_owned is None else self.local_owned).append(slot)
        return slot

    def owns(self, slot: Slot) -> bool:
        return slot in self.owned or (self.local_owned is not None and slot in self.local_owned)

    def reserve_loop_registers(self, *, nested: bool = False) -> bool:
        """Keep one loop's indices and container pointers across mapper calls."""
        if self.loop_registers_in_use:
            if not nested:
                return False
            saved = {register: self.slot() for register in (12, 13, 14, 15)}
            for register, slot in saved.items():
                self.asm.store(slot, register)
            error_label = self.label("restore_outer_loop_error")
            self.loop_suspensions.append((saved, error_label, self.call_error_label))
            self.call_error_label = error_label
        else:
            self.loop_suspensions.append(None)
        self.loop_registers_in_use = True
        for register in (12, 13, 14, 15):
            if register not in self.saved_registers:
                self.saved_registers[register] = self.slot()
        return True

    def release_loop_registers(self, *, reserved: bool = True) -> None:
        if not reserved:
            return
        suspension = self.loop_suspensions.pop()
        if suspension is None:
            self.loop_registers_in_use = False
        else:
            saved, error_label, error_target = suspension
            self.restore_loop_registers(saved)
            self.call_error_label = error_target
            self.cold_handlers.append(partial(self.restore_loop_error, saved, error_label, error_target))

    def restore_loop_registers(self, saved):
        for register, slot in saved.items():
            self.asm.load(register, slot)

    def restore_loop_error(self, saved, error_label, error_target):
        self.asm.label(error_label)
        self.restore_loop_registers(saved)
        self.asm.jump(error_target)

    def function_context(self, name: str) -> Slot:
        """Fetch a borrowed, per-call context pointer before entering the body.

        Only use this for values whose identity survives calls made by the
        builtin, such as the attached PyThreadState. The pointer lives in this
        call's stack frame and is never cached across calls or threads.
        """
        if name not in self.context_pointers:
            self.context_pointers[name] = self.slot()
        return self.context_pointers[name]

    def constant(self, value: Any) -> Immediate:
        self.constants.append(value)
        return Immediate(id(value))

    def label(self, prefix: str = "branch") -> str:
        self.label_count += 1
        return f"{prefix}_{self.label_count}"

    def load(self, register: int, value: Slot | Immediate | Address) -> None:
        if isinstance(value, Slot):
            self.asm.load(register, value)
            if value in self.lazy:
                # A dormant state is NULL internally, but Python callbacks see None.
                ready = self.label("state_argument")
                self.asm.emit(
                    bytes([0x48 | ((register >> 3) << 2) | (register >> 3), 0x85,
                           0xC0 | ((register & 7) << 3) | (register & 7)]),
                    f"test {REGISTERS[register]}, {REGISTERS[register]}",
                )
                self.asm.jump(ready, "nz")
                self.asm.mov_imm(register, self.constant(None).value)
                self.asm.label(ready)
        elif isinstance(value, Address):
            self.asm.lea(register, value.slot)
        else:
            self.asm.mov_imm(register, value.value)

    @overload
    def call_c(
        self, name: str | Immediate, *args: Slot | Immediate | Address,
        result: Literal["object"] = "object", error_label: str = "error", destination: Slot | None = None,
    ) -> Slot: ...

    @overload
    def call_c(
        self, name: str | Immediate, *args: Slot | Immediate | Address,
        result: Literal["pointer"], error_label: str = "error",
    ) -> Slot: ...

    @overload
    def call_c(
        self, name: str | Immediate, *args: Slot | Immediate | Address,
        result: Literal["int", "bool", "void"], error_label: str = "error",
    ) -> None: ...

    def call_c(
        self, name: str | Immediate, *args: Slot | Immediate | Address,
        result: str = "object", error_label: str = "error", destination: Slot | None = None,
    ) -> Slot | None:
        if destination is not None and (result != "object" or not self.owns(destination)):
            raise ValueError("A C call destination must be an owned object slot")
        if error_label == "error":
            error_label = self.call_error_label
        if (
            name == "PyObject_CallOneArg" and result == "object"
            and not hasattr(ctypes.pythonapi, "PyObject_CallOneArg")
        ):
            return self.call_one_arg_compat(args, destination, error_label)
        if len(args) > len(ARG_REGISTERS):
            raise ValueError("Native C calls support at most six arguments")
        self.load_c_arguments(args)
        if name == "Py_IncRef" and result == "void" and self.refcount_mode is not None:
            self.incref_rdi()
            return None
        # Variadic C functions require al=number of vector-register arguments.
        self.asm.emit(b"\x31\xc0", "xor eax, eax")
        self.asm.mov_imm(11, self.c_api_address(name))
        self.asm.emit(b"\x41\xff\xd3", f"call r11  # {name}")
        if result == "object":
            # A supplied destination must be empty, just like a newly allocated slot.
            slot = self.slot(owned=True) if destination is None else destination
            self.asm.store(slot)
            self.asm.test_jump(0, error_label)
            return slot
        if result == "pointer":
            slot = self.slot()
            self.asm.store(slot)
            return slot
        if result in {"int", "bool"}:
            self.asm.test_jump(0, error_label, "s" if result == "int" else "z", bits=32)
        elif result != "void":
            raise ValueError(f"Unknown native C call result kind: {result}")
        return None

    def call_one_arg_compat(self, args, destination, error_label) -> Slot:
        converted = self.vectorcall_address(args[0], tuple(args[1:]), (), error_label=error_label)
        if destination is not None:
            self.transfer(converted, destination)
            return destination
        return converted

    @staticmethod
    def c_api_address(name: str | Immediate) -> int:
        address = name.value if isinstance(name, Immediate) else (
            ctypes.cast(getattr(ctypes.pythonapi, name), ctypes.c_void_p).value
        )
        if address is None:
            raise RuntimeError(f"Missing CPython C API entry point: {name}")
        return address

    def load_c_arguments(self, args: tuple[Slot | Immediate | Address, ...]) -> None:
        for register, value in zip(ARG_REGISTERS, args, strict=False):
            self.load(register, value)
            if isinstance(value, Address):
                self.asm.mark_write(value.slot)

    def call(self, function: Any, *args: Slot | Immediate, error_label: str = "error") -> Slot:
        if (
            type(function) is BuiltinFunctionType and isinstance(function.__self__, NativeCode)
            and function.__self__.raw_entry_offset >= 0
            and len(args) == len(function.__self__.parameters) <= len(ARG_REGISTERS)
        ):
            return self.call_native_arguments(function, args, error_label)
        if len(args) == 1 and self.has_validated_object_header and type(function) is self.callable_wrapper_type:
            return self.call_recursive_wrapper(function, args[0], error_label)
        callable_ptr = self.constant(function)
        if not args:
            return self.call_c("PyObject_CallNoArgs", callable_ptr, error_label=error_label)
        if len(args) == 1 and hasattr(ctypes.pythonapi, "PyObject_CallOneArg"):
            return self.call_c("PyObject_CallOneArg", callable_ptr, args[0], error_label=error_label)
        return self.vectorcall_address(callable_ptr, args, (), error_label=error_label)

    def call_recursive_wrapper(self, function: Any, argument: Slot | Immediate, error_label: str) -> Slot:
        if self.layout is None or self.layout.type_cached_keys is None:
            return self.vectorcall_address(self.constant(function), (argument,), (), error_label=error_label)
        from adaptix._internal.code_tools.native_access import (  # noqa: PLC0415
            GENERIC_GETTER,
            LOOKUP,
            get_type_version,
            member_offset,
            pointer,
            supports_attribute_cache,
        )

        cls = type(function)
        offset = member_offset(LOOKUP(cls, "__call__"), cls.__basicsize__)
        if (
            not supports_attribute_cache()
            or offset is None
            or pointer(id(cls) + self.offset("type_getattro")) != GENERIC_GETTER
        ):
            return self.call_c("PyObject_CallOneArg", self.constant(function), argument, error_label=error_label)
        generic, done = self.label("recursive_wrapper_slow"), self.label("recursive_wrapper_done")
        result = self.slot(owned=True)
        self.load(0, self.constant(function))
        self.asm.emit(b"\x48\x8b\x50" + bytes([self.layout.object_type]), "load recursive wrapper class")
        self.load(11, self.constant(cls))
        self.asm.emit(b"\x4c\x39\xda", "check recursive wrapper class")
        self.asm.jump(generic, "nz")
        self.asm.emit(
            b"\x81\xba" + struct.pack("<iI", self.layout.type_version, get_type_version(cls)),
            "check recursive wrapper call slot",
        )
        self.asm.jump(generic, "nz")
        self.asm.emit(b"\x48\x8b\x80" + struct.pack("<i", offset), "load current recursive converter")
        self.asm.test_jump(0, generic)
        target = self.copy_loaded_reference()
        value = self.call_c("PyObject_CallOneArg", target, argument, error_label=error_label)
        self.transfer(value, result)
        self.release(target, nonnull=True)
        self.asm.jump(done)
        self.asm.label(generic)
        value = self.call_c("PyObject_CallOneArg", self.constant(function), argument, error_label=error_label)
        self.transfer(value, result)
        self.asm.label(done)
        return result

    def call_native(self, function: Any, argument: Slot | Immediate, error_label: str) -> Slot:
        """Enter a generated unary function directly, retaining CPython's recursion guard."""
        return self.call_native_arguments(function, (argument,), error_label)

    def call_native_arguments(self, function: Any, args: tuple[Slot | Immediate, ...], error_label: str) -> Slot:
        """Enter a generated function directly with its complete positional signature."""
        if error_label == "error":
            error_label = self.call_error_label
        self.constants.append(function)
        context = ctypes.create_string_buffer(b" while calling a Python object")
        self.constants.append(context)
        self.call_c(
            "Py_EnterRecursiveCall", Immediate(ctypes.addressof(context)), result="void",
        )
        # The C API returns nonzero, including positive 1, on failure.
        self.asm.test_jump(0, error_label, "nz", bits=32)
        self.load_c_arguments(args)
        self.asm.mov_imm(11, function.__self__.raw_address)
        self.asm.emit(b"\x41\xff\xd3", "call r11  # native object entry")
        result = self.slot(owned=True)
        self.asm.store(result)
        # Leave on NULL too, before the ordinary error handler normalizes the exception.
        self.call_c("Py_LeaveRecursiveCall", result="void")
        self.asm.load(0, result)
        self.asm.test_jump(0, error_label)
        return result

    def lazy_call(self, function: Any, *args: Slot | Immediate) -> Slot:
        """Reserve a state which is constructed only when an error handler needs it."""
        result = self.slot(owned=True)
        self.lazy[result] = function, args, False
        return result

    def lazy_c_call(self, name: str, *args: Slot | Immediate) -> Slot:
        """Box a native value only when a cold handler needs its Python object."""
        result = self.slot(owned=True)
        self.lazy[result] = name, args, True
        return result

    def initialize_lazy(self, slot: Slot) -> None:
        ready = self.label("state_initialized")
        self.branch_if_null(slot, ready, invert=True)
        function, args, is_c = self.lazy[slot]
        value = self.call_c(function, *args) if is_c else self.call(function, *args)
        self.transfer(value, slot)
        self.asm.label(ready)

    def vectorcall(self, function: Any, args: tuple[Slot | Immediate, ...], keyword_names: tuple[str, ...]) -> Slot:
        return self.vectorcall_address(self.constant(function), args, keyword_names)

    def construct_object(  # noqa: C901, PLR0912, PLR0915
        self, cls: Any, args: tuple[Slot | Immediate, ...], keyword_names: tuple[str, ...], parameters: tuple[str, ...],
        *, steal: bool = False, omitted: Any = None,
    ) -> Slot:
        """Allocate a proven plain Python model without executing its initializer frame."""
        if (
            not self.has_validated_object_header or sys.version_info[:2] not in {(3, 13), (3, 14), (3, 15)}
            or type(cls) is not type or not args or len(args) > 255  # noqa: PLR2004
            or (omitted is not None and len(args) > INLINE_FIELD_LIMIT)
            or (len(args) > INLINE_FIELD_LIMIT and not all(isinstance(value, Slot) for value in args))
        ):
            return (
                self.call(partial(construct_omitted, cls, parameters, omitted), *args)
                if omitted is not None else self.vectorcall(cls, args, keyword_names)
            )
        from adaptix._internal.code_tools.native_constructor import (  # noqa: PLC0415
            DEFAULT_EVAL,
            SimpleConstructorCache,
            interpreter_eval_offset,
        )

        cache = SimpleConstructorCache(cls, parameters)
        self.constants.append(cache)
        generic, initialize, done, slots = (
            self.label(prefix) for prefix in ("generic_constructor", "dynamic_init", "model_created", "slot_init")
        )
        result = self.slot(owned=True)
        self.constructor_guard(cls, cache, generic, check_code=False)
        storage = (
            self.slot(owned=True) if len(args) > INLINE_FIELD_LIMIT and getattr(cache, "field_names", None) else None
        )
        if storage is not None:
            storage_done = self.label("model_storage_ready")
            self.asm.emit(b"\x41\x83\x7b\x0c\x03", "cmp DWORD PTR [r11+12], 3  # dictionary storage")
            self.asm.jump(storage_done, "nz")
            dictionary = self.make_dict(dict(zip(
                cast(tuple[str, ...], cache.field_names), cast(tuple[Slot, ...], args), strict=True,
            )))
            self.transfer(dictionary, storage)
            self.asm.label(storage_done)
        allocated = self.call_c("PyType_GenericAlloc", self.constant(cls), Immediate(0))
        self.transfer(allocated, result)
        # GC during allocation can change the class, initializer, or tracing.
        self.constructor_guard(cls, cache, initialize)
        tstate = self.function_context("PyThreadState_Get")
        self.asm.load(0, tstate)
        self.asm.emit(
            b"\x48\x83\x78" + bytes([self.offset("thread_profile")]) + b"\x00",
            "cmp QWORD PTR [rax+80], 0  # profile callback",
        )
        self.asm.jump(initialize, "nz")
        self.asm.emit(
            b"\x48\x83\x78" + bytes([self.offset("thread_trace")]) + b"\x00",
            "cmp QWORD PTR [rax+88], 0  # trace callback",
        )
        self.asm.jump(initialize, "nz")
        self.asm.emit(b"\x48\x8b\x48" + bytes([self.offset("thread_interpreter")]), "mov rcx, [rax+16]  # interpreter")
        interpreter = self.slot()
        self.asm.store(interpreter, 1)
        self.asm.emit(
            b"\x48\x8b\x40" + bytes([self.offset("thread_eval_breaker")]) + b"\x48\x25\x00\xff\xff\xff",
            "mov rax, [rax+24]; and rax, -256",
        )
        self.asm.mov_imm(11, ctypes.addressof(cache))
        self.asm.emit(b"\x49\x3b\x43\x30", "cmp rax, [r11+48]  # instrumentation version")
        self.asm.jump(initialize, "nz")
        eval_offset = interpreter_eval_offset()
        if eval_offset is not None:
            evaluator_ready = self.label("default_evaluator")
            self.asm.load(0, interpreter)
            self.asm.emit(b"\x48\x8b\x80" + struct.pack("<i", eval_offset), f"mov rax, [rax+{eval_offset}]")
            self.asm.test_jump(0, evaluator_ready)
        else:
            evaluator = self.call_c("_PyInterpreterState_GetEvalFrameFunc", interpreter, result="pointer")
            self.asm.load(0, evaluator)
        self.asm.mov_imm(11, DEFAULT_EVAL)
        self.asm.emit(b"\x4c\x39\xd8", "cmp rax, r11  # default frame evaluator")
        self.asm.jump(initialize, "nz")
        if eval_offset is not None:
            self.asm.label(evaluator_ready)
        if omitted is not None:
            self.bind_omitted_defaults(cache, args, omitted, initialize)
        self.check_constructor_branches(cache, args, initialize)
        dictionary_init = self.label("dictionary_init")
        self.asm.mov_imm(11, ctypes.addressof(cache))
        if storage is not None:
            self.asm.emit(b"\x41\x83\x7b\x0c\x03", "cmp DWORD PTR [r11+12], 3")
            self.asm.jump(dictionary_init, "z")
        self.asm.emit(b"\x41\x83\x7b\x0c\x02", "cmp DWORD PTR [r11+12], 2  # slot storage")
        self.asm.jump(slots, "z")
        self.asm.load(2, result)
        self.asm.emit(b"\x49\x8b\x43\x28", "mov rax, [r11+40]  # basic size")
        self.asm.emit(b"\x0f\xb6\x0c\x02", "movzx ecx, BYTE PTR [rdx+rax]  # inline capacity")
        self.asm.emit(b"\x41\x3b\x4b\x3c", "cmp ecx, [r11+60]  # largest field index")
        self.asm.jump(initialize, "be")
        self.asm.emit(
            b"\xc6\x44\x02\x01" + bytes([len(args)]), f"mov BYTE PTR [rdx+rax+1], {len(args)}  # field count",
        )
        self.asm.emit(
            b"\x48\x8d\x54\x02" + bytes([self.offset("values_items")]) + b"\x48\x8d\x14\xca",
            "lea rdx, [rdx+rax+8]; lea rdx, [rdx+rcx*8]",
        )
        self.asm.emit(b"\x49\x8b\x73\x40", "mov rsi, [r11+64]  # insertion order")
        for index in range(len(args)):
            self.asm.emit(b"\x8a\x46" + bytes([index]), f"mov al, [rsi+{index}]")
            self.asm.emit(b"\x88\x42" + bytes([index]), f"mov [rdx+{index}], al")
        self.asm.label(slots)
        steal = (
            steal and all(isinstance(value, Slot) and self.owns(value) for value in args)
            and len(set(args)) == len(args)
        )
        self.asm.load(2, result)
        self.asm.mov_imm(11, cache.offsets_pointer)
        if steal:
            self.asm.emit(b"\x45\x31\xc0", "xor r8d, r8d  # consumed slot marker")
        for index, value in enumerate(args):
            self.load(7, value)
            if not steal:
                self.incref_rdi()
            self.asm.emit(b"\x49\x8b\x8b" + struct.pack("<i", index * 8), f"mov rcx, [r11+{index * 8}]")
            self.asm.emit(b"\x48\x89\x3c\x0a", "mov [rdx+rcx], rdi  # initialize owned field")
            if steal:
                self.asm.store(cast(Slot, value), 8, clear=True)
        self.asm.jump(done)
        self.asm.label(dictionary_init)
        if storage is not None:
            if sys.version_info[:2] == (3, 13):
                # GenericSetDict in 3.13 leaves inline values valid. The managed
                # setter invalidates them so attribute lookup uses the new dict.
                self.call_c("_PyObject_SetManagedDict", result, storage, result="int")
            else:
                self.call_c("PyObject_GenericSetDict", result, storage, Immediate(0), result="int")
            self.asm.jump(done)
        self.asm.label(initialize)
        if omitted is not None:
            self.initialize_omitted(cls, result, args, parameters, omitted)
        else:
            self.initialize_object(cls, result, args, keyword_names)
        self.asm.jump(done)
        self.asm.label(generic)
        value = (
            self.call(partial(construct_omitted, cls, parameters, omitted), *args)
            if omitted is not None else self.vectorcall(cls, args, keyword_names)
        )
        self.transfer(value, result)
        skip_learning = self.label("constructor_learning_done")
        self.learning_budget(cache, 56, skip_learning)
        self.release(self.call(cache, result))
        self.asm.label(skip_learning)
        self.asm.label(done)
        if storage is not None:
            self.release(storage)
        return result

    def check_constructor_branches(self, cache, args, initialize):
        done = self.label("constructor_branch_checks_done")
        self.asm.mov_imm(11, ctypes.addressof(cache))
        self.asm.emit(b"\x49\x8b\x43\x50\x48\x85\xc0", "load constructor sentinel cells")
        self.asm.jump(done, "z")
        for index, value in enumerate(args):
            checked = self.label("constructor_argument_checked")
            self.asm.emit(b"\x48\x8b\x88" + struct.pack("<i", index * 8), "load argument sentinel cell")
            self.asm.test_jump(1, checked)
            self.asm.emit(
                b"\x48\x8b\x49" + bytes([self.layout.cell_contents]) + b"\x48\x85\xc9",
                "load current initializer sentinel",
            )
            self.asm.jump(initialize, "z")
            self.load(7, value)
            self.asm.emit(b"\x48\x39\xcf", "check explicit argument against factory sentinel")
            self.asm.jump(initialize, "z")
            self.asm.label(checked)
        self.asm.label(done)

    def bind_omitted_defaults(self, cache, args, omitted, initialize):
        defaults = self.slot()
        self.asm.mov_imm(11, ctypes.addressof(cache))
        self.asm.emit(
            b"\x49\x8b\x43\x10\x48\x8b\x40" + bytes([self.layout.function_defaults]),
            "mov rax, [r11+16]; mov rax, [rax+56]  # current defaults",
        )
        self.asm.store(defaults)
        # Check every omitted binding before replacing any argument.
        for index, value in enumerate(args):
            present = self.label("explicit_argument")
            self.branch_if(value, omitted, present, invert=True)
            self.asm.load(0, defaults)
            self.asm.test_jump(0, initialize)
            needed = len(args) - index
            self.asm.emit(
                b"\x48\x81\x78" + bytes([self.layout.var_size]) + struct.pack("<i", needed),
                f"cmp default count, {needed}",
            )
            self.asm.jump(initialize, "b")
            self.asm.label(present)
        for index, value in enumerate(args):
            present = self.label("bound_argument")
            self.branch_if(value, omitted, present, invert=True)
            self.asm.load(0, defaults)
            self.asm.emit(b"\x48\x8b\x48" + bytes([self.layout.var_size]), "mov rcx, [rax+16]  # default count")
            displacement = self.layout.tuple_items - (len(args) - index) * 8
            self.asm.emit(
                b"\x48\x8b\x84\xc8" + struct.pack("<i", displacement),
                "mov rax, [rax+rcx*8+default_offset]",
            )
            bound = self.copy_loaded_reference()
            self.release(cast(Slot, value), retained=True)
            self.transfer(bound, cast(Slot, value))
            self.asm.label(present)

    def constructor_guard(self, cls, cache, fallback, *, check_code=True):
        self.asm.mov_imm(11, ctypes.addressof(cache))
        self.asm.emit(b"\x41\x83\x7b\x0c\x00", "cmp DWORD PTR [r11+12], 0  # constructor cache")
        self.asm.jump(fallback, "z")
        self.load(0, self.constant(cls))
        self.asm.emit(
            b"\x8b\x88" + struct.pack("<i", self.layout.type_version), "mov ecx, [rax+384]  # constructor type version",
        )
        self.asm.emit(b"\x41\x3b\x4b\x08", "cmp ecx, [r11+8]")
        self.asm.jump(fallback, "nz")
        if check_code:
            self.asm.emit(b"\x49\x8b\x43\x10", "mov rax, [r11+16]  # cached initializer")
            self.asm.emit(
                b"\x48\x8b\x40" + bytes([self.layout.function_code]), "mov rax, [rax+48]  # current code object",
            )
            self.asm.emit(b"\x49\x3b\x43\x18", "cmp rax, [r11+24]")
            self.asm.jump(fallback, "nz")
            plain = self.label("constructor_plain_assignment")
            self.asm.emit(b"\x49\x8b\x4b\x48\x48\x85\xc9", "load captured object setter cell")
            self.asm.jump(plain, "z")
            self.load(0, self.constant(object))
            self.asm.emit(b"\x48\x39\x41" + bytes([self.layout.cell_contents]), "check captured object setter")
            self.asm.jump(fallback, "nz")
            self.asm.label(plain)

    def initialize_object(self, cls, instance, args, keyword_names):
        positional_count = len(args) - len(keyword_names)
        positional = self.call_c("PyTuple_New", Immediate(positional_count))
        for index, value in enumerate(args[:positional_count]):
            self.call_c("Py_IncRef", value, result="void")
            self.call_c("PyTuple_SetItem", positional, Immediate(index), value, result="int")
        kwargs = None
        if keyword_names:
            kwargs = self.call_c("PyDict_New")
            for name, value in zip(keyword_names, args[positional_count:], strict=True):
                self.call_c("PyDict_SetItem", kwargs, self.constant(name), value, result="int")
        initializer = self.call_c("PyType_GetSlot", self.constant(cls), Immediate(60), result="pointer")
        absent = self.label("no_initializer")
        self.branch_if_null(initializer, absent)
        self.load_c_arguments((instance, positional, kwargs if kwargs is not None else Immediate(0)))
        self.asm.load(11, initializer)
        self.asm.emit(b"\x41\xff\xd3", "call r11  # current tp_init")
        self.asm.test_jump(0, self.call_error_label, "s", bits=32)
        self.asm.label(absent)
        self.release(positional)
        if kwargs is not None:
            self.release(kwargs)

    def initialize_omitted(self, cls, instance, args, parameters, omitted):
        kwargs = self.call(partial(omitted_kwargs, parameters, omitted), *args)
        positional = self.call_c("PyTuple_New", Immediate(0))
        initializer = self.call_c("PyType_GetSlot", self.constant(cls), Immediate(60), result="pointer")
        absent = self.label("no_initializer")
        self.branch_if_null(initializer, absent)
        self.load_c_arguments((instance, positional, kwargs))
        self.asm.load(11, initializer)
        self.asm.emit(b"\x41\xff\xd3\x85\xc0", "call r11; test eax, eax  # current tp_init")
        self.asm.jump(self.call_error_label, "s")
        self.asm.label(absent)
        self.release(positional)
        self.release(kwargs)

    def array(self, values: tuple[Slot | Immediate, ...]) -> Address | Immediate:
        slots = [self.slot() for _ in values]
        for slot, value in zip(reversed(slots), values, strict=True):
            self.load(0, value)
            self.asm.store(slot)
        return Address(slots[-1]) if slots else Immediate(0)

    def make_dict(self, items: dict[Any, Slot], *, consume: bool = False) -> Slot:
        """Build a dictionary from borrowed key/value arrays in one C call."""
        if consume and any(not self.owns(value) for value in items.values()):
            raise ValueError("Dictionary ownership transfer requires owned slots")
        if (
            self.has_validated_object_header and sys.version_info[:2] in {(3, 13), (3, 14), (3, 15)}
            and len(items) >= 2 and all(type(key) is str for key in items)  # noqa: PLR2004
        ):
            from adaptix._internal.code_tools.native_access import supports_dictionary_cache  # noqa: PLC0415
            from adaptix._internal.code_tools.native_dictionary import create_dictionary_template  # noqa: PLC0415

            if supports_dictionary_cache():
                template = create_dictionary_template(tuple(items))
                self.constants.append(template)
                if template.kind == 2 and template.tracked_copies and sys.version_info[:2] in {(3, 14), (3, 15)}:  # noqa: PLR2004
                    return self.new_shared_dict(items, template, consume)
                return self.copy_dict_template(items, template, consume)
        result = self.make_dict_from_items(items)
        if consume:
            for value in dict.fromkeys(items.values()):
                self.release(value, nonnull=True, retained=all(type(key) is str for key in items))
        return result

    def make_dict_from_items(self, items: dict[Any, Slot]) -> Slot:
        if self.dict_from_items:
            keys = tuple(items)
            key_array = (ctypes.c_void_p * len(keys))(*(id(key) for key in keys))
            self.constants.extend((keys, key_array))
            return self.call_c(
                "_PyDict_FromItems", Immediate(ctypes.addressof(key_array)), Immediate(1),
                self.array(tuple(items.values())), Immediate(1), Immediate(len(items)),
            )
        result = (
            self.call_c("_PyDict_NewPresized", Immediate(len(items)))
            if hasattr(ctypes.pythonapi, "_PyDict_NewPresized") else
            self.call_c("PyDict_New")
        )
        for key, value in items.items():
            self.call_c("PyDict_SetItem", result, self.constant(key), value, result="int")
        return result

    def copy_dict_template(self, items, template, consume):
        result = self.call_c("PyDict_Copy", self.constant(template.data))
        generic, done, no_gc = (
            self.label(prefix) for prefix in ("dict_template_changed", "dict_complete", "dict_no_gc")
        )
        self.check_dictionary_template(items, template, result, generic)
        self.populate_dictionary_values(items, template, consume, result, no_gc)
        self.asm.jump(done)
        self.asm.label(generic)
        self.release(result)
        rebuilt = self.make_dict_from_items(items)
        self.transfer(rebuilt, result)
        if consume:
            for value in dict.fromkeys(items.values()):
                self.release(value, nonnull=True, retained=True)
        self.asm.label(done)
        return result

    def check_dictionary_template(self, items, template, source, generic):
        """Leave verified key/value arrays in rdx/rsi; do not call Python."""
        self.load(0, source)
        count_check = (
            b"\x48\x83\x78" + bytes([self.layout.dict_used]) + bytes([len(items)]) if len(items) < (1 << 7) else
            b"\x48\x81\x78" + bytes([self.layout.var_size]) + struct.pack("<i", len(items))
        )
        self.asm.emit(count_check, f"cmp QWORD PTR [rax+16], {len(items)}")
        self.asm.jump(generic, "nz")
        self.asm.emit(b"\x48\x8b\x50" + bytes([self.layout.dict_keys]), "mov rdx, [rax+32]  # copied keys")
        self.asm.emit(
            b"\x80\x7a" + bytes([self.layout.keys_kind]) + bytes([template.kind]),
            f"cmp BYTE PTR [rdx+10], {template.kind}  # key kind",
        )
        self.asm.jump(generic, "nz")
        self.asm.emit(
            b"\x80\x7a" + bytes([self.layout.keys_index_bytes]) + bytes([template.index_bytes]),
            f"cmp BYTE PTR [rdx+9], {template.index_bytes}",
        )
        self.asm.jump(generic, "nz")
        if template.kind == 2:  # noqa: PLR2004
            self.asm.emit(
                b"\x48\x8b\x70" + bytes([self.layout.dict_values]), "mov rsi, [rax+40]  # shared-key value buffer",
            )
            self.asm.test_jump(6, generic)
            self.asm.emit(
                b"\x80\x3e" + bytes([max(template.value_offsets) // 8]),
                "cmp BYTE PTR [rsi], largest_value_index  # capacity",
            )
            self.asm.jump(generic, "be")
            self.asm.emit(b"\x48\x83\xc6" + bytes([self.layout.values_items]), "add rsi, 8  # value entries")
        else:
            self.asm.emit(b"\x48\x89\xd6", "mov rsi, rdx  # combined entries")
        self.load(8, self.constant(None))
        for key, key_offset, value_offset in zip(items, template.key_offsets, template.value_offsets, strict=True):
            self.load(9, self.constant(key))
            self.asm.emit(b"\x4c\x39\x8a" + struct.pack("<i", key_offset), f"cmp [rdx+{key_offset}], r9")
            self.asm.jump(generic, "nz")
            self.asm.emit(
                b"\x4c\x39\x86" + struct.pack("<i", value_offset),
                f"cmp [rsi+{value_offset}], r8  # None placeholder",
            )
            self.asm.jump(generic, "nz")
    def populate_dictionary_values(self, items, template, consume, result, no_gc):
        if not template.tracked_copies:
            self.asm.emit(b"\x45\x31\xd2", "xor r10d, r10d  # value GC flags")
        transfer = consume and len(set(items.values())) == len(items)
        for value, offset in zip(items.values(), template.value_offsets, strict=True):
            self.load(7, value)
            if not transfer:
                self.incref_rdi()
            self.asm.emit(b"\x48\x89\xbe" + struct.pack("<i", offset), f"mov [rsi+{offset}], rdi  # dictionary value")
            if not template.tracked_copies:
                self.asm.emit(b"\x48\x8b\x47" + bytes([self.layout.object_type]), "mov rax, [rdi+8]  # value type")
                self.asm.emit(
                    b"\x4c\x0b\x90" + struct.pack("<i", self.layout.type_flags),
                    "or r10, [rax+168]  # value type flags",
                )
            if transfer:
                self.asm.clear(value)
        if not template.tracked_copies:
            self.asm.emit(b"\x41\xf7\xc2\x00\x40\x00\x00", "test r10d, 0x4000  # GC-capable values")
            self.asm.jump(no_gc, "z")
            tracked = self.call_c("PyObject_GC_IsTracked", result, result="pointer")
            self.branch_if_null(tracked, no_gc, invert=True)
            self.call_c("PyObject_GC_Track", result, result="void")
        self.asm.label(no_gc)
        if consume and not transfer:
            for value in dict.fromkeys(items.values()):
                self.release(value, nonnull=True, retained=True)

    def check_shared_keys(self, template, generic):
        # Existing shared-key indices never move, and their total capacity can
        # only shrink. The template retains the original type's key table so
        # its address cannot be freed and reused after a source-dict mutation.
        self.load(0, self.constant(template.data))
        self.asm.emit(b"\x48\x8b\x50" + bytes([self.layout.dict_keys]), "mov rdx, [rax+32]  # shared keys")
        self.asm.mov_imm(9, template.keys_pointer)
        self.asm.emit(b"\x4c\x39\xca", "cmp rdx, r9  # original retained key table")
        self.asm.jump(generic, "nz")

    def new_shared_dict(self, items, template, consume):  # noqa: C901
        """Use CPython's dict freelist and allocate only the compact value buffer.

        CPython 3.14/3.15 PyDict_New always tracks its empty result. No Python calls
        occur between validating the template and publishing initialized values.
        Keys remain shared; the dict owns the PyMem buffer and transferred refs.
        """
        result = self.call_c("PyDict_New")
        capacity = template.capacity
        size = self.layout.values_items + capacity * 8 + (capacity + 7) // 8 * 8
        buffer = self.call_c("PyMem_Malloc", Immediate(size), result="pointer")
        no_memory, generic, done = (
            self.label(prefix) for prefix in ("dict_values_no_memory", "shared_dict_changed", "shared_dict_done")
        )
        self.branch_if_null(buffer, no_memory)
        self.check_shared_keys(template, generic)
        self.asm.load(6, buffer)
        self.asm.emit(
            b"\x48\xc7\x06" + struct.pack("<I", capacity | len(items) << 8),
            f"mov QWORD PTR [rsi], {capacity | len(items) << 8}  # capacity, size, nonembedded",
        )
        self.asm.emit(b"\x45\x31\xd2", "xor r10d, r10d  # unused values and consumed slots")
        used = set(template.value_offsets)
        for index in range(capacity):
            if index * 8 not in used:
                offset = self.layout.values_items + index * 8
                self.asm.emit(b"\x4c\x89\x96" + struct.pack("<i", offset), f"mov [rsi+{offset}], r10")
        transfer = consume and len(set(items.values())) == len(items)
        for value, offset in zip(items.values(), template.value_offsets, strict=True):
            self.load(7, value)
            if not transfer:
                self.incref_rdi()
            self.asm.emit(
                b"\x48\x89\xbe" + struct.pack("<i", offset + self.layout.values_items), f"mov [rsi+{offset + 8}], rdi",
            )
            if transfer:
                self.asm.store(value, 10, clear=True)
        order = bytes(offset // 8 for offset in template.value_offsets)
        for start in range(0, len(order), 8):
            self.asm.mov_imm(11, int.from_bytes(order[start:start + 8].ljust(8, b"\x00"), "little"))
            offset = self.layout.values_items + capacity * 8 + start
            self.asm.emit(b"\x4c\x89\x9e" + struct.pack("<i", offset), f"mov [rsi+{offset}], r11  # insertion order")
        self.asm.emit_memory(b"\x48\xff", 0x02, self.layout.keys_refcount, "own shared keys")
        self.asm.load(0, result)
        self.asm.emit((
                          b"\x48\x89\x50"
                          + bytes([self.layout.dict_keys])
                          + b"\x48\x89\x70"
                          + bytes([self.layout.dict_values])
                      ), "mov [rax+32], rdx; mov [rax+40], rsi")
        self.asm.emit(
            b"\x48\xc7\x40" + bytes([self.layout.dict_used]) + struct.pack("<I", len(items)),
            f"mov QWORD PTR [rax+16], {len(items)}",
        )
        if consume and not transfer:
            for value in dict.fromkeys(items.values()):
                self.release(value, nonnull=True, retained=True)
        self.asm.jump(done)
        self.asm.label(generic)
        self.call_c("PyMem_Free", buffer, result="void")
        self.release(result)
        rebuilt = self.make_dict_from_items(items)
        self.transfer(rebuilt, result)
        if consume:
            for value in dict.fromkeys(items.values()):
                self.release(value, nonnull=True, retained=True)
        self.asm.jump(done)
        self.asm.label(no_memory)
        self.call_c("PyErr_NoMemory")
        self.asm.jump(self.call_error_label)
        self.asm.label(done)
        return result

    def copy_reference(self, value: Slot | Immediate) -> Slot:
        self.call_c("Py_IncRef", value, result="void")
        result = self.slot(owned=True)
        self.load(0, value)
        self.asm.store(result)
        return result

    def copy_loaded_reference(self) -> Slot:
        """Retain a proven non-NULL object already in rax without spilling it."""
        if not self.has_validated_object_header:
            borrowed = self.slot()
            self.asm.store(borrowed)
            return self.copy_reference(borrowed)
        result = self.slot(owned=True)
        self.asm.emit(b"\x48\x89\xc7", "mov rdi, rax  # retain loaded object")
        self.incref_rdi(nonnull=True)
        self.asm.store(result, 7)
        return result

    def reserve_list(self, size: Slot) -> Slot:
        """Reserve exact-list capacity, publishing only initialized elements."""
        if not self.has_validated_object_header:
            return self.call_c("PyList_New", Immediate(0))
        result = self.call_c("PyList_New", size)
        self.asm.load(0, result)
        self.asm.emit(
            b"\x48\xc7\x40" + bytes([self.offset("var_size")]) + b"\x00\x00\x00\x00",
            "mov QWORD PTR [rax+16], 0  # empty reserved list",
        )
        return result

    def copy_list(self, source: Slot, *, destination: Slot | None = None) -> Slot:
        """Call the builtin list.copy implementation for a checked list."""
        if not self.has_validated_object_header:
            size = self.call_c("PyList_Size", source, result="pointer")
            return self.call_c("PyList_GetSlice", source, Immediate(0), size, destination=destination)
        empty: list[Any] = []
        method = empty.copy
        flags = ctypes.pythonapi.PyCFunction_GetFlags
        flags.argtypes, flags.restype = (ctypes.py_object,), ctypes.c_int
        address = ctypes.pythonapi.PyCFunction_GetFunction
        address.argtypes, address.restype = (ctypes.py_object,), ctypes.c_void_p
        if flags(method) == 4:  # METH_NOARGS  # noqa: PLR2004
            self.constants.append(method)
            return self.call_c(Immediate(address(method)), source, Immediate(0), destination=destination)
        size = self.slot()
        self.asm.load(0, source)
        self.asm.emit(b"\x48\x8b\x40" + bytes([self.offset("var_size")]), "load copied list length")
        self.asm.store(size)
        return self.call_c("PyList_GetSlice", source, Immediate(0), size, destination=destination)

    def list_as_tuple(self, source: Slot) -> Slot:
        if (
            not self.has_validated_object_header or sys.version_info[:2] not in {(3, 13), (3, 14), (3, 15)}
            or not hasattr(ctypes.pythonapi, "_PyTuple_FromArraySteal")
        ):
            return self.call_c("PyList_AsTuple", source)
        generic, done = self.label("shared_list_to_tuple"), self.label("list_to_tuple_done")
        result = self.slot(owned=True)
        self.asm.load(0, source)
        self.asm.emit_memory(
            b"\x48\x83", 0x38, self.offset("object_refcount"), "check private list ownership", immediate=b"\x01",
        )
        self.asm.jump(generic, "nz")
        # Detach the private array before allocation. GC cannot observe this
        # temporary list; the tuple API owns all item references on failure too.
        self.call_c("PyObject_GC_UnTrack", source, result="void")
        size, items = self.slot(), self.slot()
        self.asm.load(0, source)
        self.asm.emit(b"\x48\x8b\x48" + bytes([self.offset("var_size")]), "load transferred list length")
        self.asm.store(size, 1)
        self.asm.emit(b"\x48\x8b\x48" + bytes([self.offset("list_items")]), "load transferred list array")
        self.asm.store(items, 1)
        self.asm.emit(
            b"\x48\xc7\x40" + bytes([self.offset("var_size")]) + b"\x00\x00\x00\x00",
            "clear list ownership of transferred references",
        )
        converted = self.call_c("_PyTuple_FromArraySteal", items, size)
        self.transfer(converted, result)
        self.asm.jump(done)
        self.asm.label(generic)
        converted = self.call_c("PyList_AsTuple", source)
        self.transfer(converted, result)
        self.asm.label(done)
        return result

    def append_list(self, target: Slot, value: Slot, *, cached_target: bool = False) -> None:
        """Append an owned reference to an exact list, growing through the C API."""
        if not self.has_validated_object_header:
            self.call_c("PyList_Append", target, value, result="int")
            self.release(value, nonnull=True, retained=True)
            return
        grow, done = self.label("grow_list"), self.label("list_appended")
        if cached_target:
            self.asm.emit(b"\x4d\x3b\x7e" + bytes([self.offset("list_allocated")]), "cmp r15, [r14+32]  # capacity")
            self.asm.jump(grow, "ae")
            self.asm.emit(b"\x49\x8b\x4e" + bytes([self.offset("list_items")]), "mov rcx, [r14+24]  # output items")
            self.asm.load(11, value)
            self.asm.emit(b"\x4e\x89\x1c\xf9", "mov [rcx+r15*8], r11  # transfer element")
            self.asm.emit(b"\x49\xff\xc7", "inc r15  # written elements")
            self.asm.emit(
                b"\x4d\x89\x7e" + bytes([self.offset("var_size")]), "mov [r14+16], r15  # publish output length",
            )
        else:
            self.asm.load(7, target)
            self.asm.emit(b"\x48\x8b\x47" + bytes([self.offset("var_size")]), "mov rax, [rdi+16]  # output length")
            self.asm.emit(b"\x48\x3b\x47" + bytes([self.offset("list_allocated")]), "cmp rax, [rdi+32]  # capacity")
            self.asm.jump(grow, "ae")
            self.asm.emit(b"\x48\x8b\x4f" + bytes([self.offset("list_items")]), "mov rcx, [rdi+24]  # output items")
            self.asm.load(11, value)
            self.asm.emit(b"\x4c\x89\x1c\xc1", "mov [rcx+rax*8], r11  # transfer element")
            self.asm.emit(b"\x48\xff\x47" + bytes([self.offset("var_size")]), "inc QWORD PTR [rdi+16]")
        self.asm.clear(value)
        self.cold_handlers.append(
            partial(self.grow_list, target, value, grow, done, self.call_error_label, cached_target),
        )
        self.asm.label(done)
        self.asm.mark_clear(value)

    def grow_list(self, target, value, grow, done, error_label, cached_target):
        self.asm.label(grow)
        self.call_c("PyList_Append", target, value, result="int", error_label=error_label)
        if cached_target:
            self.asm.emit(b"\x49\xff\xc7", "inc r15  # written elements after growing")
        self.release(value, nonnull=True, retained=True)
        self.asm.jump(done)

    def vectorcall_address(
        self, callable_ptr: Slot | Immediate, args: tuple[Slot | Immediate, ...], keyword_names: tuple[str, ...],
        *, error_label: str = "error",
    ) -> Slot:
        if len(keyword_names) > len(args):
            raise ValueError("Vectorcall has more keyword names than arguments")
        # Arrays grow towards higher addresses, whereas stack slot indices grow
        # towards lower addresses. Reserve the array then populate it backwards.
        array_address = self.array(args)
        positional_count = Immediate(len(args) - len(keyword_names))
        if hasattr(ctypes.pythonapi, "PyObject_Vectorcall"):
            return self.call_c(
                "PyObject_Vectorcall", callable_ptr, array_address, positional_count,
                self.constant(keyword_names) if keyword_names else Immediate(0),
                error_label=error_label,
            )
        # Python 3.10 exposes Vectorcall and CallOneArg only as inline functions.
        # VectorcallDict is exported there and needs no keyword dict for ordinary calls.
        if not keyword_names:
            return self.call_c(
                "PyObject_VectorcallDict", callable_ptr, array_address, positional_count, Immediate(0),
                error_label=error_label,
            )
        kwargs = self.call_c("PyDict_New")
        for key, value in zip(keyword_names, args[-len(keyword_names):], strict=True):
            self.call_c("PyDict_SetItem", kwargs, self.constant(key), value, result="int")
        result = self.call_c(
            "PyObject_VectorcallDict", callable_ptr, array_address, positional_count, kwargs,
            error_label=error_label,
        )
        self.release(kwargs)
        return result

    def guarded_call(self, function: Any, args: tuple[Slot | Immediate, ...], handler: Any, *handler_args) -> Slot:
        return self.guarded(lambda label: self.call(function, *args, error_label=label), handler, handler_args)

    def fallback_result(self, result: Slot, function: Any, generic: str, done: str, *, cleanup=()) -> Slot:
        self.asm.label(generic)
        for slot in cleanup:
            self.release(slot)
        self.transfer(self.call(function, self.data), result)
        self.asm.label(done)
        return result

    def finish_lazy_state(self, state: Slot | None, function: Any, prefix: str) -> None:
        if state is not None:
            done = self.label(prefix)
            self.branch_if_null(state, done)
            self.release(self.call(function, state))
            self.asm.label(done)

    def inline_call(
        self, function: Any, data: Slot, handler=None, *handler_args, consume_data=False, borrow_data=False,
        code_budget: int | None = None,
    ) -> Slot:
        """Fuse a simple model program into its container's loop."""
        native = (
            function.__self__
            if type(function) is BuiltinFunctionType and isinstance(function.__self__, NativeCode) else None
        )
        program = native.program if native is not None else None
        if program is None and self.has_validated_object_header and self.program_resolver is not None:
            program = self.program_resolver(function)
        if native is not None and not self.can_inline(native, code_budget=code_budget):
            program = None
        if program is None:
            return self.call_mapper(function, data, handler, handler_args, borrow_data=borrow_data)
        consume_data = consume_data and getattr(program, "supports_consuming", False) and self.owns(data)
        if consume_data and data in handler_args:
            raise ValueError("A consuming mapper cannot retain its input in an error handler")
        previous_data, previous_error, previous_owned = self.data, self.call_error_label, self.local_owned
        recover, done = self.label("inline_model_error"), self.label("inline_model_ready")
        scope: list[Slot] = [data] if consume_data else []
        self.data = data
        self.local_owned = scope
        self.call_error_label = recover if handler else previous_error
        if consume_data:
            result = program.emit(self, consume=True)
        elif borrow_data and getattr(program, "supports_borrowing", False):
            result = program.emit(self, borrowed=True)
        else:
            result = program.emit(self)
        self.data, self.call_error_label, self.local_owned = previous_data, previous_error, previous_owned
        (self.owned if previous_owned is None else previous_owned).extend(
            slot for slot in scope if not consume_data or slot != data
        )
        if handler:
            self.asm.label(done)
            self.cold_handlers.append(
                lambda: self.recover(
                    result, handler, handler_args, recover, done, previous_error,
                    [slot for slot in scope if not consume_data or slot != data], replace_result=consume_data,
                ),
            )
        return result

    def can_inline(self, native: NativeCode, *, code_budget: int | None = None) -> bool:
        code = native.machine_code
        # Keep small conversions fused, but call large generated children once
        # instead of regenerating their complete bodies in every parent.
        if len(code) > MAX_INLINE_CODE_SIZE or code[8:11] != b"\x48\x81\xec":
            return False
        budget = getattr(native.program, "inline_budget", None)
        if code_budget is not None:
            budget = code_budget if budget is None else min(budget, code_budget)
        if budget is not None and len(self.asm.code) + len(code) > budget:
            return False
        stack_size = struct.unpack_from("<I", code, 11)[0]
        return self.slot_count * 8 + stack_size <= MAX_INLINE_STACK_SIZE

    def call_mapper(self, function, data, handler, handler_args, *, borrow_data):
        held = self.copy_reference(data) if borrow_data else None
        argument = held if held is not None else data
        result = (
            self.guarded_call(function, (argument,), handler, *handler_args)
            if handler else self.call(function, argument)
        )
        if held is not None:
            self.release(held)
        return result

    def guarded_c_call(
        self, name: str, args: tuple[Slot | Immediate, ...], handler: Any, *handler_args,
    ) -> Slot:
        return self.guarded(lambda label: self.call_c(name, *args, error_label=label), handler, handler_args)

    def dictionary_guard(self, data: Slot) -> Slot | None:
        if not self.has_validated_object_header or sys.version_info[:2] not in {(3, 13), (3, 14), (3, 15)}:
            return None
        from adaptix._internal.code_tools.native_access import supports_dictionary_cache  # noqa: PLC0415

        if not supports_dictionary_cache():
            return None
        result = self.slot()
        self.asm.load(0, data)
        self.asm.emit(b"\x48\x8b\x40" + bytes([self.offset("object_type")]), "mov rax, [rax+8]  # object type")
        self.load(11, self.constant(dict))
        self.asm.emit(b"\x4c\x39\xd8", "cmp rax, r11")
        self.asm.emit(b"\x0f\x94\xc0\x0f\xb6\xc0", "sete al; movzx eax, al")
        self.asm.store(result)
        return result

    def get_items(  # noqa: PLR0915
        self, data: Slot, names: tuple[str, ...], expected_types: tuple[type | tuple[type, ...] | None, ...], fallback,
    ):
        """Validate a simple dict layout once and retain a complete scalar row.

        The fallback returns owned fields or jumps to an existing model converter.
        """
        if (
            not self.has_validated_object_header or sys.version_info[:2] not in {(3, 13), (3, 14), (3, 15)}
            or not all(type(name) is str for name in names)
        ):
            return None
        from adaptix._internal.code_tools.native_access import (  # noqa: PLC0415
            DictionaryBatchCache,
            supports_dictionary_cache,
        )

        if not supports_dictionary_cache():
            return None
        batch = DictionaryBatchCache(names)
        self.constants.append(batch)
        results = [self.slot(owned=True) for _ in names]
        check, learn, generic, done = (
            self.label(prefix) for prefix in ("check_dict_row", "learn_dict_row", "generic_dict_row", "dict_row_ready")
        )
        self.asm.label(check)
        self.branch_if_type(data, dict, generic, invert=True)
        self.asm.load(7, data)
        self.asm.emit(
            b"\x48\x83\x7f" + bytes([self.offset("dict_values")]) + b"\x00",
            "cmp QWORD PTR [rdi+40], 0  # combined dictionary",
        )
        self.asm.jump(generic, "nz")
        self.asm.emit(b"\x48\x8b\x57" + bytes([self.offset("dict_keys")]), "mov rdx, [rdi+32]  # keys table")
        self.asm.emit(
            b"\x80\x7a" + bytes([self.offset("keys_kind")]) + b"\x01", "cmp BYTE PTR [rdx+10], 1  # unicode entries",
        )
        self.asm.jump(generic, "nz")
        self.ordered_dictionary_row(data, names, expected_types, results, done)
        self.asm.mov_imm(11, ctypes.addressof(batch))
        self.asm.emit(b"\x41\x83\x3b\x01", "cmp DWORD PTR [r11], 1  # published row cache")
        self.asm.jump(learn, "nz")
        self.asm.emit(b"\x48\x8b\x42" + bytes([self.offset("keys_nentries")]), "mov rax, [rdx+24]  # entry count")
        self.asm.emit(b"\x49\x3b\x43\x08", "cmp rax, [r11+8]  # largest learned index")
        self.asm.jump(generic, "be")
        self.asm.emit(b"\x0f\xb6\x4a" + bytes([self.offset("keys_index_bytes")]), "movzx ecx, BYTE PTR [rdx+9]")
        self.asm.emit(b"\xb8\x01\x00\x00\x00\x48\xd3\xe0", "mov eax, 1; shl rax, cl")
        self.asm.emit(
            b"\x48\x8d\x54\x02" + bytes([self.offset("keys_indices")]), "lea rdx, [rdx+rax+32]  # unicode entries",
        )
        self.asm.emit(b"\x4d\x8b\x43\x10\x4d\x8b\x4b\x18", "mov r8, [r11+16]; mov r9, [r11+24]")
        for index, (name, expected) in enumerate(zip(names, expected_types, strict=True)):
            self.asm.emit(b"\x49\x8b\x88" + struct.pack("<i", index * 8), f"mov rcx, [r8+{index * 8}]")
            self.asm.emit(
                b"\x48\xc1\xe1" + bytes([self.offset("unicode_entry_size").bit_length() - 1]) + b"\x48\x8d\x34\x0a",
                "scale Unicode entry index; lea rsi, [rdx+rcx]",
            )
            self.asm.emit(b"\x48\x8b\x06", "mov rax, [rsi]  # field key")
            self.asm.test_jump(0, generic)
            matched = self.label("row_key_matched")
            self.asm.emit(b"\x49\x3b\x81" + struct.pack("<i", index * 8), f"cmp rax, [r9+{index * 8}]")
            self.asm.jump(matched, "z")
            self.match_ascii_key(name, generic)
            self.asm.label(matched)
            self.asm.emit(
                b"\x48\x8b\x46" + bytes([self.offset("unicode_entry_value")]), "mov rax, [rsi+8]  # field value",
            )
            # A combined entry with a verified live key owns a non-NULL value.
            # No calls or GIL release occur between the key and value loads.
            if expected is not None:
                self.check_dictionary_scalar(expected, generic)
            self.asm.emit(b"\x48\x89\xc7", "mov rdi, rax  # retain checked field")
            self.incref_rdi(nonnull=True)
            self.asm.store(results[index], 7)
        self.asm.jump(done)
        self.asm.label(learn)
        self.learning_budget(batch, 4, generic)
        self.release(self.call(batch, data))
        self.asm.jump(check)
        self.asm.label(generic)
        # A later guard may fail after earlier fields were retained. The
        # source dict still owns them: validation and retention call no Python.
        for value in results:
            self.release(value, retained=True)
        values = fallback()
        if values is not None:
            for value, target in zip(values, results, strict=True):
                self.transfer(value, target)
        self.asm.label(done)
        return results

    def ordered_dictionary_row(self, data, names, expected_types, results, done):
        return emit_ordered_dictionary_row(self, data, names, expected_types, results, done)

    def ordered_key_compare(self, name, offset, compare, matched, failed):
        return emit_ordered_key_compare(self, name, offset, compare, matched, failed)

    def check_dictionary_scalar(self, expected: type | tuple[type, ...], failed: str) -> None:
        types = expected if isinstance(expected, tuple) else (expected,)
        matched = self.label("row_scalar_matched")
        for index, cls in enumerate(types):
            self.load(11, self.constant(cls))
            self.asm.emit_memory(b"\x4c\x39", 0x58, self.offset("object_type"), "check exact scalar type")
            self.asm.jump(failed if index == len(types) - 1 else matched, "nz" if index == len(types) - 1 else "z")
        self.asm.label(matched)

    def match_ascii_key(self, name: str, failed: str, *, source: Literal[0, 1] = 0):
        return emit_match_ascii_key(self, name, failed, source=source)

    def get_item(self, data: Slot, key: Any, exact_dict: Slot | None, *, error_label: str = "error") -> Slot:
        if exact_dict is None or type(key) is not str:
            return self.call_c("PyObject_GetItem", data, self.constant(key), error_label=error_label)
        from adaptix._internal.code_tools.native_access import DictionaryCache  # noqa: PLC0415

        item_cache = DictionaryCache(key)
        self.constants.append(item_cache)
        result = self.slot(owned=True)
        generic, learn, compare, direct, done = (
            self.label("generic_item"), self.label("learn_item"), self.label("compare_item_key"),
            self.label("direct_item"), self.label("item_ready"),
        )
        self.branch_if_null(exact_dict, generic)
        self.asm.load(7, data)
        self.asm.emit(
            b"\x48\x83\x7f" + bytes([self.offset("dict_values")]) + b"\x00",
            "cmp QWORD PTR [rdi+40], 0  # combined dictionary",
        )
        self.asm.jump(generic, "nz")
        self.asm.emit(b"\x48\x8b\x47" + bytes([self.offset("dict_keys")]), "mov rax, [rdi+32]  # ma_keys")
        self.asm.emit(
            b"\x80\x78" + bytes([self.offset("keys_kind")]) + b"\x01", "cmp BYTE PTR [rax+10], 1  # unicode keys",
        )
        self.asm.jump(generic, "nz")
        self.asm.mov_imm(11, ctypes.addressof(item_cache))
        self.asm.emit(b"\x41\x83\x7b\x10\x01", "cmp DWORD PTR [r11+16], 1  # published cache")
        self.asm.jump(learn, "nz")
        self.asm.emit(b"\x4d\x8b\x43\x08", "mov r8, [r11+8]  # cached entry index")
        self.asm.emit(b"\x4c\x3b\x40" + bytes([self.offset("keys_nentries")]), "cmp r8, [rax+24]  # dk_nentries")
        self.asm.jump(learn, "ae")
        self.asm.emit(
            b"\x0f\xb6\x48" + bytes([self.offset("keys_index_bytes")]),
            "movzx ecx, BYTE PTR [rax+9]  # index byte count exponent",
        )
        self.asm.emit(b"\xba\x01\x00\x00\x00\x48\xd3\xe2", "mov edx, 1; shl rdx, cl")
        self.asm.emit(b"\x48\x8d\x54\x10" + bytes([self.offset("keys_indices")]), "lea rdx, [rax+rdx+32]  # entries")
        self.asm.emit(
            b"\x49\xc1\xe0" + bytes([self.offset("unicode_entry_size").bit_length() - 1]) + b"\x4c\x01\xc2",
            "scale Unicode entry index; add rdx, r8",
        )
        self.asm.emit(b"\x48\x8b\x0a\x49\x3b\x0b", "mov rcx, [rdx]; cmp rcx, [r11]  # cached key identity")
        self.asm.jump(compare, "nz")
        self.asm.label(direct)
        self.asm.emit(
            b"\x48\x8b\x42" + bytes([self.offset("unicode_entry_value")]) + b"\x48\x85\xc0",
            "mov rax, [rdx+8]; test rax, rax",
        )
        self.asm.jump(learn, "z")
        self.asm.store(result)
        self.asm.emit(b"\x48\x89\xc7", "mov rdi, rax")
        self.incref_rdi()
        self.asm.label(done)
        self.cold_handlers.append(
            lambda: self.item_fallback(
                data, key, item_cache, result, generic, learn, compare, direct, done, error_label,
            ),
        )
        return result

    def guarded_get_item(self, data: Slot, key: Any, exact_dict: Slot | None, handler: Any, *handler_args) -> Slot:
        return self.guarded(
            lambda label: self.get_item(data, key, exact_dict, error_label=label), handler, handler_args,
        )

    def item_fallback(self, data, key, item_cache, result, generic, learn, compare, direct, done, error_label) -> None:
        self.asm.label(compare)
        self.compare_ascii_key(key, learn, direct)
        self.local_owned = []
        self.asm.label(generic)
        value = self.call_c("PyObject_GetItem", data, self.constant(key), error_label=error_label)
        self.transfer(value, result)
        self.asm.jump(done)
        self.asm.label(learn)
        self.learning_budget(item_cache, 20, generic)
        value = self.call(item_cache, data, error_label=error_label)
        self.transfer(value, result)
        self.asm.jump(done)
        self.local_owned = None

    def compare_ascii_key(self, key: str, failed: str, direct: str) -> None:
        # rcx holds the key, rdx its dictionary entry. Keep both reads under the GIL.
        if not key.isascii() or len(key) > 32:  # noqa: PLR2004
            self.asm.jump(failed)
            return
        self.asm.test_jump(1, failed)
        self.match_ascii_key(key, failed, source=1)
        self.asm.jump(direct)

    def learning_budget(self, storage: Any, offset: int, generic: str) -> None:
        from adaptix._internal.code_tools.native_access import SPECIALIZATION_LIMIT  # noqa: PLC0415

        # A polymorphic workload or frequently changing layout must not pay
        # for Python training on every call. Keep the last valid cache entry,
        # and use the ordinary C getter on subsequent cache misses.
        self.asm.mov_imm(11, ctypes.addressof(storage))
        self.asm.emit(
            b"\x41\x83\x7b" + bytes([offset, SPECIALIZATION_LIMIT]),
            f"cmp DWORD PTR [r11+{offset}], {SPECIALIZATION_LIMIT}",
        )
        self.asm.jump(generic, "ae")

    def check_cached_type(self, miss: str) -> None:
        """Compare the class in rax with the type/version cache at r11."""
        self.asm.emit(b"\x49\x3b\x03", "cmp rax, [r11]  # cached type")
        self.asm.jump(miss, "nz")
        self.asm.emit(
            b"\x8b\x88" + struct.pack("<i", self.offset("type_version")), "mov ecx, [rax+384]  # type version",
        )
        self.asm.emit(b"\x41\x3b\x4b\x08", "cmp ecx, [r11+8]")
        self.asm.jump(miss, "nz")

    def get_attr(self, data: Slot | Immediate, name: str, *, error_label: str = "error") -> Slot:
        if (
            not self.has_validated_object_header
            or sys.version_info[:2] not in {(3, 13), (3, 14), (3, 15)}
            or type(name) is not str
        ):
            return self.call_c("PyObject_GetAttr", data, self.constant(name), error_label=error_label)
        from adaptix._internal.code_tools.native_access import AttributeCache, supports_attribute_cache  # noqa: PLC0415

        if not supports_attribute_cache():
            return self.call_c("PyObject_GetAttr", data, self.constant(name), error_label=error_label)
        attribute_cache = AttributeCache(name)
        self.constants.append(attribute_cache)
        result = self.slot(owned=True)
        generic, learn, direct, done = (
            self.label("generic_attribute"), self.label("learn_attribute"),
            self.label("direct_attribute"), self.label("attribute_ready"),
        )
        self.load(7, data)
        self.asm.mov_imm(11, ctypes.addressof(attribute_cache))
        self.asm.emit(b"\x48\x8b\x47" + bytes([self.offset("object_type")]), "mov rax, [rdi+8]  # object type")
        self.check_cached_type(learn)
        self.asm.emit(b"\x41\x83\x7b\x0c\x00", "cmp DWORD PTR [r11+12], 0")
        self.asm.jump(generic, "z")
        self.asm.emit(b"\x41\x83\x7b\x0c\x01", "cmp DWORD PTR [r11+12], 1")
        self.asm.jump(direct, "nz")
        self.asm.emit(b"\x49\x8b\x4b\x18", "mov rcx, [r11+24]  # inline validity offset")
        self.asm.emit(b"\x80\x3c\x0f\x01", "cmp BYTE PTR [rdi+rcx], 1")
        self.asm.jump(generic, "nz")
        self.asm.label(direct)
        self.asm.emit(b"\x49\x8b\x4b\x10", "mov rcx, [r11+16]  # attribute offset")
        self.asm.emit(b"\x48\x8b\x04\x0f", "mov rax, [rdi+rcx]")
        self.asm.test_jump(0, generic)
        self.asm.store(result)
        self.asm.emit(b"\x48\x89\xc7", "mov rdi, rax")
        self.incref_rdi()
        self.asm.label(done)
        self.cold_handlers.append(
            lambda: self.attribute_fallback(data, name, attribute_cache, result, generic, learn, done, error_label),
        )
        return result

    def guarded_get_attr(self, data: Slot, name: str, handler: Any, *handler_args) -> Slot:
        return self.guarded(lambda label: self.get_attr(data, name, error_label=label), handler, handler_args)

    def get_attrs(  # noqa: PLR0915
        self, data: Slot, names: tuple[str, ...], handlers: tuple[Any, ...] = (), *handler_args,
    ) -> list[Slot]:
        """Read a run of plain attributes after one storage/type guard."""
        def read_individually():
            for index, name in enumerate(names):
                yield (
                    self.guarded_get_attr(data, name, handlers[index], *handler_args)
                    if handlers else self.get_attr(data, name)
                )

        supported = False
        if self.has_validated_object_header and sys.version_info[:2] in {(3, 13), (3, 14), (3, 15)}:
            from adaptix._internal.code_tools.native_access import (  # noqa: PLC0415
                AttributeBatchCache,
                supports_attribute_cache,
            )

            supported = supports_attribute_cache()
        if not supported:
            return list(read_individually())
        batch = AttributeBatchCache(names)
        self.constants.append(batch)
        check, learn, generic, direct, done = (
            self.label(prefix)
            for prefix in ("check_attrs", "learn_attrs", "generic_attrs", "direct_attrs", "attrs_ready")
        )
        results = [self.slot(owned=True) for _ in names]
        self.asm.label(check)
        self.asm.load(7, data)
        self.asm.emit(b"\x48\x8b\x47" + bytes([self.offset("object_type")]), "mov rax, [rdi+8]  # model type")
        self.asm.mov_imm(11, ctypes.addressof(batch))
        self.check_cached_type(learn)
        self.asm.emit(b"\x41\x83\x7b\x0c\x00", "cmp DWORD PTR [r11+12], 0  # storage kind")
        self.asm.jump(learn, "z")
        dictionary = self.label("dictionary_attrs")
        self.asm.emit(b"\x41\x83\x7b\x0c\x03", "cmp DWORD PTR [r11+12], 3  # dictionary storage")
        self.asm.jump(dictionary, "z")
        self.asm.emit(b"\x41\x83\x7b\x0c\x01", "cmp DWORD PTR [r11+12], 1  # inline storage")
        self.asm.jump(direct, "nz")
        self.asm.emit(b"\x49\x8b\x4b\x10", "mov rcx, [r11+16]  # inline validity offset")
        self.asm.emit(b"\x80\x3c\x0f\x01", "cmp BYTE PTR [rdi+rcx], 1")
        self.asm.jump(generic, "nz")
        self.asm.label(direct)
        self.asm.emit(b"\x49\x8b\x53\x18", "mov rdx, [r11+24]  # attribute offsets")
        self.asm.emit(b"\x49\x89\xf8", "mov r8, rdi  # source instance")
        for index, value in enumerate(results):
            self.asm.emit(b"\x48\x8b\x8a" + struct.pack("<i", index * 8), f"mov rcx, [rdx+{index * 8}]")
            self.asm.emit(b"\x49\x8b\x04\x08", "mov rax, [r8+rcx]")
            self.asm.test_jump(0, generic)
            self.asm.emit(b"\x48\x89\xc7", "mov rdi, rax  # retain checked field")
            self.incref_rdi(nonnull=True)
            self.asm.store(value, 7)
        self.asm.jump(done)
        self.asm.label(dictionary)
        namespace = self.call_c("PyObject_GenericGetDict", data, Immediate(0))
        values = self.get_items(namespace, names, (None,) * len(names), lambda: list(read_individually()))
        for value, target in zip(values, results, strict=True):
            self.transfer(value, target)
        self.release(namespace)
        self.asm.jump(done)
        self.asm.label(learn)
        self.learning_budget(batch, 32, generic)
        self.release(self.call(batch, data))
        self.asm.jump(check)
        self.asm.label(generic)
        for value in results:
            self.release(value, retained=True)
        for value, target in zip(read_individually(), results, strict=True):
            self.transfer(value, target)
        self.asm.label(done)
        return results

    def attribute_fallback(self, data, name, attribute_cache, result, generic, learn, done, error_label) -> None:
        # Each call writes its only local owned slot before checking failure,
        # and transfers it on success. No local reference survives an exit.
        self.local_owned = []
        self.asm.label(generic)
        value = self.call_c("PyObject_GetAttr", data, self.constant(name), error_label=error_label)
        self.transfer(value, result)
        self.asm.jump(done)
        self.asm.label(learn)
        self.learning_budget(attribute_cache, 32, generic)
        value = self.call(attribute_cache, data, error_label=error_label)
        self.transfer(value, result)
        self.asm.jump(done)
        self.local_owned = None

    def guarded(self, emit_call: Callable[[str], Slot], handler: Any, handler_args: tuple) -> Slot:
        """Call directly on success; transfer a normalized exception on failure."""
        recover, done = self.label("recover"), self.label("recovered")
        error_target = self.call_error_label
        result = emit_call(recover)
        self.asm.label(done)
        self.cold_handlers.append(lambda: self.recover(result, handler, handler_args, recover, done, error_target))
        return result

    def recover(
        self, result: Slot, handler: Any, handler_args: tuple, recover: str, done: str,
        error_target: str, cleanup_slots: list[Slot] | None = None, *, replace_result: bool = False,
    ) -> None:
        outer = self.asm
        self.asm = self.assembler_factory()
        self.local_owned = []
        self.call_error_label = self.label("recovery_failed")
        exc_type, exc_value, exc_tb = (self.slot(owned=True) for _ in range(3))
        self.call_c("PyErr_Fetch", Address(exc_type), Address(exc_value), Address(exc_tb), result="void")
        if cleanup_slots:
            self.cleanup(cleanup_slots)
        self.call_c("PyErr_NormalizeException", Address(exc_type), Address(exc_value), Address(exc_tb), result="void")
        has_traceback = self.label("traceback")
        self.asm.load(0, exc_tb)
        self.asm.test_jump(0, has_traceback, "nz")
        none = self.constant(None)
        self.call_c("Py_IncRef", none, result="void")
        self.load(0, none)
        self.asm.store(exc_tb)
        self.asm.label(has_traceback)
        self.call_c("PyException_SetTraceback", exc_value, exc_tb, result="int")
        for argument in handler_args:
            if isinstance(argument, Slot) and argument in self.lazy:
                self.initialize_lazy(argument)
        replacement = self.call(handler, *handler_args, exc_value)
        if replace_result:
            self.release(result, nonnull=True)
        self.asm.load(0, replacement)
        self.asm.store(result)
        self.asm.clear(replacement)
        for argument in handler_args:
            if isinstance(argument, Slot) and argument in self.lazy and self.lazy[argument][2]:
                self.release(argument)
        for exception_slot in (exc_tb, exc_value, exc_type):
            self.release(exception_slot)
        self.cleanup(self.local_owned)
        self.asm.jump(done)
        self.asm.label(self.call_error_label)
        saved_type, saved_value, saved_tb = self.slot(), self.slot(), self.slot()
        self.call_c("PyErr_Fetch", Address(saved_type), Address(saved_value), Address(saved_tb), result="void")
        self.cleanup(self.local_owned)
        self.call_c("PyErr_Restore", saved_type, saved_value, saved_tb, result="void")
        self.asm.jump(error_target)
        body = self.asm
        self.asm = outer
        self.asm.label(recover)
        self.asm.emit(b"\x31\xc0", "xor eax, eax")
        for slot in self.local_owned:
            self.asm.store(slot, clear=True)
        self.asm.extend(body)
        self.local_owned = None
        self.call_error_label = "error"

    def branch_if(self, value: Slot, constant: Any, label: str, *, invert: bool = False) -> None:
        self.branch_if_same(value, self.constant(constant), label, invert=invert)

    def branch_if_same(self, value: Slot, expected: Slot | Immediate, label: str, *, invert: bool = False) -> None:
        self.asm.load(0, value)
        self.load(11, expected)
        self.asm.emit(b"\x4c\x39\xd8", "cmp rax, r11")
        self.asm.jump(label, "nz" if invert else "z")

    def known_list_item(self, data: Slot, index: int) -> Slot:
        """Borrow an item from a proven exact list containing the given index."""
        if index < 0:
            raise ValueError("A known list index must be nonnegative")
        if self.layout is None:
            result = self.call_c("PyList_GetItem", data, Immediate(index), result="pointer")
            self.branch_if_null(result, self.call_error_label)
            return result
        self.load(0, data)
        self.asm.emit_memory(b"\x48\x8b", 0x00, self.layout.list_items, "load list item array")
        self.asm.emit_memory(b"\x48\x8b", 0x00, index * 8, f"load known list item {index}")
        result = self.slot()
        self.asm.store(result)
        return result

    def branch_if_type(self, value: Slot, expected: type, label: str, *, invert: bool = False) -> None:
        """Compare an exact type using the validated CPython object header."""
        if self.refcount_mode is None:
            raise ValueError("The CPython object header has not been validated")
        self.asm.load(0, value)
        self.asm.emit(b"\x48\x8b\x40" + bytes([self.offset("object_type")]), "mov rax, [rax+8]  # ob_type")
        self.load(11, self.constant(expected))
        self.asm.emit(b"\x4c\x39\xd8", "cmp rax, r11")
        self.asm.jump(label, "nz" if invert else "z")

    @property
    def has_validated_object_header(self) -> bool:
        return self.refcount_mode is not None

    def branch_if_null(self, value: Slot | Immediate, label: str, *, invert: bool = False) -> None:
        if isinstance(value, Slot):
            self.asm.load(0, value)
        else:
            self.asm.mov_imm(0, value.value)
        self.asm.test_jump(0, label, "nz" if invert else "z")

    def transfer(self, source: Slot, destination: Slot) -> None:
        if not self.owns(source) or not self.owns(destination) or source == destination:
            raise ValueError("Ownership transfers require two distinct owned slots")
        self.asm.load(0, source)
        self.asm.store(destination)
        self.asm.clear(source)

    def replace_reference(self, source: Slot, destination: Slot) -> None:
        """Move an owned result over a non-NULL owned input before releasing it."""
        if not self.owns(source) or not self.owns(destination) or source == destination:
            raise ValueError("Reference replacement requires two distinct owned slots")
        self.asm.load(7, destination)
        self.asm.load(0, source)
        self.asm.store(destination)
        self.asm.clear(source)
        self.decref_rdi()

    def new_reference(self, value: Any) -> Slot:
        pointer = self.constant(value)
        self.call_c("Py_IncRef", pointer, result="void")
        result = self.slot(owned=True)
        self.load(0, pointer)
        self.asm.store(result)
        return result

    def dict_lookup(self, mapping: Slot, key: Any, default: Any) -> Slot:
        """Get a new reference from an exact dict, distinguishing absence from errors."""
        if (
            self.has_validated_object_header and sys.version_info[:2] in {(3, 13), (3, 14), (3, 15)}
            and type(key) is str and key.isascii() and len(key) <= 32  # noqa: PLR2004
        ):
            from adaptix._internal.code_tools.native_access import supports_dictionary_cache  # noqa: PLC0415

            if supports_dictionary_cache():
                result = self.slot(owned=True)
                generic, missing, done = (
                    self.label(prefix) for prefix in ("generic_lookup", "absent_lookup", "lookup_ready")
                )
                self.probe_dictionary(mapping, key, missing, generic)
                self.incref_rdi(nonnull=True)
                self.asm.store(result, 7)
                self.asm.jump(done)
                self.asm.label(missing)
                self.load(7, self.constant(default))
                self.incref_rdi(nonnull=True)
                self.asm.store(result, 7)
                self.asm.jump(done)
                self.asm.label(generic)
                self.transfer(self.generic_dict_lookup(mapping, key, default), result)
                self.asm.label(done)
                return result
        return self.generic_dict_lookup(mapping, key, default)

    def probe_dictionary(self, mapping: Slot, key: str, missing: str, generic: str) -> None:
        return emit_probe_dictionary(self, mapping, key, missing, generic)

    def generic_dict_lookup(self, mapping: Slot, key: Any, default: Any) -> Slot:
        value = self.call_c("PyDict_GetItemWithError", mapping, self.constant(key), result="pointer")
        result = self.slot(owned=True)
        missing, done = self.label("missing_key"), self.label("lookup_done")
        self.asm.load(0, value)
        self.asm.test_jump(0, missing)
        self.call_c("Py_IncRef", value, result="void")
        self.asm.load(0, value)
        self.asm.store(result)
        self.asm.jump(done)
        self.asm.label(missing)
        self.call_c("PyErr_Occurred", result="pointer")
        self.asm.test_jump(0, self.call_error_label, "nz")
        replacement = self.new_reference(default)
        self.transfer(replacement, result)
        self.asm.label(done)
        return result

    def release(self, slot: Slot, *, nonnull: bool = False, retained: bool = False) -> None:
        """Drop an owned reference, optionally using proven lifetime facts.

        retained means another owner keeps the object alive through this drop.
        nonnull means every incoming path initialized the slot successfully.
        """
        if not self.owns(slot):
            raise ValueError("Cannot release a borrowed native slot")
        skip = self.label("released")
        if not nonnull:
            self.asm.load(0, slot)
            self.asm.test_jump(0, skip)
        self.asm.load(7, slot)
        self.asm.clear(slot)
        self.decref_rdi(retained=retained)
        self.asm.label(skip)
        self.asm.mark_clear(slot)

    def cleanup(self, slots: list[Slot] | None = None) -> None:
        for slot in reversed(self.owned if slots is None else slots):
            self.release(slot)

    def decref_rdi(self, *, retained: bool = False) -> None:
        if self.refcount_mode is not None:
            done, destroy = self.label("decref_done"), self.label("destroy_object")
            if self.refcount_mode != "legacy":
                self.asm.emit_memory(b"\x8b", 0x07, self.offset("object_refcount"), "load reference count")
                self.asm.emit(b"\x85\xc0", "test eax, eax")
                self.asm.jump(done, "s")
            prefix = b"" if self.refcount_mode == "immortal32" else b"\x48"
            width = "DWORD" if self.refcount_mode == "immortal32" else "QWORD"
            if not retained and self.dealloc_address is None:
                self.asm.emit_memory(
                    prefix + b"\x83",
                    0x3F,
                    self.offset("object_refcount"),
                    f"cmp {width} reference count, 1",
                    immediate=b"\x01",
                )
                self.asm.jump(destroy, "z")
            self.asm.emit_memory(
                prefix + b"\x83",
                0x2F,
                self.offset("object_refcount"),
                f"sub {width} reference count, 1",
                immediate=b"\x01",
            )
            if not retained:
                if self.dealloc_address is None:
                    self.asm.jump(done)
                    self.asm.label(destroy)
                    self.call_decref_rdi()
                else:
                    # Match CPython's Py_DECREF: the subtract supplies the
                    # zero test, and _Py_Dealloc sees the final count of zero.
                    self.asm.jump(done, "nz")
                    self.asm.mov_imm(11, self.dealloc_address)
                    self.asm.emit(b"\x41\xff\xd3", "call r11  # _Py_Dealloc")
            self.asm.label(done)
        else:
            self.call_decref_rdi()

    def incref_rdi(self, *, nonnull: bool = False) -> None:
        done = self.label("incref_done")
        if not nonnull:
            self.asm.test_jump(7, done)
        if self.refcount_mode == "legacy":
            self.asm.emit_memory(b"\x48\xff", 0x07, self.offset("object_refcount"), "increment reference count")
        else:
            self.asm.emit_memory(b"\x8b", 0x07, self.offset("object_refcount"), "load reference count")
            limit = 0xC0000000 if self.refcount_mode == "immortal32" else 0xFFFFFFFF
            self.asm.emit(b"\x3d" + struct.pack("<I", limit), f"cmp eax, 0x{limit:x}")
            self.asm.jump(done, "ae")
            self.asm.emit_memory(b"\xff", 0x07, self.offset("object_refcount"), "increment reference count")
        self.asm.label(done)

    def call_decref_rdi(self) -> None:
        address = ctypes.cast(ctypes.pythonapi.Py_DecRef, ctypes.c_void_p).value
        if address is None:
            raise RuntimeError("Missing CPython C API entry point: Py_DecRef")
        self.asm.mov_imm(11, address)
        self.asm.emit(b"\x41\xff\xd3", "call r11  # Py_DecRef")

    def finish(self, result: Slot, *, program=None) -> NativeCode:
        if result not in self.owned:
            raise ValueError("A native function must return an owned reference")
        main = self.asm
        self.asm = self.assembler_factory()
        for handler in self.cold_handlers:
            handler()
        cold = self.asm
        self.asm = main
        successful_exit = self.label("successful_exit")
        self.asm.label(successful_exit)
        flow = self.assembler_factory()
        flow.extend(main)
        flow.jump(self.label("flow_stop"))
        flow.extend(cold)
        cleared = flow.definitely_null_at(successful_exit, self.owned)
        live = [slot for slot in self.owned if slot != result and slot not in cleared]
        if live:
            self.return_with_cleanup(result, live)
        else:
            self.asm.load(0, result)
            self.emit_return()

        self.asm.label("error")
        exc_type, exc_value, exc_tb = self.slot(), self.slot(), self.slot()
        self.call_c("PyErr_Fetch", Address(exc_type), Address(exc_value), Address(exc_tb), result="void")
        self.cleanup()
        self.call_c("PyErr_Restore", exc_type, exc_value, exc_tb, result="void")
        self.asm.emit(b"\x31\xc0", "xor eax, eax")
        self.emit_return()
        self.asm.extend(cold)

        return self.make_code(program)

    def return_with_cleanup(self, result: Slot, live: list[Slot]) -> None:
        returned = self.slot()
        self.asm.load(0, result)
        self.asm.store(returned)
        self.asm.clear(result)
        self.cleanup(live)
        self.asm.load(0, returned)
        self.emit_return()

    def emit_return(self) -> None:
        for register, slot in self.saved_registers.items():
            self.asm.load(register, slot)
        self.asm.emit(b"\xc9\xc3", "leave; ret")

    def make_code(self, program=None) -> NativeCode:
        self.insert_function_context()
        stack_size = (self.slot_count * 8 + 15) // 16 * 16
        if stack_size > MAX_STACK_SIZE:  # avoid an unbounded native stack frame
            raise ValueError("Model requires more than 64 KiB of native stack space")
        prefix = self.assembler_factory()
        prefix.emit(b"\xf3\x0f\x1e\xfa", "endbr64")
        prefix.emit(b"\x55\x48\x89\xe5", "push rbp; mov rbp, rsp")
        prefix.emit(b"\x48\x81\xec" + struct.pack("<I", stack_size), f"sub rsp, {stack_size}")
        for register, slot in self.saved_registers.items():
            prefix.store(slot, register)
        prefix.emit(b"\x31\xc0", "xor eax, eax")
        for slot in self.owned:
            prefix.store(slot, clear=True)
        prefix_code = prefix.finish()
        code = prefix_code + self.asm.finish()
        raw_entry_offset = len(code) if self.bound_context is None else -1
        unary = self.assembler_factory()
        unary.code.extend(prefix_code)
        unary.lines.extend(prefix.lines)
        for argument, register in zip(self.arguments, ARG_REGISTERS, strict=False):
            unary.store(argument, register)
        displacement = len(prefix_code) + self.asm.final_labels[self.argument_ready] - (
            len(code) + len(unary.code) + 5
        )
        unary.emit(b"\xe9" + struct.pack("<i", displacement), "jmp native_body")
        code += unary.finish()
        assembly = (
            ".intel_syntax noprefix\n" + self.name + ":\n"
            + "\n".join(prefix.lines + self.asm.lines)
            + ("\nnative_unary_entry:\n" if len(self.arguments) == 1 else "\nnative_arguments_entry:\n")
            + "\n".join(unary.lines) + "\n"
        )
        return NativeCode(
            name=self.name, code=code, assembly=assembly, constants=self.constants, raw_entry_offset=raw_entry_offset,
            program=program,
            parameters=self.parameters, defaults=self.defaults,
        )

    def insert_function_context(self) -> None:
        if not self.context_pointers:
            return
        context = self.assembler_factory()
        for name, target in self.context_pointers.items():
            api = ctypes.cast(getattr(ctypes.pythonapi, name), ctypes.c_void_p).value
            if api is None:
                raise RuntimeError(f"Missing context getter: {name}")
            context.mov_imm(11, api)
            context.emit(b"\x31\xc0\x41\xff\xd3", f"xor eax, eax; call r11  # {name}, once per call")
            context.store(target)
        offset, size = self.body_offset, len(context.code)
        self.asm.code[offset:offset] = context.code
        self.asm.labels = {
            label: position + size if position >= offset and label != self.argument_ready else position
            for label, position in self.asm.labels.items()
        }
        self.asm.fixups = [(position + size if position >= offset else position, label)
                            for position, label in self.asm.fixups]
        line = self.asm.lines.index(self.argument_ready + ":") + 1
        self.asm.lines[line:line] = context.lines
        event = self.asm.flow.index(("label", self.argument_ready)) + 1
        self.asm.flow[event:event] = context.flow
