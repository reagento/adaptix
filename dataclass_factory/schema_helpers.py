from datetime import datetime
from uuid import UUID

from .factory import StackedFactory
from .common import T
from .schema import Schema

try:
    isotime_schema = Schema(
        parser=datetime.fromisoformat,  # type: ignore
        serializer=datetime.isoformat
    )
except AttributeError:
    pass


def type_checker(value, field="type", pre_parse=None):
    def check_type(data):
        if value != data[field]:
            raise ValueError
        if pre_parse:
            return pre_parse(data)
        return data

    return check_type


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


class ClsCheckSchema(Schema[T]):
    serializer = _stub

    def get_parser(self, cls, stacked_factory: StackedFactory, debug_path: bool):  # type: ignore
        def cls_check_parser(data):
            if isinstance(data, cls):
                return data
            raise TypeError(f'Argument must be {cls.__name__}')

        return cls_check_parser
