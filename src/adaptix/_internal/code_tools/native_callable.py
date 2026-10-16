import ctypes
import mmap
from functools import cache
from types import BuiltinFunctionType
from typing import Any, NamedTuple, cast


@cache
def native_function_factory() -> Any:
    factory = ctypes.pythonapi.PyCFunction_NewEx
    factory.argtypes = (ctypes.c_void_p, ctypes.py_object, ctypes.c_void_p)
    factory.restype = ctypes.py_object
    return factory


class MethodDef(ctypes.Structure):
    _fields_ = [
        ("ml_name", ctypes.c_char_p),
        ("ml_meth", ctypes.c_void_p),
        ("ml_flags", ctypes.c_int),
        ("ml_doc", ctypes.c_char_p),
    ]


class NativeMethod(NamedTuple):
    definition: bytes
    name: bytes
    documentation: bytes


class ExecutableMemory:
    def __init__(self, code: bytes):
        size = (len(code) + mmap.PAGESIZE - 1) // mmap.PAGESIZE * mmap.PAGESIZE
        self.mapping = mmap.mmap(-1, size, prot=mmap.PROT_READ | mmap.PROT_WRITE)
        self.mapping.write(code)
        self.address = ctypes.addressof(ctypes.c_char.from_buffer(self.mapping))
        libc = ctypes.CDLL(None, use_errno=True)
        mprotect = libc.mprotect
        mprotect.argtypes = (ctypes.c_void_p, ctypes.c_size_t, ctypes.c_int)
        mprotect.restype = ctypes.c_int
        # The mapping is writable only while being populated, executable only afterwards.
        if mprotect(self.address, size, mmap.PROT_READ | mmap.PROT_EXEC) != 0:
            error = ctypes.get_errno()
            self.mapping.close()
            raise OSError(error, "Cannot make generated native code executable")


class NativeCodeData(NamedTuple):
    machine_code: bytes
    assembly: str
    constants: tuple[Any, ...]
    memory: ExecutableMemory
    method: NativeMethod
    raw_entry_offset: int
    program: Any
    parameters: tuple[str, ...]


class NativeCode(NativeCodeData):
    """Lifetime owner, held by the generated builtin's __self__.

    Constants, method metadata and executable memory must outlive the builtin.
    The tuple payload cannot be cleared by cyclic GC. In particular, method
    metadata must still exist when CPython deallocates a builtin in a recursive
    model's reference cycle and reads its flags before dropping its self object.
    Method bytes also survive GC clearing ctypes buffers elsewhere in the cycle.
    """

    __slots__ = ()

    def __new__(
        cls, *, name: str, code: bytes, assembly: str, constants: list[Any], raw_entry_offset: int, program=None,
        parameters: tuple[str, ...] = ("data",), defaults: tuple[Any, ...] = (),
    ):
        memory = ExecutableMemory(code)
        method_name = name.encode("utf-8")
        required = len(parameters) - len(defaults)
        signature = ", ".join(
            parameter if index < required else f"{parameter}={defaults[index - required]!r}"
            for index, parameter in enumerate(parameters)
        )
        documentation = (
            f"{name}($self, /{', ' if signature else ''}{signature})\n--\n\nGenerated native function."
        ).encode()
        method = NativeMethod(
            bytes(MethodDef(method_name, memory.address, 0x0080 | 0x0002, documentation)),
            method_name, documentation,
        )
        return super().__new__(
            cls, code, assembly, tuple(constants), memory, method, raw_entry_offset, program, parameters,
        )

    def bind(self, context: Any) -> Any:
        """Share executable code and method metadata with a new closure owner."""
        if self.raw_entry_offset >= 0:
            raise ValueError("This native function does not accept a bound context")
        return NativeClosure(self, context)

    @property
    def raw_address(self) -> int:
        if self.raw_entry_offset < 0:
            raise ValueError("A native closure requires its callable entry")
        return self.memory.address + self.raw_entry_offset

    def __repr__(self):
        return f"<NativeCode ({len(self.machine_code)} bytes)>"

    def make_callable(self) -> BuiltinFunctionType:
        if self.raw_entry_offset < 0:
            raise ValueError("A native closure requires a bound context")
        return cast(BuiltinFunctionType, native_function_factory()(self.method.definition, self, None))


class NativeClosure(NamedTuple):
    code: NativeCode
    bound_context: Any

    @property
    def memory(self) -> ExecutableMemory:
        return self.code.memory

    @property
    def raw_address(self) -> int:
        raise ValueError("A native closure requires its callable entry")

    def make_callable(self) -> BuiltinFunctionType:
        return cast(BuiltinFunctionType, native_function_factory()(self.code.method.definition, self, None))
