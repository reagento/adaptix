from typing import Tuple

import pytest

from dataclass_factory._internal.model_tools import IntrospectionImpossible, get_callable_figure


def test_introspection_impossible():
    pytest.raises(IntrospectionImpossible, lambda: get_callable_figure(Tuple))
