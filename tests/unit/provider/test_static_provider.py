from abc import ABC, abstractmethod

import pytest
from tests_helpers import full_match

from adaptix import Mediator, Request
from adaptix._internal.provider.methods_provider import MethodsProvider, RequestDispatcher, method_handler


class SampleRequest(Request):
    pass


def test_simple():
    class TestSimple1(MethodsProvider):
        @method_handler(SampleRequest)
        def _provide_sample(self, mediator: Mediator, request: SampleRequest):
            pass

    assert (
        TestSimple1._sp_cls_request_dispatcher
        ==
        RequestDispatcher({SampleRequest: "_provide_sample"})
    )

    class TestSimple2(MethodsProvider):
        @method_handler()
        def _provide_sample(self, mediator: Mediator, request: SampleRequest):
            pass

    assert (
        TestSimple2._sp_cls_request_dispatcher
        ==
        RequestDispatcher({SampleRequest: "_provide_sample"})
    )

    class TestSimple3(MethodsProvider):
        @method_handler
        def _provide_sample(self, mediator: Mediator, request: SampleRequest):
            pass

    assert (
        TestSimple3._sp_cls_request_dispatcher
        ==
        RequestDispatcher({SampleRequest: "_provide_sample"})
    )

    class TestSimple4(MethodsProvider):
        @method_handler(SampleRequest)
        def _provide_sample(self, mediator: Mediator, request):
            pass

    assert (
        TestSimple4._sp_cls_request_dispatcher
        ==
        RequestDispatcher({SampleRequest: "_provide_sample"})
    )

    class NotASampleRequest(Request):
        pass

    class TestSimple5(MethodsProvider):
        @method_handler(SampleRequest)
        def _provide_sample(self, mediator: Mediator, request: NotASampleRequest):
            pass

    assert (
        TestSimple5._sp_cls_request_dispatcher
        ==
        RequestDispatcher({SampleRequest: "_provide_sample"})
    )


def test_abstract_method():
    class Base(MethodsProvider, ABC):
        @abstractmethod
        @method_handler
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
        class BadDecoratorArg(MethodsProvider):
            @method_handler
            def _provide(self, mediator: Mediator, request: int):
                pass

    with pytest.raises(
        ValueError,
        match=full_match("@static_provision_action decorator cannot be applied twice"),
    ):
        class DoubleDecoration(MethodsProvider):
            @method_handler
            @method_handler
            def _provide(self, mediator: Mediator, request: Request):
                pass

    with pytest.raises(TypeError):
        class SeveralSPA(MethodsProvider):
            @method_handler
            def _provide_one(self, mediator: Mediator, request: Request):
                pass

            @method_handler
            def _provide_two(self, mediator: Mediator, request: Request):
                pass


class Base1(MethodsProvider):
    @method_handler
    def _provide_one(self, mediator: Mediator, request: Request):
        pass


class Base2(MethodsProvider):
    @method_handler
    def _provide_two(self, mediator: Mediator, request: Request):
        pass


def test_inheritance_redefine_spa():
    with pytest.raises(TypeError):
        class RedefineSPAChild(Base1):
            @method_handler
            def _provide_one(self, mediator: Mediator, request: Request):
                pass


def test_inheritance_several_spa():
    with pytest.raises(TypeError):
        class SeveralSPAChild(Base1):
            @method_handler
            def _provide_two(self, mediator: Mediator, request: Request):
                pass

    with pytest.raises(TypeError):
        class Child12(Base1, Base2):
            pass

    with pytest.raises(TypeError):
        class Child21(Base2, Base1):
            pass


def test_inheritance_several_rc():
    class Base3(MethodsProvider):
        @method_handler
        def _provide_one(self, mediator: Mediator, request: SampleRequest):
            pass

    with pytest.raises(TypeError):
        class Child13(Base1, Base3):
            pass

    with pytest.raises(TypeError):
        class Child1(Base1):
            @method_handler
            def _provide_one(self, mediator: Mediator, request: SampleRequest):
                pass
