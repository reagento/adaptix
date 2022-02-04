from dataclass_factory_30.utils import SingletonMeta


def test_simple():
    class MySingleton(metaclass=SingletonMeta):
        pass

    instance1 = MySingleton()
    instance2 = MySingleton()

    assert instance1 is instance2
    assert instance1 == instance2
