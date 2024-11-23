from pydantic import BaseModel, ConfigDict, Field


class User(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="allow")

    name: str = Field(alias="full_name")
    age: int


data = {"name": "name_value", "age": 20}
assert User.model_validate(data).model_extra == {}
