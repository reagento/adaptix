from ...provider.essential import CannotProvide, Request
from ...provider.request_cls import LocatedRequest
from ...provider.request_filtering import DirectMediator, RequestChecker
from ...provider.shape_provider import InputShapeRequest, OutputShapeRequest


class AnyModelRC(RequestChecker):
    def check_request(self, mediator: DirectMediator, request: Request) -> None:
        if not isinstance(request, LocatedRequest):
            raise CannotProvide

        try:
            mediator.provide(InputShapeRequest(loc_stack=request.loc_stack))
        except CannotProvide:
            mediator.provide(OutputShapeRequest(loc_stack=request.loc_stack))
