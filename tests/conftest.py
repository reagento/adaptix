from typing import TypeVar, Union

import pytest

from adaptix import DebugTrail


@pytest.fixture(params=[False, True], ids=lambda x: f'strict_coercion={x}')
def strict_coercion(request):
    return request.param


@pytest.fixture(params=[DebugTrail.DISABLE, DebugTrail.FIRST, DebugTrail.ALL])
def debug_trail(request):
    return request.param


T1 = TypeVar('T1')
T2 = TypeVar('T2')
T3 = TypeVar('T3')


class ByTrailSelector:
    def __init__(self, debug_trail: DebugTrail):
        self.debug_trail = debug_trail

    def __call__(self, *, disable: T1, first: T2, all: T3) -> Union[T1, T2, T3]:
        if self.debug_trail == DebugTrail.DISABLE:
            return disable
        if self.debug_trail == DebugTrail.FIRST:
            return first
        if self.debug_trail == DebugTrail.ALL:
            return all
        raise ValueError


@pytest.fixture
def trail_select(debug_trail):
    return ByTrailSelector(debug_trail)
