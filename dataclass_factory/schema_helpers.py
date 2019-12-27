from datetime import datetime
from typing import Any
from typing import Dict
from uuid import UUID

from .common import T
from .schema import Schema

try:
    isotime_schema = Schema(
        parser=datetime.fromisoformat,  # type: ignore
        serializer=datetime.isoformat
    )
except AttributeError:
    pass

unixtime_schema = Schema(
    parser=datetime.fromtimestamp,
    serializer=datetime.timestamp
)

uuid_schema = Schema(
    serializer=UUID.__str__,
    parser=UUID
)


def _stub(data: T) -> T:
    return data


stub_schema = Schema(
    parser=_stub,
    serializer=_stub,
)


def get_cls_check_parser(cls: type, debug_path: bool):
    def cls_check_parser(data):
        if isinstance(data, cls):
            return data
        raise TypeError(f'Argument must be {cls.__name__}')

    return cls_check_parser


cls_check_schema = Schema(
    serializer=_stub,
    get_parser=get_cls_check_parser,
)


def cls_as_dict_pre_parse(data: Any) -> Dict[str, Any]:
    return data.__dict__


cls_as_dict_schema = Schema(
    pre_parse=cls_as_dict_pre_parse
)
