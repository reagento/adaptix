from dataclasses import dataclass

from tests_helpers.morphing import JSONSchemaFork, assert_morphing

from adaptix import Retort


@dataclass
class Book:
    title: str
    price: int
    author: str = "Unknown author"


def test_readme(accum):
    retort = Retort(recipe=[accum])

    assert_morphing(
        retort=retort,
        tp=Book,
        data={"title": "Fahrenheit 451", "price": 100},
        loaded=Book(title="Fahrenheit 451", price=100),
        dumped={"title": "Fahrenheit 451", "price": 100, "author": "Unknown author"},
        json_schema={
            "$defs": {
                "Book": {
                    "additionalProperties": JSONSchemaFork(input=True, output=False),
                    "properties": {
                        "author": {"type": "string", "default": "Unknown author"},
                        "price": {"type": "integer"},
                        "title": {"type": "string"},
                    },
                    "required": JSONSchemaFork(
                        input=["title", "price"],
                        output=["title", "price", "author"],
                    ),
                    "type": "object",
                },
            },
            "$ref": "#/$defs/Book",
        },
    )
