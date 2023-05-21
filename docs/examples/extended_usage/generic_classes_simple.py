from dataclasses import dataclass
from typing import Generic, Optional, TypeVar

from adaptix import Retort

T = TypeVar('T')


@dataclass
class MinMax(Generic[T]):
    min: Optional[T] = None
    max: Optional[T] = None


retort = Retort()

data = {'min': 10, 'max': 20}
min_max = retort.load(data, MinMax[int])
assert min_max == MinMax(min=10, max=20)
assert retort.dump(min_max, MinMax[int])
