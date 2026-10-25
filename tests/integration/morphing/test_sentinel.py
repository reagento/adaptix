from dataclasses import dataclass
from typing import Optional

from adaptix import Retort


def test_loader_with_sentinel_builtin(debug_trail):
    @dataclass
    class Model:
        value: int
        optional_value: Optional[int] = 7

    loader = Retort(debug_trail=debug_trail).get_loader(Model)

    assert loader({"value": 1}) == Model(1)
    assert loader({"value": 1, "optional_value": None}) == Model(1, None)

