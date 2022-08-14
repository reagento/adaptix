import re
from typing import Sequence, Union

from dataclass_factory_30.common import TypeHint
from dataclass_factory_30.provider.provider_basics import (
    StackEndRC, RequestChecker, OrRequestChecker, ReFieldNameRC,
    ExactFieldNameRC,
    create_type_hint_req_checker, AndRequestChecker, XorRequestChecker,
    NegRequestChecker
)

RequestCheckerSrc = Union[TypeHint, str, RequestChecker, 'F']


def create_req_checker(
    pred: RequestCheckerSrc,
) -> RequestChecker:
    if isinstance(pred, F):
        return pred.build_request_checker()

    if isinstance(pred, str):
        if pred.isidentifier():
            return ExactFieldNameRC(pred)  # this is only an optimization
        return ReFieldNameRC(re.compile(pred))

    if isinstance(pred, re.Pattern):
        return ReFieldNameRC(pred)

    if isinstance(pred, RequestChecker):
        return pred

    return create_type_hint_req_checker(pred)


class F:
    def __init__(
        self,
        *preds: Union[TypeHint, str, RequestChecker],
        stack: Sequence[RequestChecker] = (),
    ):
        current_checkers = []
        for pred in preds:
            current_checkers.append(create_req_checker(pred))
        self.stack = list(stack)
        self.stack.append(OrRequestChecker(current_checkers))

    def build_request_checker(self):
        return StackEndRC(self.stack)

    def __call__(
        self,
        *superclasses: type,
    ):
        return F(*superclasses, stack=self.stack)

    def __getitem__(self, item: str):
        checker = ReFieldNameRC(re.compile(item))
        return F(stack=self.stack + [checker])

    def __getattr__(self, item: str):
        return self[item]

    def __or__(self, other: RequestCheckerSrc) -> 'F':
        return F(stack=[OrRequestChecker([
            self.build_request_checker(), create_req_checker(other),
        ])])

    def __and__(self, other: RequestCheckerSrc) -> 'F':
        return F(stack=[AndRequestChecker([
            self.build_request_checker(), create_req_checker(other),
        ])])

    def __xor__(self, other: RequestCheckerSrc) -> 'F':
        return F(stack=[XorRequestChecker(
            self.build_request_checker(), create_req_checker(other),
        )])

    def __neg__(self) -> 'F':
        return F(stack=[
            NegRequestChecker(self.build_request_checker())
        ])


def ensure_f(
    pred: RequestCheckerSrc,
) -> F:
    if isinstance(pred, F):
        return pred
    return F(pred)
