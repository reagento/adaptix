from typing import Tuple

import pytest

from adaptix._internal.model_tools import IntrospectionImpossible, get_callable_figure


def test_introspection_impossible():
    pytest.raises(IntrospectionImpossible, lambda: get_callable_figure(Tuple))
