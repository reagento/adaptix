import ctypes
import sys
from contextlib import suppress
from functools import cache
from threading import RLock
from types import MemberDescriptorType

from adaptix._internal.code_tools.cpython_layout.selection import get_cpython_layout

LAYOUT = get_cpython_layout()


def layout_offset(name: str) -> int:
    if LAYOUT is None:
        raise RuntimeError("No CPython layout is available for native attribute access")
    return LAYOUT.offset(name)


INLINE_VALUES = 1 << 2
MANAGED_DICT = 1 << 4
IMMUTABLE_TYPE = 1 << 8
HEAP_TYPE = 1 << 9
TP_GETATTRO = 58
TP_DESCR_SET = 55
T_OBJECT = 6
T_OBJECT_EX = 16
MEMBER_READONLY = 1
SHARED_KEYS_LIMIT = 30
DICT_KEYS_SPLIT = 2
DICT_KEYS_UNICODE = 1
COMPACT_ASCII = 0x60

GENERIC = 0
INLINE = 1
SLOT = 2
DICT = 3
SPECIALIZATION_LIMIT = 16


def pointer(address: int) -> int:
    return ctypes.c_void_p.from_address(address).value or 0


def size(address: int) -> int:
    return ctypes.c_ssize_t.from_address(address).value


def get_type_version(cls: type) -> int:
    return ctypes.c_uint32.from_address(id(cls) + layout_offset("type_version")).value


def api_address(name: str) -> int | None:
    function = getattr(getattr(ctypes, "pythonapi", None), name, None)
    return ctypes.cast(function, ctypes.c_void_p).value if function is not None else None


def api(name, result, *args):
    address = api_address(name)
    return ctypes.PYFUNCTYPE(result, *args)(address) if address is not None else None


GET_SLOT = api("PyType_GetSlot", ctypes.c_void_p, ctypes.py_object, ctypes.c_int)
IS_SUBTYPE = api("PyType_IsSubtype", ctypes.c_int, ctypes.py_object, ctypes.py_object)
# Return an owned descriptor while the GIL is held. Borrowed raw addresses can
# be invalidated by a class mutation between Python bytecodes; ctypes also
# expects functions with a py_object result to return a new reference.
LOOKUP = api("_PyType_LookupRef", ctypes.py_object, ctypes.py_object, ctypes.py_object)
GENERIC_GETTER = api_address("PyObject_GenericGetAttr")


def inline_index(cls: type, name: str) -> int | None:
    keys = pointer(id(cls) + layout_offset("type_cached_keys"))
    if not keys:
        return None
    kind = ctypes.c_uint8.from_address(keys + layout_offset("keys_kind")).value
    index_bytes = ctypes.c_uint8.from_address(keys + layout_offset("keys_index_bytes")).value
    count = size(keys + layout_offset("keys_nentries"))
    if kind != DICT_KEYS_SPLIT or index_bytes > 6 or not 0 <= count <= SHARED_KEYS_LIMIT:  # noqa: PLR2004
        return None
    entries = keys + layout_offset("keys_indices") + (1 << index_bytes)
    for index in range(count):
        key = pointer(entries + layout_offset("unicode_entry_size") * index)
        if key and ctypes.cast(key, ctypes.py_object).value == name:
            return index
    return None


class Probe:
    value: object
    changed: bool


class SlotProbe:
    __slots__ = ("value",)
    value: object


def member_offset(descriptor, basic_size: int) -> int | None:
    if type(descriptor) is not MemberDescriptorType:
        return None
    member = pointer(id(descriptor) + layout_offset("member_descriptor_member"))
    if not member:
        return None
    member_type = ctypes.c_int.from_address(member + layout_offset("member_type")).value
    member_flags = ctypes.c_int.from_address(member + layout_offset("member_flags")).value
    offset = size(member + layout_offset("member_offset"))
    # Audited members need their getter to emit object.__getattr__. Relative
    # offsets and other extension flags also require the ordinary descriptor.
    if member_flags & ~MEMBER_READONLY:
        return None
    if (
        member_type not in {T_OBJECT, T_OBJECT_EX}
        or not layout_offset("object_size") <= offset <= basic_size - ctypes.sizeof(ctypes.c_void_p)
    ):
        return None
    return offset if offset % 8 == 0 else None


def dictionary_attributes_supported(cls, names):
    flags = ctypes.c_ulong.from_address(id(cls) + LAYOUT.type_flags).value
    if flags & (MANAGED_DICT | HEAP_TYPE) != (MANAGED_DICT | HEAP_TYPE):
        return False
    for name in names:
        try:
            descriptor = LOOKUP(cls, name)
        except ValueError:
            descriptor = None
        if descriptor is not None:
            descriptor_flags = ctypes.c_ulong.from_address(id(type(descriptor)) + LAYOUT.type_flags).value
            if not descriptor_flags & IMMUTABLE_TYPE or GET_SLOT(type(descriptor), TP_DESCR_SET):
                return False
    return True


@cache
def supports_attribute_cache() -> bool:
    # Called only after the compiler validates the object header and build.
    if (
        LAYOUT is None or LAYOUT.type_cached_keys is None
        or GET_SLOT is None or LOOKUP is None or GENERIC_GETTER is None
    ):
        return False
    probe = Probe()
    probe.value = object()
    basic_size = size(id(Probe) + layout_offset("type_basic_size"))
    flags = ctypes.c_ulong.from_address(id(Probe) + layout_offset("type_flags")).value
    if (
        basic_size != Probe.__basicsize__
        or flags != Probe.__flags__
        or flags & (INLINE_VALUES | MANAGED_DICT) != (INLINE_VALUES | MANAGED_DICT)
        or pointer(id(Probe) + layout_offset("type_getattro")) != GET_SLOT(Probe, TP_GETATTRO)
        or pointer(id(Probe) + layout_offset("type_getattro")) != GENERIC_GETTER
        or ctypes.c_uint8.from_address(id(probe) + basic_size + layout_offset("values_valid")).value != 1
    ):
        return False
    index = inline_index(Probe, "value")
    if index is None or pointer(
        id(probe) + basic_size + layout_offset("values_items") + ctypes.sizeof(ctypes.c_void_p) * index,
    ) != id(probe.value):
        return False
    if not get_type_version(Probe):
        return False
    Probe.changed = True
    if get_type_version(Probe):
        return False
    slot_probe = SlotProbe()
    slot_probe.value = object()
    offset = member_offset(SlotProbe.__dict__["value"], SlotProbe.__basicsize__)
    return offset is not None and pointer(id(slot_probe) + offset) == id(slot_probe.value)


def dictionary_entry(data: dict, name: str) -> tuple[int, str] | None:
    if pointer(id(data) + layout_offset("dict_values")):
        return None
    keys = pointer(id(data) + layout_offset("dict_keys"))
    if ctypes.c_uint8.from_address(keys + layout_offset("keys_kind")).value != DICT_KEYS_UNICODE:
        return None
    index_bytes = ctypes.c_uint8.from_address(keys + layout_offset("keys_index_bytes")).value
    entries = keys + layout_offset("keys_indices") + (1 << index_bytes)
    for index in range(size(keys + layout_offset("keys_nentries"))):
        key_pointer = pointer(entries + layout_offset("unicode_entry_size") * index)
        if key_pointer:
            key = ctypes.cast(key_pointer, ctypes.py_object).value
            if type(key) is str and key == name:
                return index, key
    return None


@cache
def supports_dictionary_cache() -> bool:
    if LAYOUT is None or LAYOUT.type_cached_keys is None:
        return False
    data = {"first": object(), "second": object()}
    if size(id(data) + layout_offset("dict_used")) != len(data) or pointer(id(data) + layout_offset("dict_values")):
        return False
    keys = pointer(id(data) + layout_offset("dict_keys"))
    if not keys or ctypes.c_uint8.from_address(keys + layout_offset("keys_kind")).value != DICT_KEYS_UNICODE:
        return False
    for name, value in data.items():
        entry = dictionary_entry(data, name)
        if entry is None:
            return False
        index, key = entry
        entries = keys + layout_offset("keys_indices") + (
            1 << ctypes.c_uint8.from_address(keys + layout_offset("keys_index_bytes")).value
        )
        if key is not name or pointer(
            entries + layout_offset("unicode_entry_size") * index + layout_offset("unicode_entry_value"),
        ) != id(value):
            return False
    ascii_probe = bytearray(b"native_key").decode()
    return (
        size(id(ascii_probe) + layout_offset("unicode_length")) == len(ascii_probe)
        and (
            ctypes.c_uint32.from_address(id(ascii_probe) + layout_offset("unicode_state")).value
            & COMPACT_ASCII == COMPACT_ASCII
        )
        and ctypes.string_at(id(ascii_probe) + layout_offset("unicode_ascii_data"), len(ascii_probe))
        == ascii_probe.encode("ascii")
    )


class DictionaryCache(ctypes.Structure):
    _fields_ = [
        ("key_pointer", ctypes.c_void_p), ("index", ctypes.c_ssize_t),
        ("ready", ctypes.c_uint32), ("misses", ctypes.c_uint32),
    ]

    def __init__(self, name: str):
        super().__init__()
        self.name = name
        self.key_owner: str | None = None
        self.update_lock = RLock()

    def __call__(self, data: dict):
        value = data[self.name]
        # A private copy keeps its keys table alive across Python bytecodes.
        # The input can be resized by another thread during training. A copy
        # may compact deleted entries; the machine-code identity guard checks
        # the learned index against the actual input on every subsequent call.
        entry = dictionary_entry(data.copy(), self.name)
        with self.update_lock:
            self.misses += 1
            if entry is not None:
                index, key = entry
                self.ready = 0
                self.key_owner = key
                self.key_pointer = id(key)
                self.index = index
                self.ready = 1
        return value


class AttributeCache(ctypes.Structure):
    _fields_ = [
        ("type_pointer", ctypes.c_void_p),
        ("version", ctypes.c_uint32),
        ("kind", ctypes.c_uint32),
        ("offset", ctypes.c_ssize_t),
        ("valid_offset", ctypes.c_ssize_t),
        ("misses", ctypes.c_uint32),
    ]

    def __init__(self, name: str):
        super().__init__()
        self.name = name
        self.type_owner: type | None = None
        self.update_lock = RLock()

    def __call__(self, data):
        value = getattr(data, self.name)
        cls = type(data)
        version = get_type_version(cls)
        state = self.specialize(cls, version) if pointer(id(cls) + LAYOUT.type_getattro) == GENERIC_GETTER else None
        # Keep the previous class alive until the update is complete. Its
        # finalizer can reenter the generated function and replace this cache.
        # Readers take no lock: GENERIC disables the fast path throughout
        # publication. Serialize writers, which can switch threads in Python.
        with self.update_lock:
            previous_type = self.type_owner
            self.kind = GENERIC
            self.misses += 1
            self.type_owner = cls
            self.type_pointer = id(cls)
            self.version = version
            if state is not None:
                version, offset, valid_offset, kind = state
                self.offset = offset
                self.valid_offset = valid_offset
                self.kind = kind
        del previous_type
        return value

    def specialize(self, cls: type, version: int) -> tuple[int, int, int, int] | None:
        # Capture the version before examining descriptors or shared keys.
        # A class mutation during training then invalidates this entire entry.
        if not version:
            return None
        try:
            descriptor = LOOKUP(cls, self.name)
        except ValueError:  # ctypes reports a NULL py_object for absent attributes.
            descriptor = None
        basic_size = size(id(cls) + layout_offset("type_basic_size"))
        offset = member_offset(descriptor, basic_size)
        if offset is not None and IS_SUBTYPE(cls, descriptor.__objclass__):
            return version, offset, 0, SLOT
        if descriptor is not None:
            # A mutable descriptor's type can become a data descriptor without
            # invalidating the model type. Never cache that instance lookup.
            flags = ctypes.c_ulong.from_address(id(type(descriptor)) + layout_offset("type_flags")).value
            if not flags & IMMUTABLE_TYPE or GET_SLOT(type(descriptor), TP_DESCR_SET):
                return None
        flags = ctypes.c_ulong.from_address(id(cls) + layout_offset("type_flags")).value
        if (
            flags & (INLINE_VALUES | MANAGED_DICT | HEAP_TYPE) != (INLINE_VALUES | MANAGED_DICT | HEAP_TYPE)
            or (sys.version_info < (3, 14) and basic_size != layout_offset("object_size"))
        ):
            return None
        index = inline_index(cls, self.name)
        if index is not None:
            return (
                version,
                basic_size + layout_offset("values_items") + ctypes.sizeof(ctypes.c_void_p) * index,
                basic_size + layout_offset("values_valid"),
                INLINE,
            )
        return None


class AttributeBatchCache(ctypes.Structure):
    """One type/version check for a run of ordinary instance attributes."""

    _fields_ = [
        ("type_pointer", ctypes.c_void_p), ("version", ctypes.c_uint32),
        ("kind", ctypes.c_uint32), ("valid_offset", ctypes.c_ssize_t),
        ("offsets_pointer", ctypes.c_void_p), ("misses", ctypes.c_uint32),
    ]

    def __init__(self, names: tuple[str, ...]):
        super().__init__()
        self.names = names
        self.offsets = (ctypes.c_ssize_t * len(names))()
        self.offsets_pointer = ctypes.addressof(self.offsets)
        self.type_owner: type | None = None
        self.update_lock = RLock()

    def __call__(self, data):
        cls = type(data)
        # Attribute lookup assigns a type version even when the attribute only
        # exists in instance storage. Never invoke user getters while training.
        with suppress(ValueError):
            LOOKUP(cls, self.names[0])
        version = get_type_version(cls)
        states = (
            [AttributeCache(name).specialize(cls, version) for name in self.names]
            if pointer(id(cls) + LAYOUT.type_getattro) == GENERIC_GETTER else []
        )
        supported = bool(states) and all(state is not None for state in states)
        dictionary = (
            not supported and pointer(id(cls) + LAYOUT.type_getattro) == GENERIC_GETTER
            and dictionary_attributes_supported(cls, self.names)
        )
        with self.update_lock:
            previous_type = self.type_owner
            self.kind = GENERIC
            self.misses += 1
            self.type_owner = cls
            self.type_pointer = id(cls)
            self.version = version
            if supported:
                self.valid_offset = 0
                for index, state in enumerate(states):
                    if state is None:
                        raise AssertionError
                    _, offset, valid_offset, _ = state
                    self.offsets[index] = offset
                    if valid_offset:
                        self.valid_offset = valid_offset
                self.kind = INLINE if self.valid_offset else SLOT
            elif dictionary:
                self.kind = DICT
        del previous_type


class DictionaryBatchCache(ctypes.Structure):
    _fields_ = [
        ("ready", ctypes.c_uint32), ("misses", ctypes.c_uint32), ("max_index", ctypes.c_ssize_t),
        ("indices_pointer", ctypes.c_void_p), ("keys_pointer", ctypes.c_void_p),
    ]

    def __init__(self, names: tuple[str, ...]):
        super().__init__()
        self.names = names
        self.indices = (ctypes.c_ssize_t * len(names))()
        self.keys = (ctypes.c_void_p * len(names))()
        self.indices_pointer = ctypes.addressof(self.indices)
        self.keys_pointer = ctypes.addressof(self.keys)
        self.key_owners: tuple[str, ...] = ()
        self.update_lock = RLock()

    def __call__(self, data):
        snapshot = data.copy()
        entries = [dictionary_entry(snapshot, name) for name in self.names]
        with self.update_lock:
            self.misses += 1
            if not all(entry is not None for entry in entries):
                return
            self.ready = 0
            self.key_owners = tuple(entry[1] for entry in entries if entry is not None)
            self.max_index = max(entry[0] for entry in entries if entry is not None)
            for index, entry in enumerate(entries):
                if entry is None:
                    raise AssertionError
                position, key = entry
                self.indices[index] = position
                self.keys[index] = id(key)
            self.ready = 1
