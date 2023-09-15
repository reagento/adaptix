import json
import logging
from collections import deque

import pytest
from pythonjsonlogger import jsonlogger

from adaptix.struct_trail import StructPathRendererFilter, append_trail, extend_trail, get_trail
from tests_helpers import rollback_object_state


def _raw_trail(obj: object):
    # noinspection PyProtectedMember
    return obj._adaptix_struct_trail  # type: ignore[attr-defined]


def test_append_trail():
    exc = Exception()

    append_trail(exc, 'foo')
    assert _raw_trail(exc) == deque(['foo'])
    append_trail(exc, 'bar')
    assert _raw_trail(exc) == deque(['bar', 'foo'])
    append_trail(exc, 3)
    assert _raw_trail(exc) == deque([3, 'bar', 'foo'])


def test_extend_trail():
    exc = Exception()

    extend_trail(exc, ['a', 'b'])
    assert _raw_trail(exc) == deque(['a', 'b'])
    extend_trail(exc, ['c', 'd'])
    assert _raw_trail(exc) == deque(['c', 'd', 'a', 'b'])


def test_get_trail():
    exc = Exception()

    pytest.raises(AttributeError, lambda: _raw_trail(exc))
    assert list(get_trail(exc)) == []

    append_trail(exc, 'foo')

    assert list(get_trail(exc)) == ['foo']

    new_exc = Exception()
    append_trail(new_exc, 'bar')

    assert list(get_trail(new_exc)) == ['bar']


@pytest.fixture()
def temp_logger():
    logger = logging.getLogger('temp_test_logger')
    with rollback_object_state(logger):
        yield logger


def test_struct_path_renderer_filter(caplog, temp_logger):
    caplog.set_level(logging.DEBUG, temp_logger.name)
    temp_logger.addFilter(StructPathRendererFilter())

    try:
        raise ValueError
    except Exception:
        temp_logger.exception('unexpected exception')
    assert caplog.records[-1].struct_path == []

    try:
        raise extend_trail(ValueError(), ['a', 'b'])
    except Exception:
        temp_logger.exception('unexpected exception')
    assert caplog.records[-1].struct_path == ['a', 'b']


def test_struct_path_renderer_with_pythonjsonlogger(caplog, temp_logger):
    caplog.set_level(logging.DEBUG, temp_logger.name)
    temp_logger.addFilter(StructPathRendererFilter())

    with rollback_object_state(caplog.handler):
        caplog.handler.setFormatter(jsonlogger.JsonFormatter())

        try:
            raise extend_trail(ValueError(), ['a', 'b'])
        except Exception:
            temp_logger.exception('unexpected exception')

        assert len(caplog.records) == 1
        assert json.loads(caplog.text)['struct_path'] == ['a', 'b']
