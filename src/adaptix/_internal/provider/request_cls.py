from dataclasses import dataclass, field, replace
from typing import Any, Mapping, TypeVar

from ..common import Dumper, Loader, TypeHint
from ..model_tools import Accessor, Default, ParamKind
from ..provider.essential import CannotProvide, Request
from ..utils import ClassMap

T = TypeVar('T')


@dataclass(frozen=True)
class Location:
    pass


@dataclass(frozen=True)
class TypeHintLoc(Location):
    type: TypeHint


@dataclass(frozen=True)
class FieldLoc(Location):
    name: str
    default: Default
    metadata: Mapping[Any, Any] = field(hash=False)


@dataclass(frozen=True)
class InputFieldLoc(Location):
    is_required: bool
    param_kind: ParamKind
    param_name: str


@dataclass(frozen=True)
class OutputFieldLoc(Location):
    accessor: Accessor


@dataclass(frozen=True)
class GenericParamLoc(Location):
    pos: int


LocMap = ClassMap[Location]
LR = TypeVar('LR', bound='LocatedRequest')


@dataclass(frozen=True)
class LocatedRequest(Request[T]):
    loc_map: LocMap


@dataclass(frozen=True)
class LoaderRequest(LocatedRequest[Loader]):
    pass


@dataclass(frozen=True)
class DumperRequest(LocatedRequest[Dumper]):
    pass


def get_type_from_request(request: LocatedRequest) -> TypeHint:
    return request.loc_map.get_or_raise(TypeHintLoc, lambda: CannotProvide).type


class StrictCoercionRequest(LocatedRequest[bool]):
    pass


class DebugPathRequest(LocatedRequest[bool]):
    pass
