import pytest

from dataclass_factory_30.utils import ClassDispatcher


class Cls1:
    pass


class Cls2(Cls1):
    pass


class Cls3(Cls2):
    pass


def test_equal():
    assert ClassDispatcher({int: 1, str: 2}) == ClassDispatcher({str: 2, int: 1})


def test_dispatch_one():
    with pytest.raises(KeyError):
        ClassDispatcher().dispatch(Cls1)

    dispatcher = ClassDispatcher({Cls1: 10})

    assert dispatcher.dispatch(Cls1) == 10
    assert dispatcher.dispatch(Cls2) == 10

    with pytest.raises(KeyError):
        dispatcher.dispatch(str)


def test_dispatch_parent():
    dispatcher = ClassDispatcher({Cls1: 1, Cls2: 2})

    assert dispatcher.dispatch(Cls1) == 1
    assert dispatcher.dispatch(Cls2) == 2

    assert dispatcher.dispatch(Cls3) == 2

    with pytest.raises(KeyError):
        dispatcher.dispatch(str)


class BaseLeft:
    pass


class BaseRight:
    pass


class Child(BaseLeft, BaseRight):
    pass


def test_dispatch_multi():
    dispatcher1 = ClassDispatcher({BaseLeft: 1, BaseRight: 2})
    assert dispatcher1.dispatch(Child) == 1

    dispatcher2 = ClassDispatcher({BaseRight: 2, BaseLeft: 1})
    assert dispatcher2.dispatch(Child) == 1
