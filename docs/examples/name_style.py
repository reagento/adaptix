from dataclasses import dataclass

from dataclass_factory import Factory, Schema, NameStyle

factory = Factory(default_schema=Schema(
    name_style=NameStyle.camel
))


@dataclass
class Person:
    first_name: str
    last_name: str


person = Person("ivan", "petrov")

serial_person = {
    "FirstName": "ivan",
    "LastName": "petrov"
}

assert factory.dump(person) == serial_person
