from dataclass_factory_30.retort.basic_retort import IncrementalRecipe
from tests_helpers import PlaceholderProvider


def test_incremental_recipe_empty():
    class ChildNone(IncrementalRecipe):
        pass

    assert ChildNone._inc_class_recipe == []

    class ChildEmpty(IncrementalRecipe):
        recipe = []

    assert ChildEmpty._inc_class_recipe == []


def test_incremental_recipe_single_inheritance():
    class Child1(IncrementalRecipe):
        recipe = [PlaceholderProvider(1)]

    assert Child1._inc_class_recipe == [PlaceholderProvider(1)]

    class Child2(Child1):
        recipe = [PlaceholderProvider(2)]

    assert Child2._inc_class_recipe == [PlaceholderProvider(2), PlaceholderProvider(1)]


def test_incremental_recipe_diamond_inheritance():
    class Diamond1(IncrementalRecipe):
        recipe = [PlaceholderProvider(1)]

    class Diamond2(Diamond1):
        recipe = [PlaceholderProvider(2)]

    class Diamond3(Diamond1):
        recipe = [PlaceholderProvider(3)]

    class Diamond23(Diamond2, Diamond3):
        recipe = [PlaceholderProvider(23)]

    class Diamond32(Diamond3, Diamond2):
        recipe = [PlaceholderProvider(32)]

    assert Diamond23._inc_class_recipe == [PlaceholderProvider(23), PlaceholderProvider(2),
                                           PlaceholderProvider(3), PlaceholderProvider(1)]

    assert Diamond32._inc_class_recipe == [PlaceholderProvider(32), PlaceholderProvider(3),
                                           PlaceholderProvider(2), PlaceholderProvider(1)]
