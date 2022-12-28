from abc import ABC, abstractmethod
from typing import Mapping, Sequence, TypeVar, Union

from ...common import VarTuple
from ..essential import Mediator
from ..model import DictExtraPolicy, ExtraSkip, Sieve
from ..model.crown_definitions import (
    Extractor,
    ExtraForbid,
    ExtraKwargs,
    InpExtraMove,
    InputNameLayoutRequest,
    LeafInpCrown,
    LeafOutCrown,
    OutExtraMove,
    OutputNameLayoutRequest,
    Saturator,
)

T = TypeVar('T')


ExtraIn = Union[ExtraSkip, str, Sequence[str], ExtraForbid, ExtraKwargs, Saturator]
ExtraOut = Union[ExtraSkip, str, Sequence[str], Extractor]

Key = Union[str, int]
Path = VarTuple[Key]
PathsTo = Mapping[Path, T]


class StructureMaker(ABC):
    @abstractmethod
    def make_inp_structure(
        self,
        mediator: Mediator,
        request: InputNameLayoutRequest,
    ) -> PathsTo[LeafInpCrown]:
        ...

    @abstractmethod
    def make_out_structure(
        self,
        mediator: Mediator,
        request: OutputNameLayoutRequest,
    ) -> PathsTo[LeafOutCrown]:
        ...


class SievesMaker(ABC):
    @abstractmethod
    def make_sieves(
        self,
        mediator: Mediator,
        request: OutputNameLayoutRequest,
        path_to_leaf: PathsTo[LeafOutCrown],
    ) -> PathsTo[Sieve]:
        ...


class ExtraPoliciesMaker(ABC):
    @abstractmethod
    def make_extra_policies(
        self,
        mediator: Mediator,
        request: InputNameLayoutRequest,
        path_to_leaf: PathsTo[LeafInpCrown],
    ) -> PathsTo[DictExtraPolicy]:
        ...


class ExtraMoveMaker(ABC):
    @abstractmethod
    def make_inp_extra_move(
        self,
        mediator: Mediator,
        request: InputNameLayoutRequest,
        path_to_leaf: PathsTo[LeafInpCrown],
    ) -> InpExtraMove:
        ...

    @abstractmethod
    def make_out_extra_move(
        self,
        mediator: Mediator,
        request: OutputNameLayoutRequest,
        path_to_leaf: PathsTo[LeafOutCrown],
    ) -> OutExtraMove:
        ...
