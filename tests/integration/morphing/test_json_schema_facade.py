from dataclasses import dataclass
from typing import Any, Optional

import pytest
from tests_helpers.structure_tools import EXISTS, NOT_EXISTS, assert_structure

from adaptix import Retort
from adaptix._internal.definitions import Direction
from adaptix._internal.morphing.facade.func import (
    generate_json_schema,
    generate_json_schemas_namespace,
    load_json_schema,
)
from adaptix._internal.morphing.json_schema.definitions import JSONSchema
from adaptix._internal.morphing.json_schema.mangling import IndexRefMangler
from adaptix._internal.morphing.json_schema.ref_generator import BuiltinRefGenerator
from adaptix._internal.morphing.json_schema.resolver import BuiltinJSONSchemaResolver
from adaptix._internal.morphing.json_schema.schema_model import (
    JSONSchemaBuiltinFormat,
    JSONSchemaType,
)
from adaptix.load_error import AggregateLoadError

DIALECT_URI = "https://json-schema.org/draft/2020-12/schema"


@pytest.mark.parametrize(
    ["raw", "expected"],
    [
        ("null", JSONSchemaType.NULL),
        ("boolean", JSONSchemaType.BOOLEAN),
        ("object", JSONSchemaType.OBJECT),
        ("array", JSONSchemaType.ARRAY),
        ("number", JSONSchemaType.NUMBER),
        ("integer", JSONSchemaType.INTEGER),
        ("string", JSONSchemaType.STRING),
    ],
)
def test_load_json_schema_type_enum_values(raw: str, expected: JSONSchemaType):
    schema = load_json_schema({"type": raw})

    assert schema.type == expected


@pytest.mark.parametrize(
    ["schema_data", "expected"],
    [
        (
            {"type": "string", "title": "MyStr", "description": "A string"},
            JSONSchema(type=JSONSchemaType.STRING, title="MyStr", description="A string"),
        ),
        (
            {"type": "string", "format": "date-time"},
            JSONSchema(type=JSONSchemaType.STRING, format=JSONSchemaBuiltinFormat.DATE_TIME),
        ),
        (
            {"type": "string", "format": "my-custom-format"},
            JSONSchema(type=JSONSchemaType.STRING, format="my-custom-format"),
        ),
        (
            {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "age": {"type": "integer"},
                },
                "required": ["name"],
            },
            JSONSchema(
                type=JSONSchemaType.OBJECT,
                properties={
                    "name": JSONSchema(type=JSONSchemaType.STRING),
                    "age": JSONSchema(type=JSONSchemaType.INTEGER),
                },
                required=["name"],
            ),
        ),
        (
            {"anyOf": [{"type": "string"}, {"type": "integer"}]},
            JSONSchema(any_of=[
                JSONSchema(type=JSONSchemaType.STRING),
                JSONSchema(type=JSONSchemaType.INTEGER),
            ]),
        ),
    ],
)
def test_load_json_schema_parses_dict_to_object(schema_data, expected):
    schema = load_json_schema(schema_data)

    assert schema == expected


def test_load_json_schema_strict_unknown_field_raises():
    with pytest.raises(AggregateLoadError):
        load_json_schema({"type": "string", "x-custom": "value"}, error_on_extra=True)


def test_load_json_schema_lax_unknown_field_goes_to_extra_keywords():
    schema = load_json_schema({"type": "string", "x-custom": "value"}, error_on_extra=False)

    assert schema.extra_keywords == {"x-custom": "value"}


def test_load_json_schema_empty_dict():
    schema = load_json_schema({})

    assert schema == JSONSchema()


@dataclass
class SimpleModel:
    name: str
    value: int


@dataclass
class ModelWithOptional:
    required_field: str
    optional_field: Optional[str] = None


@pytest.mark.parametrize(
    ["with_dialect_uri", "expected_schema"],
    [
        (True, DIALECT_URI),
        (False, NOT_EXISTS),
    ],
    ids=["with_uri", "without_uri"],
)
def test_generate_json_schema_dialect_uri(with_dialect_uri: bool, expected_schema: Any):  # noqa: FBT001
    schema = generate_json_schema(Retort(), SimpleModel, Direction.INPUT, with_dialect_uri=with_dialect_uri)

    assert_structure(schema, {"$schema": expected_schema})


def test_generate_json_schema_top_level_keys():
    schema = generate_json_schema(Retort(), SimpleModel, Direction.INPUT)

    assert_structure(schema, {
        "$schema": EXISTS,
        "$ref": EXISTS,
        "$defs": {
            "SimpleModel": EXISTS,
        },
    }, strict=True)


def test_generate_json_schema_custom_ref_prefix():
    schema = generate_json_schema(
        Retort(), SimpleModel, Direction.INPUT,
        local_ref_prefix="#/components/schemas/",
    )

    assert_structure(schema, {"$ref": "#/components/schemas/SimpleModel"})


def test_generate_json_schema_occupied_refs_triggers_mangling():
    schema = generate_json_schema(
        Retort(), SimpleModel, Direction.INPUT,
        occupied_refs=("SimpleModel",),
        resolver=BuiltinJSONSchemaResolver(BuiltinRefGenerator(), IndexRefMangler()),
    )

    assert_structure(schema, {
        "$defs": {
            "SimpleModel": NOT_EXISTS,
            "SimpleModel-1": EXISTS,
        },
    })


def test_generate_json_schema_custom_resolver():
    schema = generate_json_schema(
        Retort(), SimpleModel, Direction.INPUT,
        resolver=BuiltinJSONSchemaResolver(BuiltinRefGenerator(), IndexRefMangler()),
    )

    assert_structure(schema, {"$defs": {"SimpleModel": EXISTS}})


def test_generate_json_schema_optional_field_not_required_on_input():
    input_schema = generate_json_schema(Retort(), ModelWithOptional, Direction.INPUT)
    output_schema = generate_json_schema(Retort(), ModelWithOptional, Direction.OUTPUT)

    # Input schema: only required_field is required (optional_field has default)
    assert_structure(input_schema, {
        "$defs": {
            "ModelWithOptional": {
                "required": ["required_field"],
            },
        },
    })

    # Output schema: both fields are required (dumping doesn't care about defaults)
    assert_structure(output_schema, {
        "$defs": {
            "ModelWithOptional": {
                "required": ["required_field", "optional_field"],
            },
        },
    })


@dataclass
class Tag:
    label: str


@dataclass
class Article:
    title: str
    tag: Tag


@dataclass
class Post:
    body: str
    tag: Tag


def _namespace_query():
    retort = Retort()
    return [(retort, Direction.INPUT, Article), (retort, Direction.INPUT, Post)]


@pytest.mark.parametrize(
    "resolver",
    [
        pytest.param(None, id="default"),
        pytest.param(
            BuiltinJSONSchemaResolver(BuiltinRefGenerator(), IndexRefMangler()),
            id="custom_resolver",
        ),
    ],
)
def test_generate_schemas_namespace_deduplicates_shared_types(resolver):
    query = _namespace_query()
    kwargs = {"resolver": resolver} if resolver else {}

    defs, schemas = generate_json_schemas_namespace(query, **kwargs)

    assert len(schemas) == 2

    assert_structure(defs, {
        "Article": EXISTS,
        "Post": EXISTS,
        "Tag": EXISTS,
    }, strict=True)


@pytest.mark.parametrize(
    "with_dialect_uri",
    [
        pytest.param(True, id="with_uri"),
        pytest.param(False, id="without_uri"),
    ],
)
def test_generate_schemas_namespace_dialect_uri(with_dialect_uri: bool):  # noqa: FBT001
    query = _namespace_query()
    _, schemas = generate_json_schemas_namespace(query, with_dialect_uri=with_dialect_uri)

    expected_schema = DIALECT_URI if with_dialect_uri else NOT_EXISTS
    for schema in schemas:
        assert_structure(schema, {"$schema": expected_schema, "$ref": EXISTS})


def test_generate_schemas_namespace_custom_ref_prefix():
    query = _namespace_query()
    _, schemas = generate_json_schemas_namespace(
        query, local_ref_prefix="#/components/schemas/",
    )

    assert_structure(schemas, [
        {"$ref": "#/components/schemas/Article"},
        {"$ref": "#/components/schemas/Post"},
    ])
