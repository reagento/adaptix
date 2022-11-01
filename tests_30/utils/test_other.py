from dataclass_factory_30.utils import SingletonMeta


def test_singleton_simple():
    class MySingleton(metaclass=SingletonMeta):
        pass

    instance1 = MySingleton()
    instance2 = MySingleton()

    assert instance1 is instance2
    assert instance1 == instance2


def test_singleton_repr():
    class MySingleton(metaclass=SingletonMeta):
        pass

    class MyReprSingleton(metaclass=SingletonMeta):
        def __repr__(self):
            return "<CustomSingletonRepr>"

    assert repr(MySingleton()) == "MySingleton()"
    assert repr(MyReprSingleton()) == "<CustomSingletonRepr>"


def test_singleton_hash():
    class MySingleton(metaclass=SingletonMeta):
        pass

    hash(MySingleton())

