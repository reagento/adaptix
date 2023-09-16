import importlib.metadata
import re
from contextlib import contextmanager
from copy import copy
from dataclasses import asdict, dataclass, is_dataclass
from typing import Any, Callable, Optional, Type, TypeVar, Union

import pytest
from packaging.version import Version
from sqlalchemy import Engine, create_engine

from adaptix import AdornedRetort, CannotProvide, Mediator, Provider, Request
from adaptix._internal.compat import CompatExceptionGroup
from adaptix._internal.feature_requirement import PythonImplementationRequirement, PythonVersionRequirement, Requirement
from adaptix._internal.provider.model.basic_gen import CodeGenAccumulator
from adaptix._internal.struct_trail import Trail, extend_trail
from adaptix._internal.type_tools import is_parametrized
from adaptix.struct_trail import get_trail

T = TypeVar("T")


class DistributionVersionRequirement(Requirement):
    def __init__(self, distribution: str, version: str):
        self.distribution = distribution
        self.required_version = Version(version)
        super().__init__()

    def _evaluate(self) -> bool:
        try:
            distribution = importlib.metadata.distribution(self.distribution)
        except importlib.metadata.PackageNotFoundError:
            return False
        current_version = Version(distribution.version)
        return current_version >= self.required_version


ATTRS_WITH_ALIAS = DistributionVersionRequirement('attrs', '22.2.0')

def requires(
    requirement: Union[
        PythonVersionRequirement,
        PythonImplementationRequirement,
        DistributionVersionRequirement,
    ]
):
    if isinstance(requirement, PythonVersionRequirement):
        ver_str = '.'.join(map(str, requirement.min_version))
        reason = f'Python >= {ver_str} is required'
    elif isinstance(requirement, PythonImplementationRequirement):
        reason = f'{requirement.implementation_name} is required'
    elif isinstance(requirement, DistributionVersionRequirement):
        reason = f'{requirement.distribution} {requirement.required_version} is required'
    else:
        raise TypeError

    def wrapper(func):
        return pytest.mark.skipif(
            not requirement,
            reason=reason,
        )(func)

    return wrapper


class TestRetort(AdornedRetort):
    provide = AdornedRetort._facade_provide


E = TypeVar('E', bound=Exception)


def _compare_exc_instance(exc: Exception, reference: Exception):
    if is_dataclass(reference):
        assert type(exc) == type(reference)
        assert asdict(exc) == asdict(reference)
        assert list(get_trail(exc)) == list(get_trail(reference))
        if isinstance(reference, CompatExceptionGroup):
            for sub_exc, sub_reference in zip(exc.exceptions, reference.exceptions):
                _compare_exc_instance(sub_exc, sub_reference)
    elif isinstance(reference, CompatExceptionGroup):
        assert type(exc) == type(reference)
        assert exc.message == reference.message
        assert list(get_trail(exc)) == list(get_trail(reference))
        for sub_exc, sub_reference in zip(exc.exceptions, reference.exceptions):
            _compare_exc_instance(sub_exc, sub_reference)
    else:
        assert type(exc) == type(reference)
        assert exc.args == reference.args
        assert list(get_trail(exc)) == list(get_trail(reference))


def raises_exc(
    exc: Union[Type[E], E],
    func: Callable[[], Any],
    *,
    trail: Optional[Trail] = None,
    match: Optional[str] = None,
) -> E:
    exc_type = exc if isinstance(exc, type) else type(exc)
    if trail is not None and get_trail(exc):
        raise ValueError('Reference exception must not have trail if trail parameter is passed')

    with pytest.raises(exc_type, match=match) as exc_info:
        func()

    if isinstance(exc, type):
        if trail is not None:
            assert list(get_trail(exc_info.value)) == trail
    else:
        if trail is not None:
            extend_trail(exc, trail)
        _compare_exc_instance(exc_info.value, exc)

    return exc_info.value


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


class CustomEqual:
    def __init__(self, func, repr_str):
        self.func = func
        self.repr_str = repr_str

    def __eq__(self, other):
        return self.func(other)

    def __repr__(self):
        return self.repr_str

    def __str__(self):
        return self.repr_str


def type_of(tp: type) -> Any:
    def type_of_equal(other):
        return isinstance(other, tp)

    return CustomEqual(type_of_equal, f"type_of({tp.__qualname__})")


def full_match_regex_str(string_to_match: str) -> str:
    return '^' + re.escape(string_to_match) + '$'


@contextmanager
def rollback_object_state(obj):
    state_copy = copy(obj.__dict__)
    try:
        yield obj
    finally:
        obj.__dict__ = state_copy


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
