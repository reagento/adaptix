import pytest

from dataclass_factory_30.model_tools import get_func_input_figure


class MyClass:
    pass


def test_error_at_class_passing():
    pytest.raises(TypeError, lambda: get_func_input_figure(MyClass))
