from collections import deque

import pytest

from adaptix.struct_trail import append_trail, extend_trail, get_trail


def _raw_trail(obj: object):
    # noinspection PyProtectedMember
    return obj._adaptix_struct_trail  # type: ignore[attr-defined]


def test_append_trail():
    exc = Exception()

    append_trail(exc, "foo")
    assert _raw_trail(exc) == deque(["foo"])
    append_trail(exc, "bar")
    assert _raw_trail(exc) == deque(["bar", "foo"])
    append_trail(exc, 3)
    assert _raw_trail(exc) == deque([3, "bar", "foo"])


def test_extend_trail():
    exc = Exception()

    extend_trail(exc, ["a", "b"])
    assert _raw_trail(exc) == deque(["a", "b"])
    extend_trail(exc, ["c", "d"])
    assert _raw_trail(exc) == deque(["c", "d", "a", "b"])


def test_get_trail():
    exc = Exception()

    pytest.raises(AttributeError, lambda: _raw_trail(exc))
    assert list(get_trail(exc)) == []

    append_trail(exc, "foo")

    assert list(get_trail(exc)) == ["foo"]

    new_exc = Exception()
    append_trail(new_exc, "bar")

    assert list(get_trail(new_exc)) == ["bar"]
