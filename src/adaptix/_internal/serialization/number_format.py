import ctypes
from dataclasses import dataclass
from functools import cache

CHARCONV_SYMBOL = "_ZSt8to_charsPcS_dSt12chars_format"
MIN_FIXED_FLOAT = 1e-4
MAX_FIXED_FLOAT = 1e16


class CharconvResult(ctypes.Structure):
    _fields_ = [("end", ctypes.c_void_p), ("error", ctypes.c_int)]


@dataclass(frozen=True)
class FloatFormatter:
    address: int
    owner: object


@cache
def get_float_formatter() -> FloatFormatter | None:
    try:
        library = ctypes.CDLL("libstdc++.so.6")
        function = getattr(library, CHARCONV_SYMBOL)
    except (OSError, AttributeError):
        return None
    function.argtypes = (ctypes.c_void_p, ctypes.c_void_p, ctypes.c_double, ctypes.c_int)
    function.restype = CharconvResult
    for value in (-0.0, 1.0, 4.6, 1.0000000000000002, 1e15, 1e16, 1e-4, 1e-5, 5e-324, 1.7976931348623157e308):
        buffer = ctypes.create_string_buffer(32)
        start = ctypes.addressof(buffer)
        fixed = value == 0.0 or MIN_FIXED_FLOAT <= abs(value) < MAX_FIXED_FLOAT
        result = function(start, start + 30, value, 2 if fixed else 1)
        if result.error or result.end is None or not start < result.end <= start + 30:
            return None
        rendered = ctypes.string_at(start, result.end - start)
        if fixed and b"." not in rendered:
            rendered += b".0"
        if rendered != repr(value).encode():
            return None
    return FloatFormatter(ctypes.cast(function, ctypes.c_void_p).value, library)
