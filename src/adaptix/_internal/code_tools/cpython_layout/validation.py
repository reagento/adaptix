import ctypes
import sys
from abc import ABC, abstractmethod
from collections.abc import Callable, Mapping
from datetime import date, datetime, time, timedelta, timezone
from typing import Any, cast

from adaptix._internal.code_tools.cpython_layout.definitions import CPythonLayout

UNVERIFIABLE_OFFSETS = frozenset({
    "abc_invalidation_counter", "interpreter_eval_frame", "thread_eval_breaker",
})

T_OBJECT_EX = 16
TP_GETATTRO = 58
COMPACT_ASCII = 0x60
DICT_KEYS_GENERAL = 0
DICT_KEYS_UNICODE = 1
LONG_DIGIT_BITS = 30
LONG_SIZE_SHIFT = 3
LONG_SIGN_ZERO = 1
LONG_SIGN_NEGATIVE = 2
MIN_INDEX_BYTES_LOG2 = 3
MAX_INDEX_BYTES_LOG2 = 12
MAX_STRUCT_OFFSET = 1024
MAX_SET_TABLE_ENTRIES = 1 << 12
MIN_HEAP_ADDRESS = 1 << 12
MAX_SHARED_KEYS = 64
WIDE_DICT_KEYS = 200
WIDE_SET_MEMBERS = 37
INLINE_PROBE_ATTRIBUTES = 3

CheckResult = Mapping[str, bool]
Check = Callable[[CPythonLayout], CheckResult]


def read_pointer(address: int) -> int:
    return ctypes.c_void_p.from_address(address).value or 0


def read_ssize(address: int) -> int:
    return ctypes.c_ssize_t.from_address(address).value


def read_uint8(address: int) -> int:
    return ctypes.c_uint8.from_address(address).value


def read_uint32(address: int) -> int:
    return ctypes.c_uint32.from_address(address).value


def read_int(address: int) -> int:
    return ctypes.c_int.from_address(address).value


def read_ulong(address: int) -> int:
    return ctypes.c_ulong.from_address(address).value


def plausible_address(address: int) -> bool:
    return address >= MIN_HEAP_ADDRESS and address % 8 == 0


def has_type(layout: CPythonLayout, address: int, cls: type) -> bool:
    return plausible_address(address) and read_pointer(address + layout.object_type) == id(cls)


def unwrap(address: int) -> object:
    return ctypes.cast(address, ctypes.py_object).value


def type_slot_address(cls: type, slot: int) -> int:
    getter = ctypes.PYFUNCTYPE(ctypes.c_void_p, ctypes.py_object, ctypes.c_int)(
        ctypes.cast(ctypes.pythonapi.PyType_GetSlot, ctypes.c_void_p).value or 0,
    )
    return getter(cls, slot) or 0


def check_object_header(layout: CPythonLayout) -> CheckResult:
    probe = object()
    references = read_ssize(id(probe) + layout.object_refcount)
    expected = sys.getrefcount(probe)
    sample = (object(), 1, 2)
    return {
        "object_refcount": abs(references - expected) <= 1,
        "object_type": read_pointer(id(probe) + layout.object_type) == id(object),
        "object_size": layout.object_size == probe.__sizeof__(),
        "var_size": read_ssize(id(sample) + layout.var_size) == len(sample),
    }


def check_sequences(layout: CPythonLayout) -> CheckResult:
    first, second = object(), object()
    sample_tuple = (first, second)
    sample_list = [first, second]
    sample_set = {first, second}
    wide_set = set(range(WIDE_SET_MEMBERS))
    items = read_pointer(id(sample_list) + layout.list_items)
    allocated = read_ssize(id(sample_list) + layout.list_allocated)
    return {
        "tuple_items": read_pointer(id(sample_tuple) + layout.tuple_items) == id(first),
        "list_items": plausible_address(items) and read_pointer(items) == id(first),
        "list_allocated": allocated == len(sample_list),
        "set_used": (
            read_ssize(id(sample_set) + layout.set_used) == len(sample_set)
            and read_ssize(id(wide_set) + layout.set_used) == len(wide_set)
        ),
    }


def check_type_object(layout: CPythonLayout) -> CheckResult:
    class Probe:
        field: object
        extra: bool

    Probe().field = object()
    version_before = read_uint32(id(Probe) + layout.offset("type_version"))
    Probe.extra = True
    version_after = read_uint32(id(Probe) + layout.offset("type_version"))
    return {
        "type_basic_size": read_ssize(id(Probe) + layout.offset("type_basic_size")) == Probe.__basicsize__,
        "type_flags": read_ulong(id(Probe) + layout.offset("type_flags")) == Probe.__flags__,
        "type_getattro": (
            read_pointer(id(Probe) + layout.offset("type_getattro")) == type_slot_address(Probe, TP_GETATTRO)
        ),
        "type_version": bool(version_before) and not version_after,
    }


def check_dict_core(layout: CPythonLayout) -> CheckResult:
    sample = {"alpha": object(), "beta": object()}
    keys = read_pointer(id(sample) + layout.offset("dict_keys"))
    usable = plausible_address(keys)
    index_bytes = read_uint8(keys + layout.offset("keys_index_bytes")) if usable else -1
    return {
        "dict_used": read_ssize(id(sample) + layout.offset("dict_used")) == len(sample),
        "dict_keys": usable,
        "dict_values": read_pointer(id(sample) + layout.offset("dict_values")) == 0,
        "keys_kind": usable and read_uint8(keys + layout.offset("keys_kind")) == DICT_KEYS_UNICODE,
        "keys_nentries": usable and read_ssize(keys + layout.offset("keys_nentries")) == len(sample),
        "keys_refcount": usable and read_ssize(keys + layout.offset("keys_refcount")) == 1,
        "keys_index_bytes": MIN_INDEX_BYTES_LOG2 <= index_bytes <= MAX_INDEX_BYTES_LOG2,
    }


def walk_dict_entries(
    layout: CPythonLayout, data: dict, kind: int, entry_size: str, entry_key: str, entry_value: str,
) -> dict[object, int] | None:
    keys = read_pointer(id(data) + layout.offset("dict_keys"))
    if not plausible_address(keys) or read_uint8(keys + layout.offset("keys_kind")) != kind:
        return None
    count = read_ssize(keys + layout.offset("keys_nentries"))
    index_bytes = read_uint8(keys + layout.offset("keys_index_bytes"))
    size = layout.offset(entry_size)
    indices = layout.offset("keys_indices")
    usable = (
        count == len(data)
        and MIN_INDEX_BYTES_LOG2 <= index_bytes <= MAX_INDEX_BYTES_LOG2
        and 0 <= layout.offset(entry_key) < size
        and 0 <= layout.offset(entry_value) < size
        and 0 < indices <= MAX_STRUCT_OFFSET
        and size <= MAX_STRUCT_OFFSET
    )
    if not usable:
        return None
    entries = keys + indices + (1 << index_bytes)
    found = {}
    for index in range(count):
        entry = entries + size * index
        key = read_pointer(entry + layout.offset(entry_key))
        if not plausible_address(key):
            return None
        key_type = read_pointer(key + layout.object_type)
        if key_type not in {id(str), id(int)}:
            return None
        found[unwrap(key)] = read_pointer(entry + layout.offset(entry_value))
    return found


def check_dict_entries(layout: CPythonLayout) -> CheckResult:
    first, second = object(), object()
    unicode_keyed = {"alpha": first, "beta": second}
    general_keyed = {1: first, "beta": second}
    wide_keys = [str(index) for index in range(WIDE_DICT_KEYS)]
    wide_keyed = dict.fromkeys(wide_keys, first)
    unicode_found = walk_dict_entries(
        layout, unicode_keyed, DICT_KEYS_UNICODE,
        "unicode_entry_size", "unicode_entry_key", "unicode_entry_value",
    )
    wide_found = walk_dict_entries(
        layout, wide_keyed, DICT_KEYS_UNICODE,
        "unicode_entry_size", "unicode_entry_key", "unicode_entry_value",
    )
    general_found = walk_dict_entries(
        layout, general_keyed, DICT_KEYS_GENERAL,
        "general_entry_size", "general_entry_key", "general_entry_value",
    )
    unicode_ok = (
        unicode_found == {"alpha": id(first), "beta": id(second)}
        and wide_found == dict.fromkeys(wide_keys, id(first))
    )
    general_ok = general_found == {1: id(first), "beta": id(second)}
    return {
        "keys_indices": unicode_ok,
        "unicode_entry_size": unicode_ok,
        "unicode_entry_key": unicode_ok,
        "unicode_entry_value": unicode_ok,
        "general_entry_size": general_ok,
        "general_entry_key": general_ok,
        "general_entry_value": general_ok,
    }


def check_inline_values(layout: CPythonLayout) -> CheckResult:
    class Probe:
        leading: object
        field: object
        trailing: object

    probe = Probe()
    value = object()
    probe.leading = object()
    probe.field = value
    probe.trailing = object()
    basic_size = read_ssize(id(Probe) + layout.offset("type_basic_size"))
    cached_keys = read_pointer(id(Probe) + layout.offset("type_cached_keys"))
    if not plausible_address(cached_keys) or basic_size != Probe.__basicsize__:
        return dict.fromkeys(
            ("type_cached_keys", "values_valid", "values_items", "values_size", "values_capacity"), False,
        )
    index_bytes = read_uint8(cached_keys + layout.offset("keys_index_bytes"))
    count = read_ssize(cached_keys + layout.offset("keys_nentries"))
    if not MIN_INDEX_BYTES_LOG2 <= index_bytes <= MAX_INDEX_BYTES_LOG2 or not 0 < count <= MAX_SHARED_KEYS:
        return dict.fromkeys(
            ("type_cached_keys", "values_valid", "values_items", "values_size", "values_capacity"), False,
        )
    entries = cached_keys + layout.offset("keys_indices") + (1 << index_bytes)
    index = None
    for position in range(count):
        key = read_pointer(entries + layout.offset("unicode_entry_size") * position)
        if has_type(layout, key, str) and unwrap(key) == "field":
            index = position
    values = id(probe) + basic_size
    size = read_uint8(values + layout.offset("values_size"))
    return {
        "type_cached_keys": index is not None,
        "values_valid": read_uint8(values + layout.offset("values_valid")) == 1,
        "values_items": index is not None and read_pointer(
            values + layout.offset("values_items") + ctypes.sizeof(ctypes.c_void_p) * index,
        ) == id(value),
        "values_size": size == INLINE_PROBE_ATTRIBUTES,
        "values_capacity": size <= read_uint8(values + layout.offset("values_capacity")),
    }


def check_unicode(layout: CPythonLayout) -> CheckResult:
    probe = bytearray(b"native_key").decode()
    wide = bytearray(b"\xd0\xba\xd0\xbb\xd1\x8e\xd1\x87").decode("utf-8")
    digest = hash(probe)
    return {
        "unicode_length": read_ssize(id(probe) + layout.offset("unicode_length")) == len(probe),
        "unicode_hash": read_ssize(id(probe) + layout.offset("unicode_hash")) == digest,
        "unicode_state": (
            read_uint32(id(probe) + layout.offset("unicode_state")) & COMPACT_ASCII == COMPACT_ASCII
            and read_uint32(id(wide) + layout.offset("unicode_state")) & COMPACT_ASCII != COMPACT_ASCII
        ),
        "unicode_ascii_data": (
            ctypes.string_at(id(probe) + layout.offset("unicode_ascii_data"), len(probe)) == probe.encode("ascii")
        ),
    }


def check_bytes(layout: CPythonLayout) -> CheckResult:
    probe = bytes(bytearray(b"native-payload"))
    return {"bytes_data": ctypes.string_at(id(probe) + layout.offset("bytes_data"), len(probe)) == probe}


def rebuild_long(layout: CPythonLayout, value: int) -> int | None:
    digits_offset = layout.offset("long_digits")
    tag = read_ssize(id(value) + layout.offset("long_tag"))
    count, sign = tag >> LONG_SIZE_SHIFT, tag & ((1 << LONG_SIZE_SHIFT) - 1)
    allocated = (value.__sizeof__() - digits_offset) // ctypes.sizeof(ctypes.c_uint32)
    if not 0 <= count <= allocated:
        return None
    digits = (ctypes.c_uint32 * count).from_address(id(value) + digits_offset)
    magnitude = sum(int(digits[index]) << (LONG_DIGIT_BITS * index) for index in range(count))
    if sign & LONG_SIGN_ZERO:
        return 0
    return -magnitude if sign & LONG_SIGN_NEGATIVE else magnitude


def check_long(layout: CPythonLayout) -> CheckResult:
    samples = (
        0, 1, -1, 12345, -98765, 2 ** 30 - 1, 2 ** 30, 2 ** 31, -(2 ** 64) - 7,
        2 ** 300, -(2 ** 300), 10 ** 100,
    )
    correct = all(rebuild_long(layout, int(str(value))) == value for value in samples)
    return {"long_tag": correct, "long_digits": correct}


def check_set_table(layout: CPythonLayout) -> CheckResult:
    members = (object(), object(), object())
    probe = set(members)
    table = read_pointer(id(probe) + layout.offset("set_table"))
    mask = read_ssize(id(probe) + layout.offset("set_mask"))
    if not plausible_address(table) or not 0 < mask + 1 <= MAX_SET_TABLE_ENTRIES or (mask + 1) & mask:
        return dict.fromkeys(("set_mask", "set_table", "set_entry_size"), False)
    occupied = set()
    for index in range(mask + 1):
        key = read_pointer(table + layout.offset("set_entry_size") * index)
        if key:
            occupied.add(key)
    correct = occupied == {id(member) for member in members}
    return {"set_mask": correct, "set_table": correct, "set_entry_size": correct}


def check_member_descriptor(layout: CPythonLayout) -> CheckResult:
    class Probe:
        __slots__ = ("alpha", "target")
        alpha: object
        target: object

    probe = Probe()
    value = object()
    probe.alpha = object()
    probe.target = value
    descriptor = Probe.__dict__["target"]
    member = read_pointer(id(descriptor) + layout.offset("member_descriptor_member"))
    if not plausible_address(member):
        return dict.fromkeys(
            ("member_descriptor_member", "member_type", "member_offset", "member_flags"), False,
        )
    offset = read_ssize(member + layout.offset("member_offset"))
    return {
        "member_descriptor_member": True,
        "member_type": read_int(member + layout.offset("member_type")) == T_OBJECT_EX,
        "member_offset": (
            layout.object_size <= offset < Probe.__basicsize__ and read_pointer(id(probe) + offset) == id(value)
        ),
        "member_flags": read_int(member + layout.offset("member_flags")) == 0,
    }


def check_function(layout: CPythonLayout) -> CheckResult:
    def probe(first, second=1, *, third=2):
        return first, second, third

    return {
        "function_code": read_pointer(id(probe) + layout.offset("function_code")) == id(probe.__code__),
        "function_defaults": read_pointer(id(probe) + layout.offset("function_defaults")) == id(probe.__defaults__),
        "function_kwdefaults": (
            read_pointer(id(probe) + layout.offset("function_kwdefaults")) == id(probe.__kwdefaults__)
        ),
    }


def check_cell(layout: CPythonLayout) -> CheckResult:
    value = object()

    def outer():
        captured = value

        def inner():
            return captured

        return inner.__closure__[0]

    cell = outer()
    return {
        "cell_contents": read_pointer(id(cell) + layout.offset("cell_contents")) == id(cell.cell_contents),
        "cell_size": layout.offset("cell_size") == cell.__sizeof__(),
    }


def check_thread_state(layout: CPythonLayout) -> CheckResult:
    ctypes.pythonapi.PyThreadState_Get.restype = ctypes.c_void_p
    ctypes.pythonapi.PyInterpreterState_Get.restype = ctypes.c_void_p
    state = ctypes.pythonapi.PyThreadState_Get()
    interpreter = ctypes.pythonapi.PyInterpreterState_Get()

    def hook(*args):
        return None

    previous_profile = sys.getprofile()
    sys.setprofile(hook)
    profile_set = read_pointer(state + layout.offset("thread_profile"))
    sys.setprofile(previous_profile)
    previous_trace = sys.gettrace()
    sys.settrace(hook)
    trace_set = read_pointer(state + layout.offset("thread_trace"))
    sys.settrace(previous_trace)
    return {
        "thread_interpreter": read_pointer(state + layout.offset("thread_interpreter")) == interpreter,
        "thread_profile": bool(profile_set) and not read_pointer(state + layout.offset("thread_profile")),
        "thread_trace": bool(trace_set) and not read_pointer(state + layout.offset("thread_trace")),
    }


def unpack_datetime_data(layout: CPythonLayout, value: datetime) -> tuple[int, ...]:
    data = ctypes.string_at(id(value) + layout.offset("datetime_data"), 10)
    return (
        (data[0] << 8) | data[1], data[2], data[3], data[4], data[5], data[6],
        (data[7] << 16) | (data[8] << 8) | data[9],
    )


def check_datetime(layout: CPythonLayout) -> CheckResult:
    zone = timezone(timedelta(hours=3))
    aware = datetime(2026, 10, 18, 14, 30, 5, 123456, tzinfo=zone)
    naive = datetime(2026, 10, 18, 14, 30, 5, 123456)  # noqa: DTZ001
    digest = hash(aware)
    expected = (
        aware.year, aware.month, aware.day, aware.hour, aware.minute, aware.second, aware.microsecond,
    )
    return {
        "datetime_data": unpack_datetime_data(layout, aware) == expected,
        "datetime_hash": read_ssize(id(aware) + layout.offset("datetime_hash")) == digest,
        "datetime_has_tzinfo": (
            read_uint8(id(aware) + layout.offset("datetime_has_tzinfo")) == 1
            and read_uint8(id(naive) + layout.offset("datetime_has_tzinfo")) == 0
        ),
        "datetime_tzinfo": read_pointer(id(aware) + layout.offset("datetime_tzinfo")) == id(zone),
        "datetime_size": layout.offset("datetime_size") == aware.__sizeof__(),
        "datetime_naive_size": layout.offset("datetime_naive_size") == layout.offset("datetime_tzinfo"),
        "date_size": layout.offset("date_size") == date(2026, 10, 18).__sizeof__(),
    }


def check_time(layout: CPythonLayout) -> CheckResult:
    zone = timezone(timedelta(hours=-5))
    aware = time(14, 30, 5, 123456, tzinfo=zone)
    data = ctypes.string_at(id(aware) + layout.offset("time_data"), 6)
    unpacked = (data[0], data[1], data[2], (data[3] << 16) | (data[4] << 8) | data[5])
    return {
        "time_data": unpacked == (aware.hour, aware.minute, aware.second, aware.microsecond),
        "time_tzinfo": read_pointer(id(aware) + layout.offset("time_tzinfo")) == id(zone),
        "time_size": layout.offset("time_size") == aware.__sizeof__(),
        "time_naive_size": layout.offset("time_naive_size") == layout.offset("time_tzinfo"),
    }


def check_timedelta(layout: CPythonLayout) -> CheckResult:
    probe = timedelta(days=5, seconds=7, microseconds=9)
    return {
        "timedelta_days": read_int(id(probe) + layout.offset("timedelta_days")) == probe.days,
        "timedelta_seconds": read_int(id(probe) + layout.offset("timedelta_seconds")) == probe.seconds,
        "timedelta_microseconds": (
            read_int(id(probe) + layout.offset("timedelta_microseconds")) == probe.microseconds
        ),
        "timedelta_size": layout.offset("timedelta_size") == probe.__sizeof__(),
    }


def check_timezone(layout: CPythonLayout) -> CheckResult:
    offset = timedelta(hours=3, minutes=30)
    zone = timezone(offset)
    stored = read_pointer(id(zone) + layout.offset("timezone_offset"))
    return {
        "timezone_offset": has_type(layout, stored, timedelta) and unwrap(stored) == offset,
        "timezone_size": layout.offset("timezone_size") == zone.__sizeof__(),
    }


def check_dict_iterator(layout: CPythonLayout) -> CheckResult:
    source = {"alpha": object(), "beta": object()}
    iterator = iter(source)
    start = read_ssize(id(iterator) + layout.offset("dictiter_position"))
    remaining_before = read_ssize(id(iterator) + layout.offset("dictiter_remaining"))
    next(iterator)
    advanced = read_ssize(id(iterator) + layout.offset("dictiter_position"))
    remaining_after = read_ssize(id(iterator) + layout.offset("dictiter_remaining"))
    return {
        "dictiter_dict": read_pointer(id(iterator) + layout.offset("dictiter_dict")) == id(source),
        "dictiter_used": read_ssize(id(iterator) + layout.offset("dictiter_used")) == len(source),
        "dictiter_position": start == 0 and advanced == 1,
        "dictiter_remaining": remaining_before == len(source) and remaining_after == len(source) - 1,
    }


def check_abc(layout: CPythonLayout) -> CheckResult:
    class Probe(ABC):
        @abstractmethod
        def method(self):
            ...

    class Unrelated:
        pass

    issubclass(Unrelated, Probe)
    cache = read_pointer(id(Probe.__dict__["_abc_impl"]) + layout.offset("abc_negative_cache"))
    if not has_type(layout, cache, set):
        return {"abc_negative_cache": False}
    referents = {reference() for reference in cast("set[Any]", unwrap(cache))}
    return {"abc_negative_cache": Unrelated in referents}


CHECKS: tuple[tuple[tuple[str, ...], Check], ...] = (
    (("object_refcount", "object_type", "object_size", "var_size"), check_object_header),
    (("tuple_items", "list_items", "list_allocated", "set_used"), check_sequences),
    (("type_basic_size", "type_flags", "type_getattro", "type_version"), check_type_object),
    ((
        "dict_used", "dict_keys", "dict_values", "keys_kind", "keys_nentries", "keys_refcount", "keys_index_bytes",
    ), check_dict_core),
    ((
        "keys_indices", "unicode_entry_size", "unicode_entry_key", "unicode_entry_value",
        "general_entry_size", "general_entry_key", "general_entry_value",
    ), check_dict_entries),
    ((
        "type_cached_keys", "values_valid", "values_items", "values_size", "values_capacity",
    ), check_inline_values),
    (("unicode_length", "unicode_hash", "unicode_state", "unicode_ascii_data"), check_unicode),
    (("bytes_data",), check_bytes),
    (("long_tag", "long_digits"), check_long),
    (("set_mask", "set_table", "set_entry_size"), check_set_table),
    ((
        "member_descriptor_member", "member_type", "member_offset", "member_flags",
    ), check_member_descriptor),
    (("function_code", "function_defaults", "function_kwdefaults"), check_function),
    (("cell_contents", "cell_size"), check_cell),
    (("thread_interpreter", "thread_profile", "thread_trace"), check_thread_state),
    ((
        "datetime_data", "datetime_hash", "datetime_has_tzinfo", "datetime_tzinfo",
        "datetime_size", "datetime_naive_size", "date_size",
    ), check_datetime),
    (("time_data", "time_tzinfo", "time_size", "time_naive_size"), check_time),
    ((
        "timedelta_days", "timedelta_seconds", "timedelta_microseconds", "timedelta_size",
    ), check_timedelta),
    (("timezone_offset", "timezone_size"), check_timezone),
    ((
        "dictiter_dict", "dictiter_used", "dictiter_position", "dictiter_remaining",
    ), check_dict_iterator),
    (("abc_negative_cache",), check_abc),
)

COVERED_OFFSETS = frozenset(name for names, _ in CHECKS for name in names) | UNVERIFIABLE_OFFSETS


def available_offset_names(layout: CPythonLayout) -> frozenset[str]:
    return frozenset(
        field for field in type(layout).__dataclass_fields__
        if field != "version" and getattr(layout, field) is not None
    )


def validate_layout(layout: CPythonLayout) -> dict[str, bool]:
    available = available_offset_names(layout)
    results: dict[str, bool] = {}
    for names, check in CHECKS:
        if all(name in available for name in names):
            results.update(check(layout))
    return results


def layout_mismatches(layout: CPythonLayout) -> frozenset[str]:
    return frozenset(name for name, correct in validate_layout(layout).items() if not correct)
