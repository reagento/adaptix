import pytest
from tests_helpers import full_match_regex_str

from adaptix._internal.conversion.facade.checker import ensure_function_is_stub


def test_pass():
    def func():
        pass

    ensure_function_is_stub(func)


def test_ellipsis():
    def func():
        ...

    ensure_function_is_stub(func)


def test_docstring():
    def func():
        """I'm a func"""

    ensure_function_is_stub(func)


def test_exception():
    def func():
        return 1 + 2

    with pytest.raises(ValueError, match=full_match_regex_str('Body of function must be empty')):
        ensure_function_is_stub(func)
