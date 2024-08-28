from collections.abc import Sequence
from pathlib import Path

from tests_helpers.misc import import_local_module, temp_module

from adaptix._internal.type_tools import get_all_type_hints
from adaptix.type_tools import exec_type_checking


def test_exec_type_checking():
    module = import_local_module(Path(__file__).with_name("data_type_checking.py"))
    with temp_module(module):
        exec_type_checking(module)
        assert get_all_type_hints(module.Foo) == {
            "a": bool,
            "b": Sequence[int],
            "c": Sequence[str],
        }
