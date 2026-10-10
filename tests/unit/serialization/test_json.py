import ctypes
import gc
import json
import math
import random
import sys
from dataclasses import dataclass, field

import pytest

from adaptix import CodeGenBackend, Retort, dumper, loader, name_mapping
from adaptix._internal.code_tools.native_callable import ExecutableMemory
from adaptix._internal.code_tools.x86_64_assembler import Immediate, X86Assembler
from adaptix._internal.code_tools.x86_64_compiler import X86Compiler, c_function_address, check_native_platform
from adaptix._internal.morphing.native.x86_64.generator import X86CodeGenerator
from adaptix._internal.serialization.json import StdlibJsonCodec
from adaptix._internal.serialization.x86_64.codec import X86JsonCodec
from adaptix.json import JsonRetort


@pytest.fixture(params=[CodeGenBackend.PYTHON, CodeGenBackend.X86_64])
def backend(request):
    if request.param is CodeGenBackend.X86_64:
        try:
            check_native_platform()
        except RuntimeError as error:
            pytest.skip(str(error))
    return request.param


@pytest.fixture
def codec(backend):
    return JsonRetort(Retort(codegen_backend=backend)).codec


@pytest.mark.parametrize(
    "value",
    [
        None,
        True,
        False,
        0,
        -1,
        12345,
        2**63 - 1,
        -(2**63),
        2**128,
        -0.0,
        1.25,
        1e-120,
        1e100,
        "",
        "ascii",
        "кириллица é 😀",
        'quote" slash\\ controls\n\t\0',
        [],
        {},
        [1, "x", None],
        {"nested": [{"x": 1}, [2, 3]]},
        list(range(1000)),
        {f"field_{index}": index for index in range(128)},
    ],
)
@pytest.mark.parametrize("input_type", [str, bytes, bytearray])
def test_json_roundtrip(codec, value, input_type):
    source = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    data = source if input_type is str else input_type(source.encode())
    decode = codec.make_decoder(["nested", "x"] + [f"field_{index}" for index in range(128)])
    assert decode(data) == value
    assert decode(data=data) == value
    assert codec.encode(value) == source.encode()
    assert codec.encode_str(value) == source


@pytest.mark.parametrize(
    "source",
    [
        "",
        " ",
        "[",
        "{",
        "01",
        "-01",
        "+1",
        ".5",
        "1.",
        "1e",
        "1e+",
        "1 2",
        "trueX",
        "[1,]",
        "[1 2]",
        '{"a":}',
        '{"a" 1}',
        '{"a":1,}',
        "{1:2}",
        '"unterminated',
        '"bad\\x"',
        '"bad\\u123z"',
        '"bad\n"',
        "[null false]",
        "[1]x",
        '{"nested":[1,]}',
    ],
)
def test_invalid_json_preserves_document_and_error_position(codec, source):
    reference = StdlibJsonCodec().make_decoder()
    with pytest.raises(json.JSONDecodeError) as expected:
        reference(source)
    with pytest.raises(json.JSONDecodeError) as actual:
        codec.make_decoder(["nested"])(source)
    assert (actual.value.doc, actual.value.pos, actual.value.msg) == (
        expected.value.doc,
        expected.value.pos,
        expected.value.msg,
    )


@pytest.mark.parametrize("source", [b"NaN", b"Infinity", b"-Infinity", b"[NaN]"])
def test_reject_non_json_constants(codec, source):
    with pytest.raises(ValueError, match="Invalid JSON constant"):
        codec.make_decoder()(source)


@pytest.mark.parametrize("value", [float("nan"), float("inf"), -float("inf"), {"x": float("nan")}])
def test_reject_non_finite_output(codec, value):
    with pytest.raises(ValueError, match="Out of range float values"):
        codec.encode(value)
    with pytest.raises(ValueError, match="Out of range float values"):
        codec.encode_str(value)


@pytest.mark.parametrize("encoding", ["utf-8-sig", "utf-16", "utf-32", "utf-16-le", "utf-32-be"])
def test_input_encodings(codec, encoding):
    value = {"name": "пример", "values": [1, 2]}
    assert codec.make_decoder()(json.dumps(value).encode(encoding)) == value


def test_duplicate_and_escaped_keys(codec):
    assert codec.make_decoder(["name"])(b'{"name":1,"na\\u006de":2}') == {"name": 2}


def test_lone_surrogate_and_invalid_utf8(codec):
    decode = codec.make_decoder()
    assert decode(b'"\\ud800"') == "\ud800"
    assert decode('"\ud800"') == "\ud800"
    assert codec.encode_str("\ud800") == '"\ud800"'
    with pytest.raises(UnicodeEncodeError):
        codec.encode("\ud800")
    with pytest.raises(UnicodeDecodeError):
        decode(b'"\xff"')


def test_generated_data_matches_reference(codec):
    randomizer = random.Random(2026)  # noqa: S311
    atoms = [None, True, False, "a", "é", "😀", 'x"\\\0', -(2**63), 2**80, 1.5]

    def value(depth):
        if depth == 0 or randomizer.randrange(3) == 0:
            return randomizer.choice([*atoms, randomizer.randrange(-100000, 100000)])
        if randomizer.randrange(2):
            return [value(depth - 1) for _ in range(randomizer.randrange(8))]
        return {f"field_{index}": value(depth - 1) for index in range(randomizer.randrange(8))}

    decode = codec.make_decoder([f"field_{index}" for index in range(8)])
    for _ in range(300):
        item = value(4)
        text = json.dumps(item, ensure_ascii=False, separators=(",", ":"))
        assert decode(text) == item
        assert codec.encode(item) == text.encode()


def test_cycles_and_recursion_do_not_leak_the_recursion_guard(codec):
    decode = codec.make_decoder()
    cyclic = []
    cyclic.append(cyclic)
    for _ in range(3):
        with pytest.raises(ValueError, match="Circular"):
            codec.encode(cyclic)
        depth = sys.getrecursionlimit() + 100
        source = "[" * depth + "0" + "]" * depth
        try:
            StdlibJsonCodec().make_decoder()(source)
        except RecursionError:
            with pytest.raises(RecursionError):
                decode(source)
        else:
            decoded = decode(source)
            for _ in range(depth):
                assert len(decoded) == 1
                decoded = decoded[0]
            assert decoded == 0
        assert decode('[1,{"x":2}]') == [1, {"x": 2}]
        assert codec.encode([1, {"x": 2}]) == b'[1,{"x":2}]'


def test_stdlib_supported_fallback_values(codec):
    assert codec.encode((1, 2)) == b"[1,2]"
    assert codec.encode({1: "a", None: "b"}) == b'{"1":"a","null":"b"}'
    with pytest.raises(TypeError):
        codec.encode(object())
    with pytest.raises(TypeError):
        codec.make_decoder()(123)


@dataclass
class Child:
    value: int


@dataclass
class Model:
    name: str
    children: list[Child]
    default: int = 42
    tags: list[str] = field(default_factory=list)


def test_facade_recipes_defaults_cache_and_input_types(backend):
    retort = Retort(codegen_backend=backend, recipe=[name_mapping(Model, map={"name": "label"})])
    facade = JsonRetort(retort)
    load, dump = facade.get_loader(Model), facade.get_dumper(Model)
    assert load is facade.get_loader(Model)
    assert dump is facade.get_dumper(Model)
    expected = Model("пример", [Child(10)])
    source = '{"label":"пример","children":[{"value":10}],"unknown":12}'
    for data in (source, source.encode(), bytearray(source.encode())):
        assert facade.load(data, Model) == expected
    serialized = {"label": "пример", "children": [{"value": 10}], "default": 42, "tags": []}
    assert json.loads(dump(expected)) == serialized
    assert json.loads(facade.dump(expected, Model, as_bytes=False)) == serialized
    assert json.loads(facade.dump(expected)) == serialized
    assert isinstance(facade.get_dumper(Model, as_bytes=False)(expected), str)
    assert load(b'{"label":"one","children":[]}').tags is not load(b'{"label":"two","children":[]}').tags


def test_custom_converters_are_called_once(backend):
    calls = []

    def load(value):
        calls.append("load")
        return int(value)

    def dump(value):
        calls.append("dump")
        return str(value)

    facade = JsonRetort(Retort(codegen_backend=backend, recipe=[loader(int, load), dumper(int, dump)]))
    assert facade.load(b'"123"', int) == 123
    assert facade.dump(123, int) == b'"123"'
    assert calls == ["load", "dump"]


def test_native_compiler_injection_and_known_key_identity(backend):
    if backend is CodeGenBackend.PYTHON:
        pytest.skip("Native compiler injection")
    created = []

    def make_compiler(name):
        created.append(name)
        return X86Compiler(name)

    codec = X86CodeGenerator(compiler_factory=make_compiler).make_json_codec()
    assert isinstance(codec, X86JsonCodec)
    name = "known_field_" + "x" * 40
    decode = codec.make_decoder([name])
    assert decode is codec.make_decoder([name])
    assert next(iter(decode(json.dumps({name: 1})))) is name
    gc.collect()
    assert decode(b'{"unknown":1}') == {"unknown": 1}
    assert codec.encode({name: 2}) == json.dumps({name: 2}, separators=(",", ":")).encode()
    assert {"json_read_value", "json_decode", "json_write_value", "json_encode_bytes"} <= set(created)


def test_extra_fields_and_nested_mapping(backend):
    from adaptix import ExtraForbid
    from adaptix.load_error import AggregateLoadError

    retort = Retort(codegen_backend=backend, recipe=[
        name_mapping(Model, map={"name": ("meta", "label")}, extra_in=ExtraForbid(), omit_default=True),
    ])
    facade = JsonRetort(retort)
    expected = Model("sample", [Child(10)])
    source = b'{"meta":{"label":"sample"},"children":[{"value":10}]}'
    assert facade.load(source, Model) == expected
    assert json.loads(facade.dump(expected, Model)) == {"meta": {"label": "sample"}, "children": [{"value": 10}]}
    with pytest.raises(AggregateLoadError):
        facade.load(b'{"meta":{"label":"sample"},"children":[],"unknown":1}', Model)
    with pytest.raises(AggregateLoadError):
        facade.load(b'{"meta":{"label":1},"children":[]}', Model)


def test_invalid_document_does_not_invoke_custom_loader(backend):
    calls = []

    def convert(value):
        calls.append(value)
        return int(value)

    facade = JsonRetort(Retort(codegen_backend=backend, recipe=[loader(int, convert)]))
    with pytest.raises(json.JSONDecodeError):
        facade.load(b'"123" trailing', int)
    assert calls == []


def test_native_optional_fast_paths_can_be_disabled(backend, monkeypatch):
    if backend is CodeGenBackend.PYTHON:
        pytest.skip("Native object header validation")
    monkeypatch.setattr("adaptix._internal.code_tools.x86_64_compiler.inline_refcount_mode", lambda: None)
    codec = X86JsonCodec(compiler_factory=X86Compiler)
    assert codec.make_decoder(["x"])(b'{"x":[1,2.0]}') == {"x": [1, 2.0]}
    assert codec.encode({"x": [1, 2.0]}) == b'{"x":[1,2.0]}'


def test_portable_facade_does_not_require_x86(monkeypatch):
    monkeypatch.setattr("adaptix._internal.code_tools.x86_64_compiler.platform.machine", lambda: "aarch64")
    facade = JsonRetort()
    assert facade.load(b"123", int) == 123
    assert facade.dump(123, int) == b"123"


def test_generated_converters_outlive_facade(backend):
    facade = JsonRetort(Retort(codegen_backend=backend))
    load, dump = facade.get_loader(Model), facade.get_dumper(Model)
    del facade
    gc.collect()
    data = b'{"name":"sample","children":[{"value":10}]}'
    for _ in range(20):
        assert load(data) == Model("sample", [Child(10)])
        assert json.loads(dump(load(data))) == {
            "name": "sample", "children": [{"value": 10}], "default": 42, "tags": [],
        }


@dataclass
class FlatModel:
    count: int
    label: str
    rating: float = 0.0


@pytest.mark.parametrize("source", [
    b'{"label":"x","count":1}',
    b'{"count":"wrong","count":2,"label":"x"}',
    b'{"count":2,"la\\u0062el":"x","rating":1}',
    b'{"unused":{"nested":[1,2]},"count":2,"label":"x"}',
])
def test_flat_model_loading_matches_object_backend(backend, source):
    retort = Retort(codegen_backend=backend)
    assert JsonRetort(retort).load(source, FlatModel) == retort.load(json.loads(source), FlatModel)


@pytest.mark.parametrize("source", [
    b'{"label":"x"}',
    b'{"count":true,"label":"x"}',
    b'{"count":1,"label":null}',
    b'{"count":1,"label":"x","rating":{}}',
])
def test_flat_model_type_errors_preserve_trails(backend, source):
    from adaptix.load_error import AggregateLoadError

    retort = Retort(codegen_backend=backend)
    with pytest.raises(AggregateLoadError) as expected:
        retort.load(json.loads(source), FlatModel)
    with pytest.raises(AggregateLoadError) as actual:
        JsonRetort(retort).load(source, FlatModel)
    assert str(actual.value) == str(expected.value)
    assert [str(error) for error in actual.value.exceptions] == [str(error) for error in expected.value.exceptions]
    assert [getattr(error, "__notes__", []) for error in actual.value.exceptions] == [
        getattr(error, "__notes__", []) for error in expected.value.exceptions
    ]


def test_model_constructor_runs_once_after_document_validation(backend):
    calls = []

    @dataclass
    class WithHook:
        value: int

        def __post_init__(self):
            calls.append(self.value)
            if self.value == 2:
                raise ValueError("constructor failed")

    facade = JsonRetort(Retort(codegen_backend=backend))
    for source in (b'{"value":1} trailing', b'{"value":1,}', b'{"value":1,"bad":[1,]}'):
        with pytest.raises(json.JSONDecodeError):
            facade.load(source, WithHook)
    assert calls == []
    assert facade.load(b'{"value":1}', WithHook).value == 1
    with pytest.raises(ValueError, match="constructor failed"):
        facade.load(b'{"value":2}', WithHook)
    assert calls == [1, 2]


def test_changed_model_descriptor_is_read_once(backend, monkeypatch):
    calls = []
    model = FlatModel(1, "x")
    facade = JsonRetort(Retort(codegen_backend=backend))
    dump = facade.get_dumper(FlatModel)
    assert json.loads(dump(model)) == {"count": 1, "label": "x", "rating": 0.0}

    def read_label(instance):
        calls.append(instance)
        return "changed"

    monkeypatch.setattr(FlatModel, "label", property(read_label), raising=False)
    assert json.loads(dump(model)) == {"count": 1, "label": "changed", "rating": 0.0}
    assert calls == [model]


def test_model_custom_field_dumper_runs_once_on_fallback(backend):
    calls = []

    def dump(value):
        calls.append(value)
        return value

    facade = JsonRetort(Retort(codegen_backend=backend, recipe=[dumper(str, dump)]))
    model = FlatModel(2**128, "x")
    assert json.loads(facade.dump(model, FlatModel)) == {"count": 2**128, "label": "x", "rating": 0.0}
    assert calls == ["x"]


@pytest.mark.parametrize("length", [15, 16, 17, 31, 32, 33, 255, 256, 257, 4096])
def test_escaped_string_vector_boundaries_and_output_ownership(codec, length):
    value = "x" * length + "".join(map(chr, range(32))) + '\\"é😀' + "x" * length
    expected = json.dumps(value, ensure_ascii=False).encode()
    encoded = codec.encode(value)
    assert encoded == expected
    assert codec.make_decoder()(encoded) == value
    for later in ("", "longer" * 10000, value):
        codec.encode(later)
    gc.collect()
    assert encoded == expected


def test_float_extremes_and_negative_zero(codec):
    values = [0.0, -0.0, 5e-324, sys.float_info.min, sys.float_info.max, -sys.float_info.max, 1e-7, 1e20]
    expected = json.dumps(values, separators=(",", ":")).encode()
    assert codec.encode(values) == expected
    assert codec.make_decoder()(expected) == values
    assert codec.encode(codec.make_decoder()(expected)) == expected
    assert codec.make_decoder()(b"1e9999") == float("inf")


def test_short_decimal_floats_and_their_neighbors(codec):
    values = []
    for integer in (-10000001, -9999999, -100001, -10001, -101, -10, -1, 0, 1, 10, 101, 10001, 100001, 9999999, 10000001):
        value = integer / 10
        values.extend((value, math.nextafter(value, -math.inf), math.nextafter(value, math.inf)))
    expected = json.dumps(values, separators=(",", ":")).encode()
    assert codec.encode(values) == expected
    assert codec.make_decoder()(expected) == values


def test_native_buffer_resize_failure_releases_its_owner(backend, monkeypatch):
    if backend is CodeGenBackend.PYTHON:
        pytest.skip("Native buffer ownership")
    original_address = c_function_address
    assembler = X86Assembler()
    assembler.emit(b"\xf3\x0f\x1e\xfa", "endbr64")
    assembler.mov_imm(6, (1 << 63) - 1)
    assembler.mov_imm(0, original_address("_PyBytes_Resize").value)
    assembler.emit(b"\xff\xe0", "jmp rax  # request an impossible allocation")
    failure = ExecutableMemory(bytes(assembler.code))

    def address(name):
        return Immediate(failure.address) if name == "_PyBytes_Resize" else original_address(name)

    monkeypatch.setattr("adaptix._internal.code_tools.x86_64_compiler.c_function_address", address)
    codec = X86JsonCodec(compiler_factory=X86Compiler)
    for _ in range(3):
        with pytest.raises(MemoryError):
            codec.encode("long value" * 1000)
        assert codec.encode("short") == b'"short"'


def test_native_float_formatter_can_be_disabled(backend):
    if backend is CodeGenBackend.PYTHON:
        pytest.skip("Native float formatting")
    codec = X86JsonCodec(compiler_factory=X86Compiler, float_formatter_factory=lambda: None)
    values = [4.6, -0.0, 1.0000000000000002, 5e-324, sys.float_info.max]
    assert codec.encode(values) == json.dumps(values, separators=(",", ":")).encode()


def test_decimal_fast_path_respects_float_rounding_mode(codec):
    library = ctypes.CDLL(None)
    if not hasattr(library, "fesetround") or not hasattr(library, "fegetround"):
        pytest.skip("Floating-point environment unavailable")
    if sys.platform != "linux":
        pytest.skip("Linux floating-point environment constants")
    values = [0.1, math.nextafter(0.1, math.inf), 0.3, math.nextafter(0.3, -math.inf), -0.0, 5e-324]
    expected = json.dumps(values, separators=(",", ":")).encode()
    original = library.fegetround()
    try:
        for mode in (0x400, 0x800, 0xC00):
            if library.fesetround(mode) != 0:
                pytest.skip("Floating-point rounding mode unavailable")
            assert codec.encode(values) == expected
    finally:
        library.fesetround(original)
