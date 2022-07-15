from dataclasses import dataclass

from dataclass_factory_30.factory.basic_factory import IncrementalRecipe
from dataclass_factory_30.provider import Mediator, Provider, Request
from dataclass_factory_30.provider.essential import CannotProvide, T


@dataclass
class Sample(Provider):
    value: int

    def apply_provider(self, mediator: Mediator, request: Request[T]) -> T:
        raise CannotProvide


def test_incremental_recipe_empty():
    class ChildNone(IncrementalRecipe):
        pass

    assert ChildNone._inc_class_recipe == []

    class ChildEmpty(IncrementalRecipe):
        recipe = []

    assert ChildEmpty._inc_class_recipe == []


def test_incremental_recipe_single_inheritance():
    class Child1(IncrementalRecipe):
        recipe = [Sample(1)]

    assert Child1._inc_class_recipe == [Sample(1)]

    class Child2(Child1):
        recipe = [Sample(2)]

    assert Child2._inc_class_recipe == [Sample(2), Sample(1)]


def test_incremental_recipe_diamond_inheritance():
    class Diamond1(IncrementalRecipe):
        recipe = [Sample(1)]

    class Diamond2(Diamond1):
        recipe = [Sample(2)]

    class Diamond3(Diamond1):
        recipe = [Sample(3)]

    class Diamond23(Diamond2, Diamond3):
        recipe = [Sample(23)]

    class Diamond32(Diamond3, Diamond2):
        recipe = [Sample(32)]

    assert Diamond23._inc_class_recipe == [Sample(23), Sample(2), Sample(3), Sample(1)]
    assert Diamond32._inc_class_recipe == [Sample(32), Sample(3), Sample(2), Sample(1)]
