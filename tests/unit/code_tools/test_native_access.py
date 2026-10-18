import ctypes
import gc
import sys
import weakref
from concurrent.futures import ThreadPoolExecutor
from threading import Event

import pytest

from adaptix._internal.code_tools.x86_64_compiler import X86Compiler, check_native_platform


@pytest.fixture(autouse=True)
def native_platform():
    try:
        check_native_platform()
    except RuntimeError as error:
        pytest.skip(str(error))


def attribute_function(*, fallback=False):
    compiler = X86Compiler("native_attribute")
    if fallback:
        compiler.refcount_mode = None
    result = compiler.get_attr(compiler.data, "value")
    return compiler.finish(result).make_callable()


def item_function(*, key="value", fallback=False):
    compiler = X86Compiler("native_item")
    if fallback:
        compiler.refcount_mode = None
    result = compiler.get_item(compiler.data, key, compiler.dictionary_guard(compiler.data))
    return compiler.finish(result).make_callable()


def row_function(names):
    compiler = X86Compiler("native_dictionary_row")

    def fallback():
        return [compiler.get_item(compiler.data, name, None) for name in names]

    values = compiler.get_items(compiler.data, names, (None,) * len(names), fallback)
    if values is None:
        values = fallback()
    result = compiler.call(lambda *args: args, *values)
    return compiler.finish(result).make_callable()


@pytest.mark.parametrize("count", [0, 1, 5, 32, 85, 86, 255, 1024])
@pytest.mark.parametrize("key", ["value", "a\0b", "a" * 32, "a" * 33, "ключ"])
def test_dictionary_lookup_handles_resizes_deletions_and_reference_ownership(count, key):
    missing, value = object(), object()
    compiler = X86Compiler("dictionary_lookup")
    get = compiler.finish(compiler.dict_lookup(compiler.data, key, missing)).make_callable()
    data = {f"extra_{index}": index for index in range(count)}
    references = sys.getrefcount(missing), sys.getrefcount(value)
    for _ in range(10):
        assert get(data) is missing
        data[key.encode().decode()] = value
        assert get(data) is value
        assert get(dict(reversed(list(data.items())))) is value
        del data[key]
        assert get(data) is missing
        data.clear()
        data.update({f"extra_{index}": index for index in range(count)})
    assert (sys.getrefcount(missing), sys.getrefcount(value)) == references


def test_dictionary_lookup_probes_colliding_and_deleted_buckets():
    key = "lookup_key"
    colliding = [f"key_{index}" for index in range(10000) if hash(f"key_{index}") & 127 == hash(key) & 127][:40]
    assert len(colliding) == 40
    compiler = X86Compiler("colliding_dictionary_lookup")
    get = compiler.finish(compiler.dict_lookup(compiler.data, key, None)).make_callable()
    data = dict.fromkeys(colliding, "other")
    assert get(data) is None
    data[key.encode().decode()] = "found"
    assert get(data) == "found"
    for name in colliding:
        del data[name]
        assert get(data) == "found"
    del data[key]
    assert get(data) is None


def test_dictionary_lookup_falls_back_for_split_and_general_tables():
    class Model:
        pass

    model = Model()
    model.value = object()
    compiler = X86Compiler("fallback_dictionary_lookup")
    get = compiler.finish(compiler.dict_lookup(compiler.data, "value", None)).make_callable()
    assert get(vars(model)) is model.value

    class Key:
        def __hash__(self):
            return hash("value")

        def __eq__(self, other):
            raise ValueError("key comparison failed")

    with pytest.raises(ValueError, match="key comparison failed"):
        get({Key(): 1})


@pytest.mark.parametrize("names", [("first", "second"), ("a\0b", "second"), ("первое", "second"), ("a" * 40, "second")])
def test_dictionary_row_checks_keys_and_handles_deleted_entries(names):
    get_row = row_function(names)
    data = dict(zip(names, (object(), object()), strict=True))
    for _ in range(20):
        assert get_row(data) == tuple(data[name] for name in names)
    fresh = {name.encode().decode(): value for name, value in data.items()}
    assert get_row(fresh) == tuple(data.values())
    assert get_row(dict(reversed(list(data.items())))) == tuple(data.values())
    # Keep the entry count large enough that the cached position remains valid,
    # while the key at that position has become a NULL tombstone.
    data["extra"] = None
    del data[names[0]]
    with pytest.raises(KeyError):
        get_row(data)
    data[names[0]] = object()
    assert get_row(data) == tuple(data[name] for name in names)
    data.clear()
    with pytest.raises(KeyError):
        get_row(data)


def test_dictionary_row_owns_values_and_respects_mapping_overrides():
    get_row = row_function(("first", "second"))
    value = object()
    data = {"first": value, "second": value}
    references = sys.getrefcount(value)
    for _ in range(100):
        result = get_row(data)
        assert result == (value, value)
        del result
    assert sys.getrefcount(value) == references

    class Mapping(dict):
        def __getitem__(self, name):
            return name

    assert get_row(Mapping(data)) == ("first", "second")


@pytest.mark.parametrize("fallback", [False, True])
def test_attribute_cache_handles_mutation_and_dictionary_replacement(fallback):
    class Model:
        value = "default"

    value = Model()
    value.value = object()
    get_attribute = attribute_function(fallback=fallback)
    assert get_attribute(value) is value.value
    value.value = object()
    assert get_attribute(value) is value.value
    del value.value
    assert get_attribute(value) == "default"
    value.value = object()
    assert get_attribute(value) is value.value
    value.__dict__ = {"value": object()}
    assert get_attribute(value) is value.value
    value.__dict__["value"] = object()
    assert get_attribute(value) is value.value
    value.__dict__.clear()
    assert get_attribute(value) == "default"
    del Model.value
    with pytest.raises(AttributeError):
        get_attribute(value)


def test_attribute_cache_invalidates_on_class_and_base_class_changes():
    class Base:
        pass

    class Model(Base):
        pass

    value = Model()
    value.value = object()
    get_attribute = attribute_function()
    assert get_attribute(value) is value.value

    Base.value = property(lambda self: "property")
    assert get_attribute(value) == "property"
    del Base.value
    assert get_attribute(value) is value.value
    Model.__getattribute__ = lambda self, name: "custom" if name == "value" else object.__getattribute__(self, name)
    assert get_attribute(value) == "custom"
    del Model.__getattribute__
    assert get_attribute(value) is value.value


def test_attribute_cache_preserves_mutable_descriptor_precedence():
    class Descriptor:
        def __get__(self, instance, owner):
            return "descriptor"

    class Model:
        value = Descriptor()

    value = Model()
    value.value = "instance"
    get_attribute = attribute_function()
    assert get_attribute(value) == "instance"
    Descriptor.__set__ = lambda self, instance, new_value: None
    assert get_attribute(value) == "descriptor"
    del Descriptor.__set__
    assert get_attribute(value) == "instance"


def test_slot_cache_handles_missing_values_replaced_descriptors_and_inheritance():
    class Base:
        __slots__ = ("value",)

    class Model(Base):
        __slots__ = ("other",)

    value = Model()
    value.value = object()
    get_attribute = attribute_function()
    assert get_attribute(value) is value.value
    del value.value
    with pytest.raises(AttributeError):
        get_attribute(value)
    value.value = object()
    assert get_attribute(value) is value.value
    Model.value = property(lambda self: "property")
    assert get_attribute(value) == "property"
    del Model.value
    assert get_attribute(value) is value.value


def test_slot_cache_excludes_audited_and_relative_members():
    compiler = X86Compiler("native_member_flags")
    if not compiler.has_validated_object_header or sys.version_info[:2] not in {(3, 13), (3, 14), (3, 15)}:
        pytest.skip("Member specialization is unavailable on this interpreter")
    from adaptix._internal.code_tools.native_access import member_offset

    class Model:
        __slots__ = ("value",)

    descriptor = Model.__dict__["value"]
    member_pointer = ctypes.c_void_p.from_address(id(descriptor) + 40).value
    assert member_pointer is not None
    flags = ctypes.c_int.from_address(member_pointer + 24)
    original = flags.value
    offset = member_offset(descriptor, Model.__basicsize__)
    assert offset is not None
    try:
        for flag in (2, 8):  # Py_AUDIT_READ, Py_RELATIVE_OFFSET
            flags.value = flag
            assert member_offset(descriptor, Model.__basicsize__) is None
        flags.value = 1  # Py_READONLY does not affect reading a slot.
        assert member_offset(descriptor, Model.__basicsize__) == offset
    finally:
        flags.value = original


def test_attribute_cache_keeps_current_class_alive_and_releases_it_with_callable():
    Model = type("Model", (), {})
    value = Model()
    value.value = object()
    reference = weakref.ref(Model)
    get_attribute = attribute_function()
    get_attribute(value)
    del value, Model
    gc.collect()
    if any(type(item).__name__ == "AttributeCache" for item in get_attribute.__self__.constants):
        assert reference() is not None
    del get_attribute
    gc.collect()
    assert reference() is None


def test_attribute_cache_cycle_releases_executable_memory():
    class Model:
        pass

    value = Model()
    value.value = object()
    get_attribute = attribute_function()
    get_attribute(value)
    Model.get_attribute = staticmethod(get_attribute)
    memory_reference = weakref.ref(get_attribute.__self__.memory)
    type_reference = weakref.ref(Model)
    del value, Model, get_attribute
    gc.collect()
    assert memory_reference() is None
    assert type_reference() is None


def test_attribute_cache_rechecks_type_version_after_training(monkeypatch):
    get_attribute = attribute_function()
    entries = [item for item in get_attribute.__self__.constants if type(item).__name__ == "AttributeCache"]
    if not entries:
        pytest.skip("Attribute specialization is unavailable on this interpreter")
    entry = entries[0]
    original = entry.specialize

    class Model:
        pass

    value = Model()
    value.value = "instance"

    def specialize(cls, version):
        state = original(cls, version)
        Model.value = property(lambda self: "property")
        return state

    monkeypatch.setattr(entry, "specialize", specialize)
    assert get_attribute(value) == "instance"
    assert get_attribute(value) == "property"


def test_attribute_and_item_caches_return_owned_references():
    class Model:
        pass

    model = Model()
    model.value = object()
    data = {"value": model.value}
    get_attribute, get_item = attribute_function(), item_function()
    get_attribute(model)
    get_item(data)
    before = sys.getrefcount(model.value)
    for _ in range(100):
        get_attribute(model)
        get_item(data)
    after = sys.getrefcount(model.value)
    assert after == before
    result = get_attribute(model)
    del model.value
    data.clear()
    assert result is not None


@pytest.mark.parametrize("fallback", [False, True])
def test_item_cache_handles_reordering_deletion_resize_and_equal_new_keys(fallback):
    get_item = item_function(fallback=fallback)
    cases = [{"value": object(), "other": object()}, {"other": object(), "value": object()}]
    for data in cases * 5:
        assert get_item(data) is data["value"]
    data = cases[0]
    del data["value"]
    with pytest.raises(KeyError, match="value"):
        get_item(data)
    data["value"] = object()
    assert get_item(data) is data["value"]
    data.update({f"key_{index}": object() for index in range(1000)})
    assert get_item(data) is data["value"]
    for index in range(1000):
        del data[f"key_{index}"]
    assert get_item(data) is data["value"]
    data.clear()
    data[bytearray(b"value").decode()] = object()
    assert get_item(data) is data["value"]
    data["value"] = object()
    assert get_item(data) is data["value"]


def test_item_cache_preserves_subclasses_mappings_split_dictionaries_and_custom_keys():
    class Dict(dict):
        def __getitem__(self, key):
            return "subclass"

    class Mapping:
        def __getitem__(self, key):
            return "mapping"

    class Key:
        def __hash__(self):
            return hash("value")

        def __eq__(self, other):
            raise ValueError("custom equality")

    class Model:
        pass

    value = Model()
    value.value = object()
    get_item = item_function()
    assert get_item({"value": 1}) == 1
    assert get_item(Dict(value=1)) == "subclass"
    assert get_item(Mapping()) == "mapping"
    assert get_item(value.__dict__) is value.value
    with pytest.raises(ValueError, match="custom equality"):
        get_item({Key(): 1})
    assert get_item({"value": 2, 42: 3}) == 2


@pytest.mark.parametrize("key", ["", "a", "bb", "four", "value", "abcdefghi", "x" * 31, "x" * 32, "x" * 33,
                                 "ключ", "😁"])
def test_item_cache_compares_equal_new_keys_without_accepting_different_contents(key):
    get_item = item_function(key=key)
    for _ in range(100):
        fresh_key = bytearray(key.encode("utf-8")).decode("utf-8")
        data = {fresh_key: object()}
        assert get_item(data) is data[fresh_key]
    for wrong_key in ("y" * len(key), "я" * len(key), "😀" * len(key), "longer_key"):
        if wrong_key == key:
            continue
        with pytest.raises(KeyError):
            get_item({wrong_key: object()})


def test_cache_training_is_bounded_for_polymorphic_and_changing_layouts():
    get_attribute, get_item = attribute_function(), item_function()
    models = [type(f"Model_{index}", (), {})() for index in range(32)]
    for model in models:
        model.value = object()
    dictionaries = [{**{f"other_{number}": number for number in range(index)}, "value": object()}
                    for index in range(32)]
    for _ in range(5):
        for model in models:
            assert get_attribute(model) is model.value
        for data in dictionaries:
            assert get_item(data) is data["value"]
    for function in (get_attribute, get_item):
        for entry in function.__self__.constants:
            if type(entry).__name__ in {"AttributeCache", "DictionaryCache"}:
                assert entry.misses == 16


def test_attribute_cache_publication_is_coherent_between_threads():
    class First:
        pass

    class Second:
        pass

    first, second = First(), Second()
    first.value = object()
    first.other = object()
    second.other = object()
    second.value = object()
    get_attribute = attribute_function()
    previous_interval = sys.getswitchinterval()

    def read(value):
        expected = value.value
        for _ in range(1000):
            assert get_attribute(value) is expected

    try:
        sys.setswitchinterval(0.000001)
        with ThreadPoolExecutor(max_workers=2) as pool:
            for result in pool.map(read, (first, second)):
                assert result is None
    finally:
        sys.setswitchinterval(previous_interval)


def test_item_cache_training_survives_concurrent_dictionary_resize():
    data = {"value": object()}
    expected = data["value"]
    get_item = item_function()
    started, stopped = Event(), Event()
    previous_interval = sys.getswitchinterval()

    def resize():
        started.set()
        index = 0
        while not stopped.is_set():
            data[f"other_{index}"] = index
            if index % 100 == 0:
                data.clear()
                data["value"] = expected
            index += 1

    try:
        sys.setswitchinterval(0.000001)
        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(resize)
            try:
                assert started.wait(timeout=5)
                for _ in range(1000):
                    try:
                        result = get_item(data)
                    except KeyError:
                        continue  # The other thread can clear between reads.
                    assert result is expected
            finally:
                stopped.set()
            future.result(timeout=5)
    finally:
        sys.setswitchinterval(previous_interval)
