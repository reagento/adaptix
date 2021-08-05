from dataclasses import dataclass, field

from dataclass_factory_30.core import Provider
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
    b_fac = BuiltinFactory()
    b_recipe = b_fac._full_recipe()

    g1_recipe = b_recipe.copy()
    assert Gen1Factory()._full_recipe() == g1_recipe

    g2_recipe = [SP(1)] + g1_recipe
    assert Gen2Factory()._full_recipe() == g2_recipe

    g3_recipe = [SP(2)] + g2_recipe
    assert Gen3Factory()._full_recipe() == g3_recipe

    g4_recipe = g3_recipe.copy()
    assert Gen4Factory()._full_recipe() == g4_recipe

    g5_recipe = [SP(3)] + g4_recipe
    assert Gen5Factory()._full_recipe() == g5_recipe

    g6_recipe = g5_recipe.copy()
    assert Gen6Factory()._full_recipe() == g6_recipe

    g7_recipe = [SP(4)] + g6_recipe
    assert Gen7Factory()._full_recipe() == g7_recipe

    assert (
        Gen1Factory([SP(10)])._full_recipe()
        ==
        b_recipe + [SP(10)]
    )
