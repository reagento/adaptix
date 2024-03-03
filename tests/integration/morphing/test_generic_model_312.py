from dataclasses import dataclass
from decimal import Decimal
from typing import Optional

from adaptix import Retort


@dataclass
class MinMax[NumberT]:
    min_value: Optional[NumberT]
    max_value: Optional[NumberT]


def test_loading():
    retort = Retort()

    assert retort.load({"min_value": 1, "max_value": 2}, MinMax[int]) == MinMax(1, 2)
    assert retort.load({"min_value": "1", "max_value": "2"}, MinMax[Decimal]) == MinMax(Decimal(1), Decimal(2))


def test_dumping():
    retort = Retort()

    assert retort.dump(MinMax(1, 2), MinMax[int]) == {"min_value": 1, "max_value": 2}
    assert retort.dump(MinMax(Decimal(1), Decimal(2)), MinMax[Decimal]) == {"min_value": "1", "max_value": "2"}
