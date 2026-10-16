# ruff: noqa: PLR2004
import ctypes
import sys
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from functools import cache, partial
from threading import RLock

from adaptix._internal.code_tools.cpython_layout.selection import get_cpython_layout
from adaptix._internal.morphing.native import descriptions

LAYOUT = get_cpython_layout()

DIGITS = ctypes.create_string_buffer(b"".join(f"{value:02}".encode() for value in range(100)))
MONTH_DAYS = ctypes.create_string_buffer(bytes((0, 31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)))


@cache
def supported(cls=datetime):
    if LAYOUT is None or sys.version_info[:2] not in {(3, 13), (3, 14), (3, 15)}:
        return False
    if cls is date:
        value = date(2025, 1, 2)
        expected, size = b"\x00\x07\xe9\x01\x02", LAYOUT.date_size
    elif cls is time:
        value = time(3, 4, 5, 123456)
        expected, size = b"\x00\x03\x04\x05\x01\xe2\x40\x00", LAYOUT.time_size
    else:
        value = datetime(2025, 1, 2, 3, 4, 5, 123456, tzinfo=None)  # noqa: DTZ001
        expected, size = b"\x00\x07\xe9\x01\x02\x03\x04\x05\x01\xe2\x40\x00", LAYOUT.datetime_size
    text = bytearray(b"2025-01-02T03:04:05.123456").decode()
    return (
        not cls.__flags__ & (1 << 9)
        and cls.__basicsize__ == size
        and ctypes.string_at(id(value) + LAYOUT.datetime_has_tzinfo, len(expected)) == expected
        and ctypes.c_ssize_t.from_address(id(text) + LAYOUT.unicode_length).value == 26
        and ctypes.c_uint32.from_address(id(text) + LAYOUT.unicode_state).value & 0xFF == 0x64
        and ctypes.string_at(id(text) + LAYOUT.unicode_ascii_data, 27) == text.encode() + b"\x00"
    )


@cache
def timezone_supported():
    if LAYOUT is None:
        return False
    delta = timedelta(hours=-5, minutes=-30)
    zone = timezone(delta)
    value = datetime(2025, 1, 2, tzinfo=zone)
    clock = time(3, 4, tzinfo=zone)
    return (
        timezone.__basicsize__ == LAYOUT.timezone_size
        and timedelta.__basicsize__ == LAYOUT.timedelta_size
        and ctypes.c_void_p.from_address(id(zone) + LAYOUT.timezone_offset).value == id(delta)
        and ctypes.c_int.from_address(id(delta) + LAYOUT.timedelta_days).value == delta.days
        and ctypes.c_int.from_address(id(delta) + LAYOUT.timedelta_seconds).value == delta.seconds
        and ctypes.c_int.from_address(id(delta) + LAYOUT.timedelta_microseconds).value == 0
        and ctypes.c_void_p.from_address(id(value) + LAYOUT.datetime_tzinfo).value == id(zone)
        and ctypes.c_void_p.from_address(id(clock) + LAYOUT.time_tzinfo).value == id(zone)
    )


def dump_offset(c, cls, generic):
    """Read only an exact immutable timezone, in whole minutes."""
    sign, minutes = c.slot(), c.slot()
    c.asm.emit(b"\x31\xc0", "xor eax, eax")
    c.asm.store(sign)
    naive, positive = c.label("no_offset"), c.label("positive_offset")
    c.asm.load(0, c.data)
    c.asm.emit(b"\x80\x78" + bytes([c.layout.datetime_has_tzinfo]) + b"\x00", "check timezone flag")
    c.asm.jump(naive, "z")
    if cls is date or not timezone_supported():
        c.asm.jump(generic)
    else:
        c.asm.emit(
            b"\x48\x8b\x40" + bytes([c.layout.time_tzinfo if cls is time else c.layout.datetime_tzinfo]), "load tzinfo",
        )
        c.load(11, c.constant(timezone))
        c.asm.emit(b"\x4c\x39\x58" + bytes([c.layout.object_type]), "check exact timezone")
        c.asm.jump(generic, "nz")
        c.asm.emit(
            (
                b"\x48\x8b\x50"
                + bytes([c.layout.timezone_offset])
                + b"\x83\x7a"
                + bytes([c.layout.timedelta_microseconds])
                + b"\x00"
            ),
            "read timedelta; check offset fraction",
        )
        c.asm.jump(generic, "nz")
        c.asm.emit(
            (
                b"\x69\x42"
                + bytes([c.layout.timedelta_days])
                + b"\x80\x51\x01\x00\x03\x42"
                + bytes([c.layout.timedelta_seconds])
            ),
            "offset seconds = days * 86400 + seconds",
        )
        c.asm.emit(b"\x99\xb9\x3c\x00\x00\x00\xf7\xf9\x85\xd2", "divide offset seconds by 60")
        c.asm.jump(generic, "nz")
        c.asm.emit(b"\xb9\x2b\x00\x00\x00\x85\xc0", "positive offset sign")
        c.asm.jump(positive, "ns")
        c.asm.emit(b"\xf7\xd8\xb9\x2d\x00\x00\x00", "absolute offset; negative sign")
        c.asm.label(positive)
        c.asm.store(sign, 1)
        c.asm.store(minutes)
    c.asm.label(naive)
    return sign, minutes


def write_offset(c, sign, minutes, length, done):
    c.asm.load(0, sign)
    c.asm.test_jump(0, done, bits=32)
    c.asm.load(10, length)
    c.asm.emit(b"\x43\x88\x44\x11" + bytes([c.layout.unicode_ascii_data]), "store timezone sign")
    c.asm.load(0, minutes)
    c.asm.emit(b"\x31\xd2\xb9\x3c\x00\x00\x00\xf7\xf1", "divide absolute offset by 60")
    c.asm.emit(b"\x41\x0f\xb7\x0c\x43\x41\x0f\xb7\x04\x53", "read timezone hour/minute decimal pairs")
    c.asm.emit(
        (
            b"\x66\x43\x89\x4c\x11"
            + bytes([c.layout.unicode_ascii_data+1])
            + b"\x43\xc6\x44\x11"
            + bytes([c.layout.unicode_ascii_data+3])
            + b"\x3a\x66\x43\x89\x44\x11"
            + bytes([c.layout.unicode_ascii_data+4])
        ), "store HH:MM timezone suffix",
    )


class TimezoneCache(ctypes.Structure):
    _fields_ = [("count", ctypes.c_uint32), ("offsets", ctypes.c_int32 * 8), ("zones", ctypes.c_void_p * 8)]

    def __init__(self):
        super().__init__()
        self.owners = []
        self.offset_array = self.offsets
        self.zone_array = self.zones
        self.lock = RLock()

    def load(self, function, data):
        value = function(data)
        if type(value) not in (time, datetime) or type(value.tzinfo) is not timezone:
            return value
        delta = value.utcoffset()
        seconds = delta.days * 86400 + delta.seconds
        if delta.microseconds or seconds % 60:
            return value
        minutes = seconds // 60
        if minutes in self.offsets[: self.count] or self.count == 8:
            return value
        # Retain before publishing; appending can run a reentrant GC callback.
        self.owners.append(value.tzinfo)
        with self.lock:
            if minutes not in self.offset_array[:self.count]:
                index = self.count
                if index < 8:
                    # Reuse array views: creating ctypes views can itself run GC.
                    self.offset_array[index] = minutes
                    self.zone_array[index] = id(value.tzinfo)
                    self.count = index + 1
        return value


def load_offset(c, position, generic, cache, zone):
    positive, found = c.label("positive_iso_offset"), c.label("known_iso_offset")
    hours = c.slot()
    c.asm.emit(b"\x41\x80\x78" + bytes([c.layout.unicode_ascii_data + position + 3, 58]), "check timezone colon")
    c.asm.jump(generic, "nz")
    parse_pair(c, position + 1, generic, limit=23)
    c.asm.store(hours)
    parse_pair(c, position + 4, generic, limit=59)
    c.asm.load(1, hours)
    c.asm.emit(b"\x6b\xc9\x3c\x01\xc8", "offset minutes = hours * 60 + minutes")
    c.asm.emit(b"\x41\x80\x78" + bytes([c.layout.unicode_ascii_data + position, 43]), "check positive timezone sign")
    c.asm.jump(positive, "z")
    c.asm.emit(b"\x41\x80\x78" + bytes([c.layout.unicode_ascii_data + position, 45]), "check negative timezone sign")
    c.asm.jump(generic, "nz")
    c.asm.emit(b"\xf7\xd8", "neg eax")
    c.asm.label(positive)
    c.asm.mov_imm(11, ctypes.addressof(cache))
    c.asm.emit(b"\x31\xc9", "start timezone cache search")
    search = c.label("find_iso_timezone")
    c.asm.label(search)
    c.asm.emit(b"\x41\x3b\x0b", "check timezone cache count")
    c.asm.jump(generic, "ae")
    c.asm.emit(b"\x41\x3b\x44\x8b" + bytes([TimezoneCache.offsets.offset]), "compare cached offset minutes")
    c.asm.jump(found, "z")
    c.asm.emit(b"\xff\xc1", "inc ecx")
    c.asm.jump(search)
    c.asm.label(found)
    c.asm.emit(b"\x49\x8b\x44\xcb" + bytes([TimezoneCache.zones.offset]), "load cached immutable timezone")
    retained = c.copy_loaded_reference()
    c.transfer(retained, zone)


def divide_100(c):
    """Unsigned eax / 100 -> ecx, remainder -> eax, with edx as scratch."""
    c.asm.mov_imm(1, 1374389535)
    c.asm.emit(b"\x48\x0f\xaf\xc8\x48\xc1\xe9\x25", "imul rcx, rax; shr rcx, 37  # divide by 100")
    c.asm.emit(b"\x6b\xd1\x64\x29\xd0", "imul edx, ecx, 100; sub eax, edx")


def write_pair(c, source_offset, output_offset):
    c.asm.emit(b"\x41\x0f\xb6\x40" + bytes([source_offset]), f"movzx eax, BYTE PTR [r8+{source_offset}]")
    c.asm.emit(b"\x41\x0f\xb7\x04\x43", "movzx eax, WORD PTR [r11+rax*2]")
    c.asm.emit(
        b"\x66\x41\x89\x41" + bytes([c.layout.unicode_ascii_data + output_offset]),
        f"mov WORD PTR [r9+{c.layout.unicode_ascii_data + output_offset}], ax",
    )


def parse_pair(c, offset, generic, *, limit=99, nonzero=False):
    c.asm.emit(
        b"\x41\x0f\xb7\x40" + bytes([c.layout.unicode_ascii_data + offset]), "movzx eax, WORD PTR [r8+decimal_pair]",
    )
    c.asm.emit(b"\x2d\x30\x30\x00\x00\x89\xc1\x81\xe1\xff\x00\x00\x00", "sub eax, 0x3030; mov ecx, eax; and ecx, 255")
    c.asm.emit(b"\x83\xf9\x09", "cmp first decimal digit, 9")
    c.asm.jump(generic, "a")
    c.asm.emit(b"\xc1\xe8\x08\x83\xf8\x09", "shr eax, 8; cmp second decimal digit, 9")
    c.asm.jump(generic, "a")
    c.asm.emit(b"\x6b\xc9\x0a\x01\xc8", "imul ecx, ecx, 10; add eax, ecx")
    if limit != 99:
        c.asm.emit(b"\x83\xf8" + bytes([limit]), f"cmp eax, {limit}")
        c.asm.jump(generic, "a")
    if nonzero:
        c.asm.test_jump(0, generic, bits=32)


def load_datetime(c, function, cls):  # noqa: C901, PLR0912, PLR0915
    generic, done, no_memory = (c.label(prefix) for prefix in ("iso_parse_slow", "iso_parsed", "iso_parse_no_memory"))
    result = c.slot(owned=True)
    zone = c.slot(owned=True)
    base_length = c.slot()
    timezone_cache = TimezoneCache() if cls is not date and timezone_supported() else None
    if timezone_cache is not None:
        c.constants.append(timezone_cache)
    c.branch_if_type(c.data, str, generic, invert=True)
    c.asm.load(8, c.data)
    c.asm.emit(
        b"\x41\x8b\x40" + bytes([c.layout.unicode_state]) + b"\x83\xe0\x60\x83\xf8\x60", "test compact ASCII string",
    )
    c.asm.jump(generic, "nz")
    short_length = 10 if cls is date else 8 if cls is time else 19
    c.asm.mov_imm(0, short_length)
    c.asm.store(base_length)
    c.asm.emit(b"\x49\x83\x78" + bytes([c.layout.unicode_length]) + bytes([short_length]), "check ISO string length")
    length_ok = c.label("iso_length_ok")
    c.asm.jump(length_ok, "z")
    if cls is date:
        c.asm.jump(generic)
    else:
        fraction, aware_short, aware_fraction = (
            c.label(prefix) for prefix in ("iso_fraction", "iso_offset", "iso_fraction_offset")
        )
        c.asm.emit(
            b"\x49\x83\x78" + bytes([c.layout.unicode_length]) + bytes([short_length + 7]),
            "check fractional ISO length",
        )
        c.asm.jump(fraction, "z")
        if timezone_cache is not None:
            c.asm.emit(
                b"\x49\x83\x78" + bytes([c.layout.unicode_length]) + bytes([short_length + 6]),
                "check timezone ISO length",
            )
            c.asm.jump(aware_short, "z")
            c.asm.emit(
                b"\x49\x83\x78" + bytes([c.layout.unicode_length]) + bytes([short_length + 13]),
                "check fractional timezone ISO length",
            )
            c.asm.jump(aware_fraction, "z")
        c.asm.jump(generic)
        if timezone_cache is not None:
            c.asm.label(aware_short)
            load_offset(c, short_length, generic, timezone_cache, zone)
            c.asm.jump(length_ok)
            c.asm.label(aware_fraction)
            load_offset(c, short_length + 7, generic, timezone_cache, zone)
        c.asm.label(fraction)
        c.asm.mov_imm(0, short_length + 7)
        c.asm.store(base_length)
        c.asm.emit(
            b"\x41\x80\x78" + bytes([c.layout.unicode_ascii_data + short_length, 46]), "check fractional separator",
        )
        c.asm.jump(generic, "nz")
    c.asm.label(length_ok)
    separators = (
        ((4, 45), (7, 45))
        if cls is date
        else ((2, 58), (5, 58))
        if cls is time
        else ((4, 45), (7, 45), (10, 84), (13, 58), (16, 58))
    )
    for offset, value in separators:
        c.asm.emit(b"\x41\x80\x78" + bytes([c.layout.unicode_ascii_data + offset, value]), "cmp ISO separator")
        c.asm.jump(generic, "nz")
    fields = []
    if cls is not time:
        year = c.slot()
        parse_pair(c, 0, generic)
        c.asm.store(year)
        parse_pair(c, 2, generic)
        c.asm.load(1, year)
        c.asm.emit(b"\x6b\xc9\x64\x01\xc8\x85\xc0", "imul ecx, ecx, 100; add eax, ecx; test eax, eax")
        c.asm.jump(generic, "z")
        c.asm.store(year)
        fields = [year]
        for offset, limit, nonzero in ((5, 12, True), (8, 31, True)):
            parse_pair(c, offset, generic, limit=limit, nonzero=nonzero)
            value = c.slot()
            c.asm.store(value)
            fields.append(value)
        c.constants.append(MONTH_DAYS)
        c.asm.mov_imm(11, ctypes.addressof(MONTH_DAYS))
        c.asm.load(0, fields[1])
        c.asm.emit(b"\x41\x0f\xb6\x0c\x03", "movzx ecx, BYTE PTR [r11+rax]  # month length")
        c.asm.load(0, fields[2])
        c.asm.emit(b"\x39\xc8", "cmp day, month length")
        c.asm.jump(generic, "a")
        leap_done = c.label("valid_month_day")
        c.asm.load(0, fields[1])
        c.asm.emit(b"\x83\xf8\x02", "cmp month, February")
        c.asm.jump(leap_done, "nz")
        c.asm.load(0, fields[2])
        c.asm.emit(b"\x83\xf8\x1d", "cmp day, 29")
        c.asm.jump(leap_done, "nz")
        c.asm.load(0, year)
        c.asm.emit(b"\xa9\x03\x00\x00\x00", "test year modulo 4")
        c.asm.jump(generic, "nz")
        divide_100(c)
        c.asm.test_jump(0, leap_done, "nz", bits=32)
        c.asm.emit(b"\xf7\xc1\x03\x00\x00\x00", "test century modulo 4")
        c.asm.jump(generic, "nz")
        c.asm.label(leap_done)
    if cls is not date:
        time_offset = 0 if cls is time else 11
        for offset, limit in ((time_offset, 23), (time_offset + 3, 59), (time_offset + 6, 59)):
            parse_pair(c, offset, generic, limit=limit)
            value = c.slot()
            c.asm.store(value)
            fields.append(value)
    micros = c.slot()
    c.asm.emit(b"\x31\xc0", "xor eax, eax")
    c.asm.store(micros)
    no_micros = c.label("iso_seconds_only")
    c.asm.load(0, base_length)
    c.asm.emit(b"\x83\xf8" + bytes([short_length]), "check for fractional seconds")
    c.asm.jump(no_micros, "z")
    for offset in (short_length + 1, short_length + 3, short_length + 5):
        parse_pair(c, offset, generic)
        c.asm.load(1, micros)
        c.asm.emit(b"\x6b\xc9\x64\x01\xc8", "imul ecx, ecx, 100; add eax, ecx")
        c.asm.store(micros)
    c.asm.label(no_micros)
    size = c.slot()
    naive = c.label("iso_naive_allocation")
    c.asm.mov_imm(0, c.layout.datetime_naive_size if cls is datetime else c.layout.time_naive_size)
    c.asm.load(1, zone)
    c.asm.test_jump(1, naive)
    c.asm.emit(b"\x83\xc0\x08", "add timezone pointer size")
    c.asm.label(naive)
    c.asm.store(size)
    allocation = c.call_c("PyObject_Malloc", size, result="pointer")
    c.branch_if_null(allocation, no_memory)
    c.asm.load(9, allocation)
    c.asm.emit_memory(
        b"\x49\xc7", 0x01, c.layout.object_refcount, "mov reference count, 1", immediate=b"\x01\x00\x00\x00",
    )
    c.load(0, c.constant(cls))
    c.asm.emit((
                   b"\x49\x89\x41"
                   + bytes([c.layout.object_type])
                   + b"\x49\xc7\x41"
                   + bytes([c.layout.datetime_hash])
                   + b"\xff\xff\xff\xff"
               ), "mov datetime type; mov hash, -1")
    c.asm.emit(
        b"\x49\xc7\x41" + bytes([c.layout.datetime_has_tzinfo]) + b"\x00\x00\x00\x00",
        "clear date storage and timezone flag",
    )
    if cls is datetime:
        c.asm.emit(
            b"\x49\xc7\x41" + bytes([c.layout.datetime_data + 7]) + b"\x00\x00\x00\x00",
            "clear datetime fraction and fold",
        )
    if cls is not time:
        c.asm.load(0, year)
        c.asm.emit(
            b"\x66\xc1\xc0\x08\x66\x41\x89\x41" + bytes([c.layout.datetime_data]), "rol ax, 8; mov big-endian year",
        )
    data_offset = c.layout.time_data if cls is time else c.layout.datetime_data
    offsets = tuple(
        data_offset + index for index in ((0, 1, 2) if cls is time else (2, 3) if cls is date else (2, 3, 4, 5, 6))
    )
    for value, offset in zip(fields if cls is time else fields[1:], offsets, strict=True):
        c.asm.load(0, value)
        c.asm.emit(b"\x41\x88\x41" + bytes([offset]), "mov datetime component")
    if cls is not date:
        c.asm.load(0, micros)
        c.asm.emit(
            b"\x0f\xc8\xc1\xe8\x08\x41\x89\x41"
            + bytes([c.layout.time_data + 3 if cls is time else c.layout.datetime_data + 7]),
            "store microseconds and fold",
        )
        naive = c.label("iso_without_timezone")
        c.asm.load(0, zone)
        c.asm.test_jump(0, naive)
        c.asm.emit(
            b"\x41\xc6\x41"
            + bytes([c.layout.datetime_has_tzinfo])
            + b"\x01\x49\x89\x41"
            + bytes([c.layout.time_tzinfo if cls is time else c.layout.datetime_tzinfo]),
            "set timezone flag and steal reference",
        )
        c.asm.emit(b"\x31\xc0", "clear stolen timezone reference")
        c.asm.store(zone, 0, clear=True)
        c.asm.label(naive)
    c.asm.store(result, 9)
    c.asm.jump(done)
    c.asm.label(no_memory)
    c.call_c("PyErr_NoMemory")
    c.asm.label(generic)
    c.release(zone)
    fallback = partial(timezone_cache.load, function) if timezone_cache is not None else function
    value = c.call(fallback, c.data)
    c.transfer(value, result)
    c.asm.label(done)
    return result


@dataclass(frozen=True)
class DateTimeProgram(descriptions.DateTimeProgram):
    def emit(self, c):  # noqa: PLR0915
        function = descriptions.resolve_function(self.function)
        cls = self.cls
        if not c.has_validated_object_header or not supported(cls):
            return c.call(function, c.data)
        if self.loading:
            return load_datetime(c, function, cls)
        generic, done, no_memory = (
            c.label(prefix) for prefix in ("datetime_slow", "datetime_done", "datetime_no_memory")
        )
        result = c.slot(owned=True)
        c.branch_if_type(c.data, cls, generic, invert=True)
        sign, minutes = dump_offset(c, cls, generic)
        c.asm.load(0, c.data)
        short_length = 10 if cls is date else 8 if cls is time else 19
        micro_offset = c.layout.time_data + 3 if cls is time else c.layout.datetime_data + 7
        length = c.slot()
        if cls is date:
            c.asm.mov_imm(0, short_length)
        else:
            c.asm.emit(b"\x8b\x40" + bytes([micro_offset]) + b"\x25\xff\xff\xff\x00", "read microseconds")
            short = c.label("seconds_only")
            c.asm.emit(b"\x85\xc0", "test eax, eax")
            c.asm.mov_imm(0, short_length)
            c.asm.jump(short, "z")
            c.asm.mov_imm(0, short_length + 7)
            c.asm.label(short)
        base_length = c.slot()
        c.asm.store(base_length)
        if cls is not date:
            naive = c.label("iso_naive_length")
            c.asm.load(1, sign)
            c.asm.test_jump(1, naive, bits=32)
            c.asm.emit(b"\x83\xc0\x06", "add timezone suffix length")
            c.asm.label(naive)
        c.asm.store(length)
        c.asm.emit(
            b"\x48\x83\xc0" + bytes([c.layout.unicode_ascii_data + 1]),
            "add rax, 41  # ASCII header, payload and terminator",
        )
        allocation_size = c.slot()
        c.asm.store(allocation_size)
        allocation = c.call_c("PyObject_Malloc", allocation_size, result="pointer")
        c.branch_if_null(allocation, no_memory)
        c.asm.load(9, allocation)
        c.asm.emit_memory(
            b"\x49\xc7", 0x01, c.layout.object_refcount, "mov QWORD PTR [r9], 1", immediate=b"\x01\x00\x00\x00",
        )
        c.load(0, c.constant(str))
        c.asm.emit(b"\x49\x89\x41" + bytes([c.layout.object_type]), "mov [r9+8], rax")
        c.asm.load(0, length)
        c.asm.emit(b"\x49\x89\x41" + bytes([c.layout.unicode_length]), "mov [r9+16], rax")
        c.asm.emit(
            b"\x49\xc7\x41" + bytes([c.layout.unicode_hash]) + b"\xff\xff\xff\xff", "mov QWORD PTR [r9+24], -1  # hash",
        )
        c.asm.emit(
            b"\x49\xc7\x41" + bytes([c.layout.unicode_state]) + b"\x64\x00\x00\x00",
            "mov QWORD PTR [r9+32], 0x64  # compact non-interned ASCII",
        )
        c.asm.emit(b"\x41\xc6\x44\x01" + bytes([c.layout.unicode_ascii_data]) + b"\x00", "mov BYTE PTR [r9+rax+40], 0")
        c.asm.store(result, 9)
        c.asm.load(8, c.data)
        c.constants.append(DIGITS)
        c.asm.mov_imm(11, ctypes.addressof(DIGITS))
        if cls is not time:
            c.asm.emit(
                b"\x41\x0f\xb7\x40" + bytes([c.layout.datetime_data]) + b"\x66\xc1\xc0\x08", "read big-endian year",
            )
            divide_100(c)
            c.asm.emit(b"\x41\x0f\xb7\x0c\x4b\x41\x0f\xb7\x04\x43", "read year decimal pairs")
            c.asm.emit(
                (
                    b"\x66\x41\x89\x49"
                    + bytes([c.layout.unicode_ascii_data])
                    + b"\x66\x41\x89\x41"
                    + bytes([c.layout.unicode_ascii_data + 2])
                ),
                "store four-digit year",
            )
        pairs = (
            ((c.layout.datetime_data + 2, 5), (c.layout.datetime_data + 3, 8))
            if cls is date
            else ((c.layout.time_data, 0), (c.layout.time_data + 1, 3), (c.layout.time_data + 2, 6))
            if cls is time
            else tuple(
                (c.layout.datetime_data + index, target)
                for index, target in ((2, 5), (3, 8), (4, 11), (5, 14), (6, 17))
            )
        )
        for source, target in pairs:
            write_pair(c, source, target)
        separators = (
            ((4, 45), (7, 45))
            if cls is date
            else ((2, 58), (5, 58))
            if cls is time
            else ((4, 45), (7, 45), (10, 84), (13, 58), (16, 58))
        )
        for offset, value in separators:
            c.asm.emit(b"\x41\xc6\x41" + bytes([c.layout.unicode_ascii_data + offset, value]), "store ISO separator")
        suffix = c.label("iso_timezone_suffix")
        if cls is not date:
            c.asm.load(0, base_length)
            c.asm.emit(b"\x83\xf8" + bytes([short_length]), "check for fractional seconds")
            c.asm.jump(suffix, "z")
            c.asm.emit(b"\x41\xc6\x41" + bytes([c.layout.unicode_ascii_data + short_length, 46]), "store decimal point")
            c.asm.emit(
                b"\x41\x8b\x40" + bytes([micro_offset]) + b"\x0f\xc8\xc1\xe8\x08", "read big-endian microseconds",
            )
            divide_100(c)
            c.asm.emit(
                b"\x41\x0f\xb7\x04\x43\x66\x41\x89\x41" + bytes([c.layout.unicode_ascii_data + short_length + 5]),
                "store last fraction digits",
            )
            c.asm.emit(b"\x89\xc8", "mov eax, ecx")
            divide_100(c)
            c.asm.emit(b"\x41\x0f\xb7\x0c\x4b\x41\x0f\xb7\x04\x43", "read fraction decimal pairs")
            c.asm.emit(
                b"\x66\x41\x89\x49"
                + bytes([c.layout.unicode_ascii_data + short_length + 1])
                + b"\x66\x41\x89\x41"
                + bytes([c.layout.unicode_ascii_data + short_length + 3]),
                "store first fraction digits",
            )
        c.asm.label(suffix)
        if cls is not date:
            write_offset(c, sign, minutes, base_length, done)
        c.asm.jump(done)
        c.asm.label(no_memory)
        c.call_c("PyErr_NoMemory")
        return c.fallback_result(result, function, generic, done)
