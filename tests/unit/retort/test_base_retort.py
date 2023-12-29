import pytest
from tests_helpers import PlaceholderProvider, full_match_regex_str

from adaptix import Retort
from adaptix._internal.retort.base_retort import BaseRetort


def test_incremental_recipe_empty():
    class ChildNone(BaseRetort):
        pass

    assert ChildNone._full_class_recipe == ()

    class ChildEmpty(BaseRetort):
        recipe = []

    assert ChildEmpty._full_class_recipe == ()


def test_incremental_recipe_single_inheritance():
    class Child1(BaseRetort):
        recipe = (PlaceholderProvider(1), )

    assert Child1._full_class_recipe == (PlaceholderProvider(1), )

    class Child2(Child1):
        recipe = [PlaceholderProvider(2)]

    assert Child2._full_class_recipe == (PlaceholderProvider(2), PlaceholderProvider(1))


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

    assert Diamond23._full_class_recipe == (
        PlaceholderProvider(23),
        PlaceholderProvider(2),
        PlaceholderProvider(3),
        PlaceholderProvider(1),
    )

    assert Diamond32._full_class_recipe == (
        PlaceholderProvider(32),
        PlaceholderProvider(3),
        PlaceholderProvider(2),
        PlaceholderProvider(1),
    )


def test_recipe_access():
    class RetortWithRecipe(Retort):
        recipe = [
            PlaceholderProvider(1),
        ]

    with pytest.raises(AttributeError, match=full_match_regex_str("Can not read 'recipe' attribute")):
        RetortWithRecipe.recipe

    with pytest.raises(AttributeError, match=full_match_regex_str("Can not set 'recipe' attribute")):
        RetortWithRecipe.recipe = []

    with pytest.raises(AttributeError, match=full_match_regex_str("Can not delete 'recipe' attribute")):
        del RetortWithRecipe.recipe

    with_recipe = RetortWithRecipe()

    with pytest.raises(AttributeError, match=full_match_regex_str("Can not read 'recipe' attribute")):
        with_recipe.recipe

    with pytest.raises(AttributeError, match=full_match_regex_str("Can not set 'recipe' attribute")):
        with_recipe.recipe = []

    with pytest.raises(AttributeError, match=full_match_regex_str("Can not delete 'recipe' attribute")):
        del with_recipe.recipe


def test_bad_recipe():
    with pytest.raises(TypeError, match=full_match_regex_str("Recipe attributes must be Iterable[Provider]")):
        class StringItemRecipe(BaseRetort):
            recipe = [
                'hello',
                'world',
            ]
