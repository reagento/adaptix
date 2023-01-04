from dataclasses import dataclass
from itertools import permutations
from typing import Optional, Sequence, Type

import pytest

from dataclass_factory.provider import CannotProvide, Mediator, Provider, Request
from dataclass_factory.retort import BuiltinMediator, RawRecipeSearcher, RecursionResolving


@dataclass(frozen=True)
class SampleRequest1(Request[None]):
    pass


@dataclass(frozen=True)
class SampleRequest2(Request[None]):
    pass


@dataclass(frozen=True)
class SampleRequest3(Request[None]):
    pass


@dataclass
class StackAsserter(Provider):
    request_type: Type[Request]
    expected_stack: Sequence[Request]
    send_next: Optional[Request]

    def apply_provider(self, mediator: Mediator, request: Request):
        if not isinstance(request, self.request_type):
            raise CannotProvide

        assert list(self.expected_stack) == list(mediator.request_stack)

        if self.send_next is not None:
            mediator.provide(self.send_next)


ASSERTER_LIST = [
    StackAsserter(SampleRequest1, [SampleRequest1()], send_next=SampleRequest2()),
    StackAsserter(SampleRequest2, [SampleRequest1(), SampleRequest2()], send_next=SampleRequest3()),
    StackAsserter(SampleRequest3, [SampleRequest1(), SampleRequest2(), SampleRequest3()], send_next=None),
]


@pytest.mark.parametrize(
    'order',
    [
        pytest.param(order, id=str(order))
        for order in permutations([1, 2, 3])
    ],
)
def test_request_stack(order):
    searcher = RawRecipeSearcher(recipe=[ASSERTER_LIST[value-1] for value in order])

    mediator = BuiltinMediator(
        searcher=searcher,
        recursion_resolving=RecursionResolving(),
        request_stack=[],
    )

    mediator.provide(
        SampleRequest1(),
    )
