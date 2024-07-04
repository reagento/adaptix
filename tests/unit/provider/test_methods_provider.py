from abc import ABC, abstractmethod

import pytest

from adaptix import Mediator, Request
from adaptix._internal.provider.methods_provider import MethodsProvider, method_handler
from adaptix._internal.provider.request_checkers import AlwaysTrueRequestChecker


class SampleRequest(Request):
    pass


def test_simple():
    class TestSimple1(MethodsProvider):
        @method_handler
        def provide_sample(self, mediator: Mediator, request: SampleRequest):
            pass

    instance = TestSimple1()
    assert (
        instance.get_request_handlers() == [
            (SampleRequest, AlwaysTrueRequestChecker(), instance.provide_sample),
        ]
    )


def test_abstract_method():
    class Base(MethodsProvider, ABC):
        @abstractmethod
        @method_handler
        def provide_sample(self, mediator: Mediator, request: SampleRequest):
            pass

    class Child(Base):
        def provide_sample(self, mediator: Mediator, request: SampleRequest):
            pass

    instance = Child()
    assert (
        instance.get_request_handlers() == [
            (SampleRequest, AlwaysTrueRequestChecker(), instance.provide_sample),
        ]
    )


def test_error_raising_with_one_class():
    with pytest.raises(TypeError):
        class BadDecoratorArg(MethodsProvider):
            @method_handler
            def provide(self, mediator: Mediator, request: int):
                pass

    with pytest.raises(TypeError):
        class SeveralSPA(MethodsProvider):
            @method_handler
            def provide_one(self, mediator: Mediator, request: Request):
                pass

            @method_handler
            def provide_two(self, mediator: Mediator, request: Request):
                pass


class Base1(MethodsProvider):
    @method_handler
    def provide_one(self, mediator: Mediator, request: Request):
        pass


class Base2(MethodsProvider):
    @method_handler
    def provide_two(self, mediator: Mediator, request: Request):
        pass


def test_inheritance_redefine_spa():
    with pytest.raises(TypeError):
        class RedefineSPAChild(Base1):
            @method_handler
            def provide_one(self, mediator: Mediator, request: Request):
                pass


def test_inheritance_several_spa():
    with pytest.raises(TypeError):
        class SeveralSPAChild(Base1):
            @method_handler
            def provide_two(self, mediator: Mediator, request: Request):
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
        def provide_one(self, mediator: Mediator, request: SampleRequest):
            pass

    with pytest.raises(TypeError):
        class Child13(Base1, Base3):
            pass

    with pytest.raises(TypeError):
        class Child1(Base1):
            @method_handler
            def provide_one(self, mediator: Mediator, request: SampleRequest):
                pass
