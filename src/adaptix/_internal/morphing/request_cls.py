from dataclasses import dataclass

from ..common import Dumper, Loader
from ..provider.request_cls import LocatedRequest


@dataclass(frozen=True)
class LoaderRequest(LocatedRequest[Loader]):
    pass


@dataclass(frozen=True)
class DumperRequest(LocatedRequest[Dumper]):
    pass
