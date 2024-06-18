from adaptix._internal.provider.essential import DirectMediator, Request, RequestChecker


class AlwaysTrueRequestChecker(RequestChecker):
    def check_request(self, mediator: DirectMediator, request: Request, /) -> bool:
        return True

