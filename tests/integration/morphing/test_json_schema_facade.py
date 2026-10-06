from dataclasses import dataclass

import pytest
from tests_helpers import raises_exc
from tests_helpers.morphing import JSONSchemaOptItem, assert_morphing

from adaptix import Retort, name_mapping
from adaptix._internal.definitions import Direction
from adaptix._internal.morphing.facade.func import (
    DIALECT_2020_12,
    generate_json_schema,
    generate_json_schemas_namespace,
    load_json_schema,
)
from adaptix._internal.morphing.json_schema.definitions import JSONSchema
from adaptix._internal.morphing.json_schema.mangling import IndexRefMangler
from adaptix._internal.morphing.json_schema.ref_generator import BuiltinRefGenerator
from adaptix._internal.morphing.json_schema.resolver import BuiltinJSONSchemaResolver, RefGenerator
from adaptix._internal.morphing.json_schema.schema_model import JSONSchemaBuiltinFormat
from adaptix.load_error import AggregateLoadError, ExtraFieldsLoadError


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
    data = {"type": "string", "x-custom": "value"}

    raises_exc(
        AggregateLoadError(
            f"while loading model {JSONSchema}",
            [ExtraFieldsLoadError({"x-custom"}, data)],
        ),
        lambda: load_json_schema(data, error_on_extra=True),
    )


def test_load_json_schema_lax_unknown_field_goes_to_extra_keywords():
    schema = load_json_schema({"type": "string", "x-custom": "value"}, error_on_extra=False)

    assert schema.extra_keywords == {"x-custom": "value"}


@dataclass
class SimpleModel:
    name: str
    value: int


@pytest.mark.parametrize(
    "with_dialect_uri",
    [True, False],
    ids=["with_uri", "without_uri"],
)
def test_generate_json_schema_dialect_uri(with_dialect_uri: bool):  # noqa: FBT001
    schema = generate_json_schema(Retort(), SimpleModel, Direction.INPUT, with_dialect_uri=with_dialect_uri)

    assert ("$schema" in schema) == with_dialect_uri


def test_generate_json_schema_matches_full_expected_shape():
    assert_morphing(
        retort=Retort(),
        tp=SimpleModel,
        data={"name": "foo", "value": 1},
        loaded=SimpleModel(name="foo", value=1),
        json_schema={
            "$ref": "#/$defs/SimpleModel",
            "$schema": DIALECT_2020_12,
            "$defs": {
                "SimpleModel": {
                    "title": "SimpleModel",
                    "type": "object",
                    "required": ["name", "value"],
                    "properties": {
                        "name": {"type": "string"},
                        "value": {"type": "integer"},
                    },
                    "additionalProperties": JSONSchemaOptItem(input=True),
                },
            },
        },
    )


def test_generate_json_schema_custom_ref_prefix():
    schema = generate_json_schema(
        Retort(), SimpleModel, Direction.INPUT,
        local_ref_prefix="#/components/schemas/",
    )

    assert schema["$ref"] == "#/components/schemas/SimpleModel"


class _PrefixRefGenerator(RefGenerator):
    def generate_ref(self, json_schema, loc_stack):
        return "Custom" + BuiltinRefGenerator().generate_ref(json_schema, loc_stack)


@pytest.mark.parametrize(
    ["resolver", "occupied_refs", "expected_ref"],
    [
        pytest.param(
            BuiltinJSONSchemaResolver(BuiltinRefGenerator(), IndexRefMangler()),
            ("SimpleModel",),
            "SimpleModel-1",
            id="mangling_of_occupied_ref",
        ),
        pytest.param(
            BuiltinJSONSchemaResolver(_PrefixRefGenerator(), IndexRefMangler()),
            (),
            "CustomSimpleModel",
            id="custom_ref_generator",
        ),
    ],
)
def test_generate_json_schema_custom_resolver(resolver, occupied_refs, expected_ref):
    schema = generate_json_schema(
        Retort(), SimpleModel, Direction.INPUT,
        resolver=resolver,
        occupied_refs=occupied_refs,
    )

    assert schema["$ref"] == f"#/$defs/{expected_ref}"


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


def test_generate_schemas_namespace_deduplicates_shared_types():
    retort = Retort()

    defs, schemas = generate_json_schemas_namespace([
        (retort, Direction.INPUT, Article),
        (retort, Direction.INPUT, Post),
    ])

    assert len(schemas) == 2
    assert defs.keys() == {"Article", "Post", "Tag"}
