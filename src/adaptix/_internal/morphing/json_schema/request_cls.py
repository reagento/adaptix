from dataclasses import dataclass

from ...definitions import Direction
from ...provider.located_request import LocatedRequest
from .definitions import JSONSchema, JSONSchemaRef


@dataclass(frozen=True)
class JSONSchemaContext:
    dialect: str
    direction: Direction


@dataclass(frozen=True)
class WithJSONSchemaContext:
    ctx: JSONSchemaContext


@dataclass(frozen=True)
class GetJSONSchemaRequest(LocatedRequest[JSONSchema], WithJSONSchemaContext):
    pass


@dataclass(frozen=True)
class JSONSchemaRefRequest(LocatedRequest[JSONSchemaRef], WithJSONSchemaContext):
    json_schema: JSONSchema


@dataclass(frozen=True)
class InlineJSONSchemaRequest(LocatedRequest[bool], WithJSONSchemaContext):
    pass


@dataclass(frozen=True)
class GenerateJSONSchemaRequest(LocatedRequest[JSONSchema], WithJSONSchemaContext):
    pass
