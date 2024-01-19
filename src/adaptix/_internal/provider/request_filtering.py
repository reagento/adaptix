from abc import ABC, abstractmethod
from typing import Optional, Union

from .essential import CannotProvide, Provider, Request
from .loc_stack_filtering import DirectMediator, LocStackChecker, Pred, create_loc_stack_checker
from .request_cls import LocatedRequest


class RequestChecker(ABC):
    @abstractmethod
    def check_request(self, mediator: DirectMediator, request: Request) -> None:
        """Raise CannotProvide if the request does not meet the conditions"""


class ProviderWithRC(Provider, ABC):
    @abstractmethod
    def get_request_checker(self) -> Optional[RequestChecker]:
        ...


class AnyRequestChecker(RequestChecker):
    def check_request(self, mediator: DirectMediator, request: Request) -> None:
        return


class LSCRequestChecker(RequestChecker):
    def __init__(self, loc_stack_checker: LocStackChecker):
        self.loc_stack_checker = loc_stack_checker

    def check_request(self, mediator: DirectMediator, request: Request) -> None:
        if not isinstance(request, LocatedRequest):
            raise CannotProvide
        if not self.loc_stack_checker.check_loc_stack(mediator, request.loc_stack):
            raise CannotProvide


def create_request_checker(pred: Union[Pred, RequestChecker]) -> RequestChecker:
    if isinstance(pred, RequestChecker):
        return pred
    lsc = create_loc_stack_checker(pred)
    return LSCRequestChecker(lsc)
