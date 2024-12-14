from dataclasses import dataclass, field
from typing import Generic, TypeVar, Union

from ...provider.loc_stack_filtering import LocStack
from ...type_tools.fwd_ref import FwdRef
from .schema_model import BaseJSONSchema

T = TypeVar("T")

JSONSchemaT = TypeVar("JSONSchemaT")


@dataclass(frozen=True)
class JSONSchemaRef(Generic[JSONSchemaT]):
    value: str
    is_final: bool
    json_schema: JSONSchemaT
    loc_stack: LocStack = field(repr=False)

    def __hash__(self):
        return hash(self.value)


Boolable = Union[T, bool]


class JSONSchema(BaseJSONSchema[JSONSchemaRef[Boolable[FwdRef["JSONSchema"]]], Boolable[FwdRef["JSONSchema"]]]):
    pass


class ResolvedJSONSchema(BaseJSONSchema[str, Boolable[FwdRef["ResolvedJSONSchema"]]]):
    pass

