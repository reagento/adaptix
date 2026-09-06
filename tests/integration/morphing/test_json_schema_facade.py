from dataclasses import dataclass
from typing import Optional

import pytest
from tests_helpers.morphing import JSONSchemaFork, assert_morphing

from adaptix import Retort, name_mapping
from adaptix._internal.definitions import Direction
from adaptix._internal.morphing.facade.func import (
    DIALECT_2020_12 as DIALECT_URI,
    generate_json_schema,
    generate_json_schemas_namespace,
    load_json_schema,
)
from adaptix._internal.morphing.json_schema.mangling import IndexRefMangler
from adaptix._internal.morphing.json_schema.ref_generator import BuiltinRefGenerator
from adaptix._internal.morphing.json_schema.resolver import BuiltinJSONSchemaResolver
from adaptix._internal.morphing.json_schema.schema_model import JSONSchemaBuiltinFormat
from adaptix.load_error import AggregateLoadError


@pytest.mark.parametrize(
    ["raw", "expected"],
    [
        ("date-time", JSONSchemaBuiltinFormat.DATE_TIME),
        ("my-custom-format", "my-custom-format"),
    ],
)
def test_load_json_schema_format_uses_builtin_enum_or_falls_back_to_str(raw, expected):
    schema = load_json_schema({"type": "string", "format": raw})

    assert schema.format == expected


def test_load_json_schema_strict_unknown_field_raises():
    with pytest.raises(AggregateLoadError):
        load_json_schema({"type": "string", "x-custom": "value"}, error_on_extra=True)


def test_load_json_schema_lax_unknown_field_goes_to_extra_keywords():
    schema = load_json_schema({"type": "string", "x-custom": "value"}, error_on_extra=False)

    assert schema.extra_keywords == {"x-custom": "value"}


@dataclass
class SimpleModel:
    name: str
    value: int


@dataclass
class ModelWithOptional:
    required_field: str
    optional_field: Optional[str] = None


@pytest.mark.parametrize(
    "with_dialect_uri",
    [True, False],
    ids=["with_uri", "without_uri"],
)
def test_generate_json_schema_dialect_uri(with_dialect_uri: bool):  # noqa: FBT001
    schema = generate_json_schema(Retort(), SimpleModel, Direction.INPUT, with_dialect_uri=with_dialect_uri)

    assert ("$schema" in schema) == with_dialect_uri


def test_generate_json_schema_matches_full_expected_shape():
    def _make(extra: dict) -> dict:
        return {
            "$ref": "#/$defs/SimpleModel",
            "$schema": DIALECT_URI,
            "$defs": {
                "SimpleModel": {
                    "title": "SimpleModel",
                    "type": "object",
                    "required": ["name", "value"],
                    "properties": {
                        "name": {"type": "string"},
                        "value": {"type": "integer"},
                    },
                    **extra,
                },
            },
        }

    assert_morphing(
        retort=Retort(),
        tp=SimpleModel,
        data={"name": "foo", "value": 1},
        loaded=SimpleModel(name="foo", value=1),
        json_schema=JSONSchemaFork(
            input=_make({"additionalProperties": True}),
            output=_make({}),
        ),
    )


def test_generate_json_schema_custom_ref_prefix():
    schema = generate_json_schema(
        Retort(), SimpleModel, Direction.INPUT,
        local_ref_prefix="#/components/schemas/",
    )

    assert schema["$ref"] == "#/components/schemas/SimpleModel"


def test_generate_json_schema_occupied_refs_triggers_mangling():
    schema = generate_json_schema(
        Retort(), SimpleModel, Direction.INPUT,
        occupied_refs=("SimpleModel",),
        resolver=BuiltinJSONSchemaResolver(BuiltinRefGenerator(), IndexRefMangler()),
    )

    assert "SimpleModel" not in schema["$defs"]
    assert "SimpleModel-1" in schema["$defs"]


def test_generate_json_schema_custom_resolver():
    schema = generate_json_schema(
        Retort(), SimpleModel, Direction.INPUT,
        resolver=BuiltinJSONSchemaResolver(BuiltinRefGenerator(), IndexRefMangler()),
    )

    assert "SimpleModel" in schema["$defs"]


def test_generate_json_schema_optional_field_not_required_on_input():
    def _make(required: list, extra: dict) -> dict:
        return {
            "$ref": "#/$defs/ModelWithOptional",
            "$schema": DIALECT_URI,
            "$defs": {
                "ModelWithOptional": {
                    "title": "ModelWithOptional",
                    "type": "object",
                    "required": required,
                    "properties": {
                        "required_field": {"type": "string"},
                        "optional_field": {
                            "default": None,
                            "anyOf": [{"type": "string"}, {"type": "null"}],
                        },
                    },
                    **extra,
                },
            },
        }

    assert_morphing(
        retort=Retort(),
        tp=ModelWithOptional,
        data={"required_field": "x"},
        loaded=ModelWithOptional(required_field="x"),
        dumped={"required_field": "x", "optional_field": None},
        json_schema=JSONSchemaFork(
            # Input schema: only required_field is required (optional_field has a default)
            input=_make(["required_field"], {"additionalProperties": True}),
            # Output schema: both fields are required (dumping doesn't care about defaults)
            output=_make(["required_field", "optional_field"], {}),
        ),
    )


@dataclass
class ListItem:
    x: int
    y: int


@dataclass
class ListModel:
    a: ListItem
    b: ListItem


def test_generate_json_schema_prefix_items_dedupes_shared_ref():
    retort = Retort(recipe=[name_mapping(ListModel, as_list=True)])

    schema = generate_json_schema(retort, ListModel, Direction.INPUT)

    assert schema["$defs"]["ListModel"]["prefixItems"] == [
        {"$ref": "#/$defs/ListItem"},
        {"$ref": "#/$defs/ListItem"},
    ]
    assert "ListItem" in schema["$defs"]


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
    assert defs.keys() == {"Article", "Post", "Tag"}


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

    for schema in schemas:
        assert ("$schema" in schema) == with_dialect_uri
        assert "$ref" in schema


def test_generate_schemas_namespace_custom_ref_prefix():
    query = _namespace_query()
    _, schemas = generate_json_schemas_namespace(
        query, local_ref_prefix="#/components/schemas/",
    )

    assert [schema["$ref"] for schema in schemas] == [
        "#/components/schemas/Article",
        "#/components/schemas/Post",
    ]
