from dataclasses import dataclass

from pydantic import BaseModel


@dataclass
class Person:
    name: str
    age: float


class PersonDTO(BaseModel):
    name: str
    age: float


person = Person(name="Anna", age=20)
person_dto = PersonDTO.model_validate(person, from_attributes=True)
assert person_dto == PersonDTO(name="Anna", age=20)
