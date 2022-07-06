from collections import deque

import pytest

from dataclass_factory_30.struct_path import append_path, extend_path, get_path, get_path_unchecked


def _raw_path(obj: object):
    # noinspection PyProtectedMember
    return obj._df_struct_path  # type: ignore[attr-defined]


def test_append_path():
    exc = Exception()

    append_path(exc, 'foo')
    assert _raw_path(exc) == deque(['foo'])
    append_path(exc, 'bar')
    assert _raw_path(exc) == deque(['bar', 'foo'])
    append_path(exc, 3)
    assert _raw_path(exc) == deque([3, 'bar', 'foo'])

    append_path(object(), 'baz')


def test_extend_path():
    exc = Exception()

    extend_path(exc, ['a', 'b'])
    assert _raw_path(exc) == deque(['a', 'b'])
    extend_path(exc, ['c', 'd'])
    assert _raw_path(exc) == deque(['c', 'd', 'a', 'b'])

    extend_path(object(), ['baz'])


def test_get_path():
    exc = Exception()

    assert list(get_path_unchecked(exc)) == []

    with pytest.raises(AttributeError):
        _raw_path(exc)

    assert list(get_path(exc)) == []
    assert list(get_path_unchecked(exc)) == []
    assert _raw_path(exc) == deque()

    append_path(exc, 'foo')

    assert list(get_path(exc)) == ['foo']
    assert list(get_path_unchecked(exc)) == ['foo']

    new_exc = Exception()
    append_path(new_exc, 'bar')

    assert list(get_path(new_exc)) == ['bar']
    assert list(get_path_unchecked(new_exc)) == ['bar']

    assert get_path(object()) is None
    assert list(get_path_unchecked(object())) == []
