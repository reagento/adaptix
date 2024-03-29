from abc import ABC, abstractmethod

import pytest
from tests_helpers import full_match

from adaptix import Mediator, Request
from adaptix._internal.provider.static_provider import RequestDispatcher, StaticProvider, static_provision_action


class SampleRequest(Request):
    pass


def test_simple():
    class TestSimple1(StaticProvider):
        @static_provision_action(SampleRequest)
        def _provide_sample(self, mediator: Mediator, request: SampleRequest):
            pass

    assert (
        TestSimple1._sp_cls_request_dispatcher
        ==
        RequestDispatcher({SampleRequest: "_provide_sample"})
    )

    class TestSimple2(StaticProvider):
        @static_provision_action()
        def _provide_sample(self, mediator: Mediator, request: SampleRequest):
            pass

    assert (
        TestSimple2._sp_cls_request_dispatcher
        ==
        RequestDispatcher({SampleRequest: "_provide_sample"})
    )

    class TestSimple3(StaticProvider):
        @static_provision_action
        def _provide_sample(self, mediator: Mediator, request: SampleRequest):
            pass

    assert (
        TestSimple3._sp_cls_request_dispatcher
        ==
        RequestDispatcher({SampleRequest: "_provide_sample"})
    )

    class TestSimple4(StaticProvider):
        @static_provision_action(SampleRequest)
        def _provide_sample(self, mediator: Mediator, request):
            pass

    assert (
        TestSimple4._sp_cls_request_dispatcher
        ==
        RequestDispatcher({SampleRequest: "_provide_sample"})
    )

    class NotASampleRequest(Request):
        pass

    class TestSimple5(StaticProvider):
        @static_provision_action(SampleRequest)
        def _provide_sample(self, mediator: Mediator, request: NotASampleRequest):
            pass

    assert (
        TestSimple5._sp_cls_request_dispatcher
        ==
        RequestDispatcher({SampleRequest: "_provide_sample"})
    )


def test_abstract_method():
    class Base(StaticProvider, ABC):
        @abstractmethod
        @static_provision_action
        def _provide_sample(self, mediator: Mediator, request: SampleRequest):
            pass

    class Child(Base):
        def _provide_sample(self, mediator: Mediator, request: SampleRequest):
            pass

    assert (
        Child._sp_cls_request_dispatcher
        ==
        RequestDispatcher({SampleRequest: "_provide_sample"})
    )


def test_error_raising_with_one_class():
    with pytest.raises(TypeError):
        class BadDecoratorArg(StaticProvider):
            @static_provision_action
            def _provide(self, mediator: Mediator, request: int):
                pass

    with pytest.raises(
        ValueError,
        match=full_match("@static_provision_action decorator cannot be applied twice"),
    ):
        class DoubleDecoration(StaticProvider):
            @static_provision_action
            @static_provision_action
            def _provide(self, mediator: Mediator, request: Request):
                pass

    with pytest.raises(TypeError):
        class SeveralSPA(StaticProvider):
            @static_provision_action
            def _provide_one(self, mediator: Mediator, request: Request):
                pass

            @static_provision_action
            def _provide_two(self, mediator: Mediator, request: Request):
                pass


class Base1(StaticProvider):
    @static_provision_action
    def _provide_one(self, mediator: Mediator, request: Request):
        pass


class Base2(StaticProvider):
    @static_provision_action
    def _provide_two(self, mediator: Mediator, request: Request):
        pass


def test_inheritance_redefine_spa():
    with pytest.raises(TypeError):
        class RedefineSPAChild(Base1):
            @static_provision_action
            def _provide_one(self, mediator: Mediator, request: Request):
                pass


def test_inheritance_several_spa():
    with pytest.raises(TypeError):
        class SeveralSPAChild(Base1):
            @static_provision_action
            def _provide_two(self, mediator: Mediator, request: Request):
                pass

    with pytest.raises(TypeError):
        class Child12(Base1, Base2):
            pass

    with pytest.raises(TypeError):
        class Child21(Base2, Base1):
            pass


def test_inheritance_several_rc():
    class Base3(StaticProvider):
        @static_provision_action
        def _provide_one(self, mediator: Mediator, request: SampleRequest):
            pass

    with pytest.raises(TypeError):
        class Child13(Base1, Base3):
            pass

    with pytest.raises(TypeError):
        class Child1(Base1):
            @static_provision_action
            def _provide_one(self, mediator: Mediator, request: SampleRequest):
                pass
