from dataclasses import dataclass, field
from typing import Any, Callable, Mapping, Type, TypeVar, Union

from ..common import TypeHint
from ..model_tools.definitions import Accessor, Default

T = TypeVar("T")


class _BaseLoc:
    def cast_or_raise(
        self,
        tp: Type[T],
        exception_factory: Callable[[], Union[BaseException, Type[BaseException]]],
    ) -> T:
        if type(self) in _CAST_SOURCES[tp]:
            return self  # type: ignore[return-value]
        raise exception_factory()

    def cast(self, tp: Type[T]) -> T:
        return self.cast_or_raise(tp, lambda: TypeError(f"Can not cast {self} to {tp}"))

    def is_castable(self, tp: Type[T]) -> bool:
        return type(self) in _CAST_SOURCES[tp]


@dataclass(frozen=True)
class _TypeHintLoc(_BaseLoc):
    type: TypeHint


@dataclass(frozen=True)
class _FieldLoc(_TypeHintLoc):
    field_id: str
    default: Default
    metadata: Mapping[Any, Any] = field(hash=False)


@dataclass(frozen=True)
class _InputFieldLoc(_FieldLoc):
    is_required: bool


@dataclass(frozen=True)
class _OutputFieldLoc(_FieldLoc):
    accessor: Accessor


@dataclass(frozen=True)
class _GenericParamLoc(_TypeHintLoc):
    generic_pos: int


class TypeHintLoc(_TypeHintLoc):
    pass


class FieldLoc(_FieldLoc):
    pass


class InputFieldLoc(_InputFieldLoc):
    pass


class OutputFieldLoc(_OutputFieldLoc):
    pass


class GenericParamLoc(_GenericParamLoc):
    pass


_CAST_SOURCES = {
    TypeHintLoc: {TypeHintLoc, FieldLoc, InputFieldLoc, OutputFieldLoc, GenericParamLoc},
    FieldLoc: {FieldLoc, InputFieldLoc, OutputFieldLoc},
    InputFieldLoc: (InputFieldLoc, ),
    OutputFieldLoc: (OutputFieldLoc, ),
    GenericParamLoc: (GenericParamLoc, ),
}

AnyLoc = Union[TypeHintLoc, FieldLoc, InputFieldLoc, OutputFieldLoc, GenericParamLoc]
