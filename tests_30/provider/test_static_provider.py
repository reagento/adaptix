from abc import ABC, abstractmethod

from dataclass_factory_30.provider import (
    Mediator,
    Request,
    RequestDispatcher,
    StaticProvider,
    static_provision_action
)


class SampleRequest(Request):
    pass


def test_simple():
    class TestSimple(StaticProvider):
        @static_provision_action(SampleRequest)
        def _provide_sample(
            self,
            mediator: Mediator,
            request: SampleRequest
        ):
            return

    assert (
        TestSimple().get_request_dispatcher()
        ==
        RequestDispatcher({SampleRequest: '_provide_sample'})
    )


def test_abstract_method():
    class Base(StaticProvider, ABC):
        @abstractmethod
        @static_provision_action(SampleRequest)
        def _provide_sample(
            self,
            mediator: Mediator,
            request: SampleRequest
        ):
            pass

    class Child(Base):
        def _provide_sample(
            self,
            mediator: Mediator,
            request: SampleRequest
        ):
            return

    assert (
        Child().get_request_dispatcher()
        ==
        RequestDispatcher({SampleRequest: '_provide_sample'})
    )
