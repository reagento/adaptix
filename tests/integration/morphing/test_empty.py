from dataclasses import dataclass

from tests_helpers.morphing import JSONSchemaFork, assert_morphing

from adaptix import Retort


@dataclass
class Empty:
    pass


def test_simple(accum):
    retort = Retort(recipe=[accum])

    assert_morphing(
        retort=retort,
        tp=Empty,
        data={"some_field": 1},
        loaded=Empty(),
        dumped={},
        json_schema={
            "$defs": {
                "Empty": {
                    "additionalProperties": JSONSchemaFork(input=True, output=False),
                    "properties": {},
                    "required": [],
                    "type": "object",
                },
            },
            "$ref": "#/$defs/Empty",
        },
    )
