import ctypes
import mmap
import zlib
from typing import Any, NamedTuple


class MethodDef(ctypes.Structure):
    _fields_ = [
        ("ml_name", ctypes.c_char_p),
        ("ml_meth", ctypes.c_void_p),
        ("ml_flags", ctypes.c_int),
        ("ml_doc", ctypes.c_char_p),
    ]


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
    machine_code_size: int
    assembly_source: bytes
    constants: tuple[Any, ...]
    memory: ExecutableMemory
    method: MethodDef
    raw_entry_offset: int
    program: Any


class NativeCode(NativeCodeData):
    """Lifetime owner, held by the generated builtin's __self__.

    Constants, method metadata and executable memory must outlive the builtin.
    The tuple payload cannot be cleared by cyclic GC. In particular, method
    metadata must still exist when CPython deallocates a builtin in a recursive
    model's reference cycle and reads its flags before dropping its self object.
    """

    __slots__ = ()

    def __new__(
        cls, *, name: str, code: bytes, assembly: str | bytes, constants: list[Any], raw_entry_offset: int,
        program=None,
    ):
        memory = ExecutableMemory(code)
        method = MethodDef(
            name.encode("utf-8"),
            memory.address,
            0x0080 | 0x0002,  # METH_FASTCALL | METH_KEYWORDS
            f"{name}($self, /, data)\n--\n\nGenerated native function.".encode(),
        )
        source = assembly.encode("utf-8") if isinstance(assembly, str) else assembly
        # Keep diagnostics compact without caching their decoded copies. The
        # executable mapping owns the code; constants need one owner per identity.
        return super().__new__(
            cls, len(code), zlib.compress(source, level=1),
            tuple({id(value): value for value in constants}.values()), memory, method, raw_entry_offset, program,
        )

    @property
    def machine_code(self) -> bytes:
        return self.memory.mapping[:self.machine_code_size]

    @property
    def assembly(self) -> str:
        return zlib.decompress(self.assembly_source).decode("utf-8")

    @property
    def raw_address(self) -> int:
        return self.memory.address + self.raw_entry_offset

    def __repr__(self):
        return f"<NativeCode ({self.machine_code_size} bytes)>"

    def make_callable(self):
        make_function = ctypes.pythonapi.PyCFunction_NewEx
        make_function.argtypes = (ctypes.POINTER(MethodDef), ctypes.py_object, ctypes.c_void_p)
        make_function.restype = ctypes.py_object
        return make_function(ctypes.byref(self.method), self, None)
