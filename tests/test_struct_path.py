import json
import logging
from collections import deque

import pytest
from pythonjsonlogger import jsonlogger

from dataclass_factory.struct_path import StructPathRendererFilter, append_path, extend_path, get_path
from tests_helpers import rollback_object_state


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


def test_extend_path():
    exc = Exception()

    extend_path(exc, ['a', 'b'])
    assert _raw_path(exc) == deque(['a', 'b'])
    extend_path(exc, ['c', 'd'])
    assert _raw_path(exc) == deque(['c', 'd', 'a', 'b'])


def test_get_path():
    exc = Exception()

    pytest.raises(AttributeError, lambda: _raw_path(exc))
    assert list(get_path(exc)) == []

    append_path(exc, 'foo')

    assert list(get_path(exc)) == ['foo']

    new_exc = Exception()
    append_path(new_exc, 'bar')

    assert list(get_path(new_exc)) == ['bar']


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
        raise extend_path(ValueError(), ['a', 'b'])
    except Exception:
        temp_logger.exception('unexpected exception')
    assert caplog.records[-1].struct_path == ['a', 'b']


def test_struct_path_renderer_with_pythonjsonlogger(caplog, temp_logger):
    caplog.set_level(logging.DEBUG, temp_logger.name)
    temp_logger.addFilter(StructPathRendererFilter())

    with rollback_object_state(caplog.handler):
        caplog.handler.setFormatter(jsonlogger.JsonFormatter())

        try:
            raise extend_path(ValueError(), ['a', 'b'])
        except Exception:
            temp_logger.exception('unexpected exception')

        assert len(caplog.records) == 1
        assert json.loads(caplog.text)['struct_path'] == ['a', 'b']
