import dataclasses
import inspect
import re
import runpy
import sys
from contextlib import contextmanager
from dataclasses import dataclass, is_dataclass
from enum import Enum
from operator import getitem
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import (
    Any,
    Callable,
    Dict,
    Generator,
    List,
    Mapping,
    NamedTuple,
    Optional,
    Reversible,
    Type,
    TypedDict,
    TypeVar,
    Union,
)
from uuid import uuid4

import pytest
from _pytest.python import Metafunc
from sqlalchemy import Engine, create_engine

from adaptix import AdornedRetort, CannotProvide, DebugTrail, Mediator, NoSuitableProvider, Provider, Request
from adaptix._internal.compat import CompatExceptionGroup
from adaptix._internal.feature_requirement import HAS_ATTRS_PKG, HAS_PY_311, DistributionVersionRequirement, Requirement
from adaptix._internal.morphing.model.basic_gen import CodeGenAccumulator
from adaptix._internal.struct_trail import TrailElement, extend_trail, render_trail_as_note
from adaptix._internal.type_tools import is_parametrized
from adaptix._internal.utils import add_note
from adaptix.struct_trail import get_trail

T = TypeVar("T")


ATTRS_WITH_ALIAS = DistributionVersionRequirement('attrs', '22.2.0')


def requires(requirement: Requirement):
    def wrapper(func):
        return pytest.mark.skipif(
            not requirement,
            reason=requirement.fail_reason,
        )(func)

    return wrapper


class TestRetort(AdornedRetort):
    def provide(self, request: Request[T]) -> T:
        return self._facade_provide(request, error_message=f'cannot provide {request}')


E = TypeVar('E', bound=Exception)


def _repr_value(obj: Any) -> Dict[str, Any]:
    if not isinstance(obj, Exception):
        return obj

    result = {}
    if is_dataclass(obj):
        result.update(
            **{
                fld.name: _repr_value(getattr(obj, fld.name))
                for fld in dataclasses.fields(obj)
            }
        )
    if isinstance(obj, CompatExceptionGroup):
        result['message'] = obj.message
        result['exceptions'] = [_repr_value(exc) for exc in obj.exceptions]
    if isinstance(obj, CannotProvide):
        result['message'] = obj.message
        result['is_terminal'] = obj.is_terminal
        result['is_demonstrative'] = obj.is_demonstrative
    if isinstance(obj, NoSuitableProvider):
        result['message'] = obj.message
    if not result:
        result['args'] = [_repr_value(arg) for arg in obj.args]
    return {
        '__type__': type(obj),
        '__trail__': list(get_trail(obj)),
        **result,
        '__cause__': _repr_value(obj.__cause__),
        '__notes__': getattr(obj, '__notes__', []),
    }


def raises_exc(
    exc: Union[Type[E], E],
    func: Callable[[], Any],
    *,
    match: Optional[str] = None,
) -> E:
    exc_type = exc if isinstance(exc, type) else type(exc)

    with pytest.raises(exc_type, match=match) as exc_info:
        func()

    assert _repr_value(exc_info.value) == _repr_value(exc)

    return exc_info.value


def with_cause(exc: E, cause: BaseException) -> E:
    exc.__cause__ = cause
    return exc


def parametrize_bool(param: str, *params: str):
    full_params = [param, *params]

    def decorator(func):
        for p in full_params:
            func = pytest.mark.parametrize(
                p, [False, True],
                ids=[f'{p}=False', f'{p}=True']
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

    def apply_provider(self, mediator: Mediator, request: Request[T]) -> T:
        raise CannotProvide


def full_match_regex_str(string_to_match: str) -> str:
    return '^' + re.escape(string_to_match) + '$'


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


def create_sa_engine(**kwargs) -> Engine:
    return create_engine("sqlite://", **kwargs)


T1 = TypeVar('T1')
T2 = TypeVar('T2')
T3 = TypeVar('T3')


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
    vars: Optional[Dict[str, Any]] = None,  # noqa: A002
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
        ns_dict['__ns_id__'] = ns_id
    return SimpleNamespace(**ns_dict)


@contextmanager
def load_namespace_keeping_module(
    file_name: str,
    ns_id: Optional[str] = None,
    vars: Optional[Dict[str, Any]] = None,  # noqa: A002
    run_name: Optional[str] = None,
) -> Generator[SimpleNamespace, None, None]:
    if run_name is None:
        run_name = 'temp_module_' + uuid4().hex
    ns = load_namespace(file_name=file_name, ns_id=ns_id, vars=vars, run_name=run_name, stack_offset=3)
    module = ModuleType(run_name)
    for attr, value in ns.__dict__.items():
        setattr(module, attr, value)
    sys.modules[run_name] = module
    try:
        yield ns
    finally:
        sys.modules.pop(run_name, None)


def with_notes(exc: E, *notes: Union[str, List[str]]) -> E:
    for note_or_list in notes:
        if isinstance(note_or_list, list):
            for note in note_or_list:
                add_note(exc, note)
        else:
            add_note(exc, note_or_list)
    return exc


def with_trail(exc: E, sub_trail: Reversible[TrailElement]) -> E:
    return render_trail_as_note(extend_trail(exc, sub_trail))


class ModelSpec(Enum):
    DATACLASS = 'dataclass'
    TYPED_DICT = 'typed_dict'
    NAMED_TUPLE = 'named_tuple'
    ATTRS = 'attrs'

    @classmethod
    def default_requirements(cls):
        return {
            cls.ATTRS: HAS_ATTRS_PKG,
        }


@dataclass
class ModelSpecSchema:
    decorator: Any
    bases: Any
    get_field: Callable[[Any, str], Any]


def model_spec_to_schema(spec: ModelSpec):
    if spec == ModelSpec.DATACLASS:
        return ModelSpecSchema(decorator=dataclass, bases=(), get_field=getattr)
    if spec == ModelSpec.TYPED_DICT:
        return ModelSpecSchema(decorator=lambda x: x, bases=(TypedDict,), get_field=getitem)
    if spec == ModelSpec.NAMED_TUPLE:
        return ModelSpecSchema(decorator=lambda x: x, bases=(NamedTuple,), get_field=getattr)
    if spec == ModelSpec.ATTRS:
        from attrs import define
        return ModelSpecSchema(decorator=define, bases=(), get_field=getattr)
    raise ValueError


def exclude_model_spec(first_spec: ModelSpec, *other_specs: ModelSpec):
    specs = [first_spec, *other_specs]

    def decorator(func):
        func.adaptix_exclude_model_spec = specs
        return func

    return decorator


GENERIC_MODELS_REQUIREMENTS: Mapping[ModelSpec, Requirement] = {
    ModelSpec.TYPED_DICT: HAS_PY_311,
    ModelSpec.NAMED_TUPLE: HAS_PY_311,
}


def only_generic_models(test_func):
    test_func.adaptix_model_spec_requirements = GENERIC_MODELS_REQUIREMENTS


def parametrize_model_spec(fixture_name: str, metafunc: Metafunc) -> None:
    if fixture_name not in metafunc.fixturenames:
        return

    excluded = getattr(metafunc.function, 'adaptix_exclude_model_spec', [])
    requirements = {
        **ModelSpec.default_requirements(),
        **getattr(metafunc.module, 'adaptix_model_spec_requirements', {}),
        **getattr(metafunc.function, 'adaptix_model_spec_requirements', {}),
    }
    metafunc.parametrize(
        fixture_name,
        [
            pytest.param(model_spec_to_schema(spec), id=spec.value)
            for spec in ModelSpec
            if spec not in excluded and (spec not in requirements or bool(requirements[spec]))
        ]
    )
