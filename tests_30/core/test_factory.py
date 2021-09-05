from dataclasses import dataclass, field

from dataclass_factory_30.core import Provider, collect_class_full_recipe
from dataclass_factory_30.high_level.factory import BuiltinFactory


@dataclass
class SP(Provider):
    x: int


class Gen1Factory(BuiltinFactory):
    pass


class Gen2Factory(Gen1Factory):
    recipe = [
        SP(1)
    ]


class Gen3Factory(Gen2Factory):
    recipe: list = [
        SP(2)
    ]


class Gen4Factory(Gen3Factory):
    pass


@dataclass(frozen=True)
class Gen5Factory(Gen4Factory):
    recipe = [
        SP(3)
    ]


@dataclass(frozen=True)
class Gen6Factory(Gen5Factory):
    pass


@dataclass(frozen=True)
class Gen7Factory(Gen6Factory):
    recipe: list = field(
        default_factory=lambda: [SP(4)]
    )


def test_full_recipe():
    b_recipe = collect_class_full_recipe(BuiltinFactory)

    g1_recipe = b_recipe.copy()
    assert collect_class_full_recipe(Gen1Factory) == g1_recipe

    g2_recipe = [SP(1)] + g1_recipe
    assert collect_class_full_recipe(Gen2Factory) == g2_recipe

    g3_recipe = [SP(2)] + g2_recipe
    assert collect_class_full_recipe(Gen3Factory) == g3_recipe

    g4_recipe = g3_recipe.copy()
    assert collect_class_full_recipe(Gen4Factory) == g4_recipe

    g5_recipe = [SP(3)] + g4_recipe
    assert collect_class_full_recipe(Gen5Factory) == g5_recipe

    g6_recipe = g5_recipe.copy()
    assert collect_class_full_recipe(Gen6Factory) == g6_recipe

    g7_recipe = g6_recipe.copy()
    assert collect_class_full_recipe(Gen7Factory) == g7_recipe
