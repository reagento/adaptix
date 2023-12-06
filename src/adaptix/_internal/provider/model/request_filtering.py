from ..essential import CannotProvide, Request
from ..request_cls import LocatedRequest
from ..request_filtering import DirectMediator, RequestChecker
from .definitions import InputShapeRequest, OutputShapeRequest


class AnyModelRC(RequestChecker):
    def check_request(self, mediator: DirectMediator, request: Request) -> None:
        if not isinstance(request, LocatedRequest):
            raise CannotProvide

        try:
            mediator.provide(InputShapeRequest(loc_map=request.loc_map))
        except CannotProvide:
            mediator.provide(OutputShapeRequest(loc_map=request.loc_map))
