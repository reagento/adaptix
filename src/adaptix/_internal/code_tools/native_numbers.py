import ctypes
import sys
from functools import cache


@cache
def integer_layout_supported():
    if sys.version_info[:2] not in {(3, 13), (3, 14)} or sys.int_info.bits_per_digit != 30:  # noqa: PLR2004
        return False
    for value in (0, 1, -1, (1 << 30) - 1):
        tag = ctypes.c_size_t.from_address(id(value) + 16).value & ~4
        expected = 1 if value == 0 else 8 if value > 0 else 10
        if tag != expected:
            return False
        if value and ctypes.c_uint32.from_address(id(value) + 24).value != abs(value):
            return False
    return True


@cache
def float_layout_supported():
    probe = 1.25
    return ctypes.c_double.from_address(id(probe) + 16).value == probe
