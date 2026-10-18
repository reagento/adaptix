import ctypes
import gc
import sys
import weakref
from dataclasses import dataclass, make_dataclass
from typing import Any

import pytest

from adaptix import CodeGenBackend, Retort
from adaptix._internal.code_tools.cpython_layout.selection import get_cpython_layout
from adaptix._internal.code_tools.native_callable import ExecutableMemory
from adaptix._internal.code_tools.x86_64_assembler import X86Assembler
from adaptix._internal.code_tools.x86_64_compiler import check_native_platform


@pytest.fixture(autouse=True)
def native_platform():
    try:
        check_native_platform()
    except RuntimeError as error:
        pytest.skip(str(error))


def require_native_constructor(function):
    if get_cpython_layout() is None:
        pytest.skip("No layout for this interpreter build")
    from adaptix._internal.code_tools.native_constructor import GET_TSTATE, monitoring_disabled

    if not monitoring_disabled(function, GET_TSTATE()):
        pytest.skip("Native construction is disabled while tracing or monitoring")


@pytest.mark.parametrize("slots", [False, True])
@pytest.mark.parametrize("count", [2, 32])
def test_fresh_storage_and_reference_ownership(slots, count):
    Model = make_dataclass(
        "Model", [("first", Any), ("second", Any), *[(f"field_{index}", Any, None) for index in range(count - 2)]],
        slots=slots,
    )

    function = Retort(codegen_backend=CodeGenBackend.X86_64).get_loader(Model)
    first, second = object(), object()
    data = {"first": first, "second": second}
    references = sys.getrefcount(first), sys.getrefcount(second)
    for _ in range(100):
        result = function(data)
        assert result.first is first
        assert result.second is second
        if not slots:
            assert list(vars(result)) == ["first", "second", *[f"field_{index}" for index in range(count - 2)]]
        del result
    gc.collect()
    assert (sys.getrefcount(first), sys.getrefcount(second)) == references


@pytest.mark.skipif(sys.version_info[:2] not in {(3, 13), (3, 14), (3, 15)}, reason="Direct constructor requires CPython 3.13+")
@pytest.mark.parametrize("slots", [False, True])
@pytest.mark.parametrize("frozen", [False, True])
def test_plain_initializers_use_native_construction(slots, frozen):
    @dataclass(slots=slots, frozen=frozen)
    class Model:
        value: int

    require_native_constructor(Model.__init__)
    from adaptix._internal.code_tools.native_constructor import SimpleConstructorCache

    load = Retort(codegen_backend=CodeGenBackend.X86_64).get_loader(Model)
    for _ in range(20):
        assert load({"value": 1}) == Model(1)
    caches = [item for item in load.__self__.constants if isinstance(item, SimpleConstructorCache)]
    assert caches
    assert any(cache.kind for cache in caches)


@pytest.mark.parametrize("replace_code", [False, True])
def test_initializer_changes_after_warming(replace_code):
    @dataclass
    class Model:
        value: int

    function = Retort(codegen_backend=CodeGenBackend.X86_64).get_loader(Model)
    for _ in range(20):
        assert function({"value": 1}).value == 1

    def changed(self, value):
        self.value = value + 100

    if replace_code:
        Model.__init__.__code__ = changed.__code__
    else:
        Model.__init__ = changed
    for _ in range(20):
        assert function({"value": 1}).value == 101


def test_custom_setter_added_after_warming():
    @dataclass
    class Model:
        value: int

    function = Retort(codegen_backend=CodeGenBackend.X86_64).get_loader(Model)
    for _ in range(20):
        function({"value": 1})
    seen = []

    def setter(self, name, value):
        seen.append((name, value))
        object.__setattr__(self, name, value * 2)

    Model.__setattr__ = setter
    for _ in range(20):
        assert function({"value": 3}).value == 6
    assert seen == [("value", 3)] * 20


@pytest.mark.parametrize("profiling", [False, True])
def test_tracing_enabled_after_warming_observes_initializer(profiling):
    @dataclass
    class Model:
        value: int

    function = Retort(codegen_backend=CodeGenBackend.X86_64).get_loader(Model)
    for _ in range(20):
        function({"value": 1})
    seen = []

    def observe(frame, event, arg):
        if frame.f_code is Model.__init__.__code__ and event == "call":
            seen.append(frame.f_locals["value"])
        return observe

    setter = sys.setprofile if profiling else sys.settrace
    getter = sys.getprofile if profiling else sys.gettrace
    previous = getter()
    setter(observe)
    try:
        for value in range(3):
            assert function({"value": value}).value == value
    finally:
        setter(previous)
    assert seen == [0, 1, 2]


def test_constructor_side_effects_are_never_skipped():
    seen = []

    @dataclass
    class Model:
        value: int

        def __post_init__(self):
            seen.append(self.value)

    function = Retort(codegen_backend=CodeGenBackend.X86_64).get_loader(Model)
    for value in range(30):
        assert function({"value": value}).value == value
    assert seen == list(range(30))


@pytest.mark.skipif(sys.version_info[:2] not in {(3, 13), (3, 14), (3, 15)}, reason="Direct constructor requires CPython 3.13+")
def test_custom_frame_evaluator_enabled_after_warming_executes_initializer():
    @dataclass
    class Model:
        value: int

    require_native_constructor(Model.__init__)
    from adaptix._internal.code_tools.native_constructor import DEFAULT_EVAL, GET_EVAL, GET_TSTATE, LAYOUT, pointer

    function = Retort(codegen_backend=CodeGenBackend.X86_64).get_loader(Model)
    for _ in range(20):
        function({"value": 1})
    interpreter = pointer(GET_TSTATE() + LAYOUT.thread_interpreter)
    original = GET_EVAL(interpreter)
    address = ctypes.cast(ctypes.pythonapi._PyInterpreterState_SetEvalFrameFunc, ctypes.c_void_p).value
    assert address is not None
    set_evaluator = ctypes.PYFUNCTYPE(None, ctypes.c_void_p, ctypes.c_void_p)(address)
    frames = ctypes.c_uint64()
    asm = X86Assembler()
    asm.emit(b"\xf3\x0f\x1e\xfa", "endbr64")
    asm.mov_imm(11, ctypes.addressof(frames))
    asm.emit(b"\x49\xff\x03", "inc QWORD PTR [r11]  # count evaluated frames")
    asm.mov_imm(11, DEFAULT_EVAL)
    asm.emit(b"\x41\xff\xe3", "jmp r11  # preserve evaluator arguments")
    memory = ExecutableMemory(asm.finish())
    set_evaluator(interpreter, memory.address)
    try:
        before = frames.value
        result = function({"value": 3})
        after = frames.value
    finally:
        set_evaluator(interpreter, original)
    assert result.value == 3
    assert after - before == 1


@pytest.mark.parametrize("count", [1, 32])
def test_initialized_models_participate_in_cyclic_gc(count):
    Model = make_dataclass("Model", [("value", Any), *[(f"field_{index}", Any, None) for index in range(count - 1)]])

    function = Retort(codegen_backend=CodeGenBackend.X86_64).get_loader(Model)
    for _ in range(20):
        function({"value": None})
    data = []
    result = function({"value": data})
    reference = weakref.ref(result)
    data.append(result)
    del result, data
    gc.collect()
    assert reference() is None


@pytest.mark.skipif(sys.version_info[:2] not in {(3, 13), (3, 14), (3, 15)}, reason="Direct constructor requires CPython 3.13+")
def test_cache_publication_retains_the_code_that_was_validated(monkeypatch):
    from adaptix._internal.code_tools import native_constructor

    @dataclass
    class Model:
        value: int

    function = Retort(codegen_backend=CodeGenBackend.X86_64).get_loader(Model)
    original = native_constructor.initializer_fields

    def changed(self, value):
        self.value = value + 100

    def inspect_and_change(initializer, parameters, code=None):
        fields = original(initializer, parameters, code)
        initializer.__code__ = changed.__code__
        return fields

    monkeypatch.setattr(native_constructor, "initializer_fields", inspect_and_change)
    assert function({"value": 1}).value == 1
    for _ in range(30):
        assert function({"value": 1}).value == 101


@pytest.mark.skipif(sys.version_info < (3, 12), reason="sys.monitoring requires Python 3.12")
def test_monitoring_enabled_after_warming_observes_initializer():
    @dataclass
    class Model:
        value: int

    function = Retort(codegen_backend=CodeGenBackend.X86_64).get_loader(Model)
    for _ in range(20):
        function({"value": 1})
    monitoring = sys.monitoring
    tool = next((tool for tool in range(6) if monitoring.get_tool(tool) is None), None)
    if tool is None:
        pytest.skip("No free monitoring tool")
    seen = []

    def observe(code, offset):
        if code is Model.__init__.__code__:
            seen.append(code)

    monitoring.use_tool_id(tool, "adaptix-constructor-test")
    monitoring.register_callback(tool, monitoring.events.PY_START, observe)
    monitoring.set_events(tool, monitoring.events.PY_START)
    try:
        assert function({"value": 2}).value == 2
    finally:
        monitoring.set_events(tool, 0)
        monitoring.register_callback(tool, monitoring.events.PY_START, None)
        monitoring.free_tool_id(tool)
    assert seen == [Model.__init__.__code__]


@pytest.mark.parametrize("count", [30, 31, 32, 128, 255])
def test_wide_initializer_bytecode_and_code_mutation(count):
    cls = make_dataclass("Wide", [(f"field_{index}", int) for index in range(count)])
    data = {f"field_{index}": 1000 + index for index in range(count)}
    function = Retort(codegen_backend=CodeGenBackend.X86_64).get_loader(cls)
    for _ in range(20):
        value = function(data)
        assert vars(value) == data
        assert [getattr(value, name) for name in data] == list(data.values())
    seen = []

    def changed(self, *args):
        seen.append(args)
        self.__dict__.update(dict(zip(data, args, strict=True)))

    cls.__init__ = changed
    assert vars(function(data)) == data
    assert seen == [tuple(data.values())]


@pytest.mark.parametrize("slots", [False, True])
def test_frozen_setter_closure_mutation_after_warming(slots):
    @dataclass(frozen=True, slots=slots)
    class Model:
        value: int

    function = Retort(codegen_backend=CodeGenBackend.X86_64).get_loader(Model)
    for _ in range(20):
        assert function({"value": 1000}).value == 1000
    seen = []

    class Changed:
        @staticmethod
        def __setattr__(value, name, item):  # noqa: PLE0302
            seen.append((name, item))
            object.__setattr__(value, name, item + 1)

    Model.__init__.__closure__[0].cell_contents = Changed
    for _ in range(20):
        assert function({"value": 1000}).value == 1001
    assert seen == [("value", 1000)] * 20
