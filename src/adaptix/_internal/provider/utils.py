from typing import Sequence

from .essential import Request
from .request_cls import FieldLoc, LocatedRequest


def find_field_request(request_stack: Sequence[Request]) -> LocatedRequest:
    for parent_request in request_stack:
        if isinstance(parent_request, LocatedRequest) and parent_request.loc_map.has(FieldLoc):
            return parent_request
    raise ValueError('Owner type is not found')
