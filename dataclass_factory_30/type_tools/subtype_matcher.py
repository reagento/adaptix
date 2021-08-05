from abc import ABC, abstractmethod
from typing import Dict, TypeVar, Optional

from ..common import TypeHint

SubtypeMatch = Dict[TypeVar, TypeHint]


class SubtypeMatcher(ABC):
    @abstractmethod
    def __call__(self, sub_tp: TypeHint) -> Optional[SubtypeMatch]:
        pass

    @abstractmethod
    def is_subtype(self, sub_tp: TypeHint) -> bool:
        pass


class DefaultSubtypeMatcher(SubtypeMatcher):
    def __init__(self, tp: TypeHint):
        pass

    def __call__(self, sub_tp: TypeHint) -> Optional[SubtypeMatch]:
        pass

    def is_subtype(self, sub_tp: TypeHint) -> bool:
        pass
