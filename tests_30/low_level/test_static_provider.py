from abc import ABC, abstractmethod

from dataclass_factory_30.core import BaseFactory, SearchState, Request, RequestDispatcher
from dataclass_factory_30.low_level import StaticProvider, static_provision_action, ParserRequest


class SampleRequest(Request):
    pass


def test_simple():
    class TestSimple(StaticProvider):
        @static_provision_action(SampleRequest)
        def _provide_sample(
            self,
            factory: BaseFactory,
            s_state: SearchState,
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
            factory: BaseFactory,
            s_state: SearchState,
            request: SampleRequest
        ):
            pass

    class Child(Base):
        def _provide_sample(
            self,
            factory: BaseFactory,
            s_state: SearchState,
            request: SampleRequest
        ):
            return

    assert (
        Child().get_request_dispatcher()
        ==
        RequestDispatcher({SampleRequest: '_provide_sample'})
    )
