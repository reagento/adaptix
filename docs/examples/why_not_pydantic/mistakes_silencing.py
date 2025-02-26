# mypy: disable-error-code="call-arg"
from pydantic import BaseModel


class SomeModel(BaseModel):
    a: int
    b: int


SomeModel(
    a=1,
    b=2,
    c=3,  # unknown field!
)
