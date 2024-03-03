from dataclasses import dataclass

from adaptix import NameStyle, Retort, name_mapping


@dataclass
class Person:
    first_name: str
    last_name: str


retort = Retort(
    recipe=[
        name_mapping(
            Person,
            name_style=NameStyle.CAMEL,
        ),
    ],
)

data = {
    "firstName": "Richard",
    "lastName": "Stallman",
}
event = retort.load(data, Person)
assert event == Person(first_name="Richard", last_name="Stallman")
assert retort.dump(event) == data
