from dataclasses import dataclass, field
from typing import Generic, TypeVar, Union

from ...provider.loc_stack_filtering import LocStack
from .schema_model import BaseJSONSchema

T = TypeVar("T")

JSONSchemaT = TypeVar("JSONSchemaT")


@dataclass(frozen=True)
class JSONSchemaRef(Generic[JSONSchemaT]):
    value: str
    is_final: bool
    json_schema: JSONSchemaT = field(repr=False)
    loc_stack: LocStack = field(repr=False)

    def __hash__(self):
        return hash(self.value)


Boolable = Union[T, bool]


class JSONSchema(BaseJSONSchema[JSONSchemaRef[Boolable["JSONSchema"]], Boolable["JSONSchema"]]):
    pass


class ResolvedJSONSchema(BaseJSONSchema[str, Boolable["ResolvedJSONSchema"]]):
    pass

