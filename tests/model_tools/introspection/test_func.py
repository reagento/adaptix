import pytest

from _dataclass_factory.model_tools import get_func_figure


class MyClass:
    pass


def test_error_at_class_passing():
    pytest.raises(TypeError, lambda: get_func_figure(MyClass))
