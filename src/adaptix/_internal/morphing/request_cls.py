from dataclasses import dataclass

from ... import DebugTrail
from ..common import Dumper, Loader
from ..provider.loc_stack_basis import LocatedRequest


@dataclass(frozen=True)
class LoaderRequest(LocatedRequest[Loader]):
    pass


@dataclass(frozen=True)
class DumperRequest(LocatedRequest[Dumper]):
    pass


class StrictCoercionRequest(LocatedRequest[bool]):
    pass


class DebugTrailRequest(LocatedRequest[DebugTrail]):
    pass
