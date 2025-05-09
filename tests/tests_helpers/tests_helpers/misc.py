import dataclasses
import importlib.util
import inspect
import re
import runpy
import sys
from collections.abc import Generator, Mapping, Reversible, Sequence
from contextlib import contextmanager
from dataclasses import dataclass, is_dataclass
from functools import reduce
from pathlib import Path
from textwrap import dedent
from traceback import format_exception
from types import ModuleType, SimpleNamespace
from typing import Any, Callable, Optional, TypeVar, Union
from uuid import uuid4

import pytest

from adaptix import CannotProvide, DebugTrail, Provider, ProviderNotFoundError, Request, Retort
from adaptix._internal.compat import CompatExceptionGroup
from adaptix._internal.feature_requirement import DistributionVersionRequirement, Requirement
from adaptix._internal.morphing.model.basic_gen import CodeGenAccumulator
from adaptix._internal.provider.essential import Mediator, RequestHandlerRegisterRecord
from adaptix._internal.retort.operating_retort import OperatingRetort
from adaptix._internal.struct_trail import TrailElement, extend_trail, render_trail_as_note
from adaptix._internal.type_tools import is_parametrized
from adaptix._internal.utils import add_note
from adaptix.struct_trail import get_trail

ATTRS_WITH_ALIAS = DistributionVersionRequirement("attrs", "22.2.0")

T = TypeVar("T")


def requires(requirement: Requirement):
    def wrapper(func):
        return pytest.mark.skipif(
            not requirement,
            reason=requirement.fail_reason,
        )(func)

    return wrapper


E = TypeVar("E", bound=Exception)


def _repr_value(obj: Any) -> dict[str, Any]:
    if not isinstance(obj, Exception):
        return obj

    result = {}
    if is_dataclass(obj):
        result.update(
            **{
                fld.name: _repr_value(getattr(obj, fld.name))
                for fld in dataclasses.fields(obj)
            },
        )
    if isinstance(obj, CompatExceptionGroup):
        result["message"] = obj.message
        result["exceptions"] = [_repr_value(exc) for exc in obj.exceptions]
    if isinstance(obj, CannotProvide):
        result["message"] = obj.message
        result["is_terminal"] = obj.is_terminal
        result["is_demonstrative"] = obj.is_demonstrative
    if isinstance(obj, ProviderNotFoundError):
        result["message"] = obj.message
        result["description"] = obj.description
    if not result:
        result["args"] = [_repr_value(arg) for arg in obj.args]
    return {
        "__type__": type(obj),
        "__trail__": list(get_trail(obj)),
        **result,
        "__cause__": _repr_value(obj.__cause__),
        "__notes__": getattr(obj, "__notes__", []),
    }


def raises_exc(
    exc: Union[type[E], E],
    func: Callable[[], Any],
    *,
    match: Optional[str] = None,
) -> E:
    exc_type = exc if isinstance(exc, type) else type(exc)

    with pytest.raises(exc_type, match=match) as exc_info:
        func()

    assert _repr_value(exc_info.value) == _repr_value(exc)

    return exc_info.value


def _prepare_reference(reference: str, replaces: Mapping[str, Any]) -> str:
    text_replaces = {
        src: format(target) for src, target in replaces.items()
    }
    pattern = re.compile(
        "|".join(
            map(re.escape, sorted(text_replaces.keys(), key=len, reverse=True)),
        ),
    )
    return pattern.sub(
        lambda match: text_replaces[match.group()],
        dedent(reference).lstrip(),
    )


def raises_exc_text(
    func: Callable[[], Any],
    reference: str,
    replaces: Optional[Mapping[str, Any]] = None,
) -> None:
    try:
        func()
    except Exception as e:
        e.__traceback__ = None
        current = "".join(format_exception(type(e), e, e.__traceback__))
        final_reference = _prepare_reference(reference, replaces or {})
        assert current == final_reference
    else:
        raise AssertionError("Error is not raised")


def with_cause(exc: E, cause: BaseException) -> E:
    exc.__cause__ = cause
    return exc


def parametrize_bool(param: str, *params: str):
    full_params = [param, *params]

    def decorator(func):
        for p in full_params:
            func = pytest.mark.parametrize(
                p, [False, True],
                ids=[f"{p}=False", f"{p}=True"],
            )(func)
        return func

    return decorator


def cond_list(flag: object, lst: Union[Callable[[], list], list]) -> list:
    if flag:
        return lst() if callable(lst) else lst
    return []


@dataclass
class DebugCtx:
    accum: CodeGenAccumulator

    @property
    def source(self):
        return self.accum.list[-1][1].source

    @property
    def source_namespace(self):
        return self.accum.list[-1][1].namespace


@dataclass
class PlaceholderProvider(Provider):
    value: int

    def get_request_handlers(self) -> Sequence[RequestHandlerRegisterRecord]:
        return []


def full_match(string_to_match: str) -> str:
    return "^" + re.escape(string_to_match) + "$"


def pretty_typehint_test_id(config, val, argname):
    if is_parametrized(val):
        return str(val)
    try:
        return val.__name__
    except AttributeError:
        try:
            return val._name
        except AttributeError:
            return None


T1 = TypeVar("T1")
T2 = TypeVar("T2")
T3 = TypeVar("T3")


class ByTrailSelector:
    def __init__(self, debug_trail: DebugTrail):
        self.debug_trail = debug_trail

    def __call__(self, *, disable: T1, first: T2, all: T3) -> Union[T1, T2, T3]:  # noqa: A002
        if self.debug_trail == DebugTrail.DISABLE:
            return disable
        if self.debug_trail == DebugTrail.FIRST:
            return first
        if self.debug_trail == DebugTrail.ALL:
            return all
        raise ValueError


def load_namespace(
    file_name: str,
    ns_id: Optional[str] = None,
    vars: Optional[dict[str, Any]] = None,  # noqa: A002
    run_name: Optional[str] = None,
    stack_offset: int = 1,
) -> SimpleNamespace:
    caller_file = inspect.getfile(inspect.stack()[stack_offset].frame)
    ns_dict = runpy.run_path(
        str(Path(caller_file).with_name(file_name)),
        init_globals=vars,
        run_name=run_name,
    )
    if ns_id is not None:
        ns_dict["__ns_id__"] = ns_id
    return SimpleNamespace(**ns_dict)


@contextmanager
def temp_module(module: ModuleType):
    sys.modules[module.__name__] = module
    try:
        yield
    finally:
        sys.modules.pop(module.__name__, None)


@contextmanager
def load_namespace_keeping_module(
    file_name: str,
    ns_id: Optional[str] = None,
    vars: Optional[dict[str, Any]] = None,  # noqa: A002
    run_name: Optional[str] = None,
) -> Generator[SimpleNamespace, None, None]:
    if run_name is None:
        run_name = "temp_module_" + uuid4().hex
    ns = load_namespace(file_name=file_name, ns_id=ns_id, vars=vars, run_name=run_name, stack_offset=3)
    module = ModuleType(run_name)
    for attr, value in ns.__dict__.items():
        setattr(module, attr, value)

    with temp_module(module):
        yield ns


def import_local_module(file_path: Path, name: Optional[str] = None) -> ModuleType:
    if name is None:
        name = file_path.stem

    spec = importlib.util.spec_from_file_location(name, file_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def with_notes(exc: E, *notes: Union[str, list[str]]) -> E:
    for note_or_list in notes:
        if isinstance(note_or_list, list):
            for note in note_or_list:
                add_note(exc, note)
        else:
            add_note(exc, note_or_list)
    return exc


def with_trail(exc: E, sub_trail: Reversible[TrailElement]) -> E:
    return render_trail_as_note(extend_trail(exc, sub_trail))


class FailedRequirement(Requirement):
    def __init__(self, fail_reason: str):
        self._fail_reason = fail_reason
        super().__init__()

    def _evaluate(self) -> bool:
        return False

    @property
    def fail_reason(self) -> str:
        return self._fail_reason


class AndRequirement(Requirement):
    def __init__(self, *requirements):
        self._requirements = requirements
        super().__init__()

    def _evaluate(self) -> bool:
        return reduce(lambda a, b: bool(a) and bool(b), self._requirements)

    @property
    def fail_reason(self) -> str:
        return " AND ".join(requirement.fail_reason for requirement in self._requirements)


class StubRequest(Request):
    pass


stub_retort = Retort()


def create_mediator(retort: OperatingRetort = stub_retort) -> Mediator:
    return retort._create_mediator(StubRequest())
