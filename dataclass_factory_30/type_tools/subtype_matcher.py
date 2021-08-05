from abc import ABC, abstractmethod
from collections import abc as c_abc
from typing import Dict, TypeVar, Optional, Any, Annotated, NoReturn, List, ClassVar, Final

from . import normalize_type, NormType, is_new_type, is_subclass_soft
from ..common import TypeHint

SubtypeMatch = Dict[TypeVar, TypeHint]


class SubtypeMatcher(ABC):
    @abstractmethod
    def __call__(self, sub_tp: TypeHint, tp: TypeHint) -> Optional[SubtypeMatch]:
        pass

    @abstractmethod
    def is_subtype(self, sub_tp: TypeHint, tp: TypeHint) -> bool:
        pass


class DefaultSubtypeMatcher(SubtypeMatcher):
    def __call__(self, sub_tp: TypeHint, tp: TypeHint) -> Optional[SubtypeMatch]:
        pass

    def is_subtype(self, sub_tp: TypeHint, tp: TypeHint) -> bool:
        pass

