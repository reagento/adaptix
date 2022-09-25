import re

import pytest

from dataclass_factory_30.facade import Retort
from dataclass_factory_30.retort import BaseRetort
from tests_helpers import PlaceholderProvider


def test_incremental_recipe_empty():
    class ChildNone(BaseRetort):
        pass

    assert ChildNone._full_class_recipe == []

    class ChildEmpty(BaseRetort):
        recipe = []

    assert ChildEmpty._full_class_recipe == []


def test_incremental_recipe_single_inheritance():
    class Child1(BaseRetort):
        recipe = [PlaceholderProvider(1)]

    assert Child1._full_class_recipe == [PlaceholderProvider(1)]

    class Child2(Child1):
        recipe = [PlaceholderProvider(2)]

    assert Child2._full_class_recipe == [PlaceholderProvider(2), PlaceholderProvider(1)]


def test_incremental_recipe_diamond_inheritance():
    class Diamond1(BaseRetort):
        recipe = [PlaceholderProvider(1)]

    class Diamond2(Diamond1):
        recipe = [PlaceholderProvider(2)]

    class Diamond3(Diamond1):
        recipe = [PlaceholderProvider(3)]

    class Diamond23(Diamond2, Diamond3):
        recipe = [PlaceholderProvider(23)]

    class Diamond32(Diamond3, Diamond2):
        recipe = [PlaceholderProvider(32)]

    assert Diamond23._full_class_recipe == [
        PlaceholderProvider(23),
        PlaceholderProvider(2),
        PlaceholderProvider(3),
        PlaceholderProvider(1),
    ]

    assert Diamond32._full_class_recipe == [
        PlaceholderProvider(32),
        PlaceholderProvider(3),
        PlaceholderProvider(2),
        PlaceholderProvider(1),
    ]


def test_recipe_access():
    class WithRecipe(Retort):
        recipe = [
            PlaceholderProvider(1),
        ]

    with pytest.raises(AttributeError, match=re.escape("Can not read 'recipe' attribute")):
        WithRecipe.recipe

    with pytest.raises(AttributeError, match=re.escape("Can not set 'recipe' attribute")):
        WithRecipe.recipe = []

    with pytest.raises(AttributeError, match=re.escape("Can not delete 'recipe' attribute")):
        del WithRecipe.recipe

    with_recipe = WithRecipe()

    with pytest.raises(AttributeError, match=re.escape("Can not read 'recipe' attribute")):
        with_recipe.recipe

    with pytest.raises(AttributeError, match=re.escape("Can not set 'recipe' attribute")):
        with_recipe.recipe = []

    with pytest.raises(AttributeError, match=re.escape("Can not delete 'recipe' attribute")):
        del with_recipe.recipe


def test_bad_recipe():
    with pytest.raises(TypeError, match=re.escape("Recipe attributes must be List[Provider]")):
        class DictRecipe(BaseRetort):
            recipe = {}

    with pytest.raises(TypeError, match=re.escape("Recipe attributes must be List[Provider]")):
        class StringItemRecipe(BaseRetort):
            recipe = [
                'hello',
                'world',
            ]
