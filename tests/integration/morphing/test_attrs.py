from attr import Factory, define, field
from tests_helpers.morphing import JSONSchemaFork, assert_morphing

from adaptix import Retort, name_mapping


@define
class Coordinates:
    x: int
    y: int


def test_coordinates(accum):
    retort = Retort(recipe=[accum])

    assert_morphing(
        retort=retort,
        tp=Coordinates,
        data={"x": 1, "y": 2},
        loaded=Coordinates(x=1, y=2),
        dumped={"x": 1, "y": 2},
        json_schema={
            "$defs": {
                "Coordinates": {
                    "additionalProperties": JSONSchemaFork(input=True, output=False),
                    "properties": {
                        "x": {"type": "integer"},
                        "y": {"type": "integer"},
                    },
                    "required": ["x", "y"],
                    "type": "object",
                },
            },
            "$ref": "#/$defs/Coordinates",
        },
    )


@define
class WithDependentFactory:
    x = field(default=Factory(list))
    y = field(default=Factory(lambda self: set(self.x), takes_self=True))


def test_with_dependent_factory(accum):
    retort = Retort(recipe=[accum])

    loader = retort.get_loader(WithDependentFactory)
    assert loader({}) == WithDependentFactory()

    loader = retort.get_loader(WithDependentFactory)
    assert loader({"x": [1, 2, 3]}) == WithDependentFactory(x=[1, 2, 3], y={1, 2, 3})

    loader = retort.get_loader(WithDependentFactory)
    assert loader({"x": [1, 2, 3], "y": {2, 3}}) == WithDependentFactory(x=[1, 2, 3], y={2, 3})

    dumper = retort.get_dumper(WithDependentFactory)
    assert dumper(WithDependentFactory()) == {"x": [], "y": set()}

    dumper = retort.get_dumper(WithDependentFactory)
    assert dumper(WithDependentFactory(x=[1, 2, 3], y={2, 3})) == {"x": [1, 2, 3], "y": {2, 3}}


def test_with_dependent_factory_skipping(accum):
    retort = Retort(recipe=[accum, name_mapping(omit_default=True)])

    dumper = retort.get_dumper(WithDependentFactory)
    assert dumper(WithDependentFactory(x=[1, 2, 3], y={2, 3})) == {"x": [1, 2, 3], "y": {2, 3}}

    dumper = retort.get_dumper(WithDependentFactory)
    assert dumper(WithDependentFactory(x=[1, 2, 3], y={1, 2, 3})) == {"x": [1, 2, 3]}
