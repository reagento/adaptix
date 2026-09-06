import pytest

from adaptix import Omitted
from adaptix._internal.morphing.json_schema.definitions import JSONSchema, RemoteRef, ResolvedJSONSchema
from adaptix._internal.morphing.json_schema.schema_tools import (
    approx_hash_json_schema,
    replace_json_schema_ref,
    traverse_json_schema,
)


def test_traverse_items_yields_root_and_item():
    item = JSONSchema(title="Item")
    root = JSONSchema(items=item)

    result = list(traverse_json_schema(root))

    assert result == [root, item]


def test_traverse_not_yields_root_and_subschema():
    sub = JSONSchema(title="sub")
    root = JSONSchema(not_=sub)

    result = list(traverse_json_schema(root))

    assert result == [root, sub]


def test_traverse_bool_schema_not_yielded():
    bool_schema = True
    result = list(traverse_json_schema(bool_schema))

    assert result == []


def test_traverse_nested_deep_visits_all_levels():
    leaf = JSONSchema(title="leaf")
    mid = JSONSchema(items=leaf)
    root = JSONSchema(items=mid)

    result = list(traverse_json_schema(root))

    assert result == [root, mid, leaf]


def test_traverse_properties_yields_root_and_all_values():
    prop_a = JSONSchema(title="A")
    prop_b = JSONSchema(title="B")
    root = JSONSchema(properties={"a": prop_a, "b": prop_b})

    result = list(traverse_json_schema(root))

    assert result == [root, prop_a, prop_b]


def test_traverse_all_of_yields_root_and_all_elements():
    s1, s2, s3 = JSONSchema(title="1"), JSONSchema(title="2"), JSONSchema(title="3")
    root = JSONSchema(all_of=[s1, s2, s3])

    result = list(traverse_json_schema(root))

    assert result == [root, s1, s2, s3]


def test_traverse_any_of_yields_root_and_all_elements():
    s1, s2 = JSONSchema(title="x"), JSONSchema(title="y")
    root = JSONSchema(any_of=[s1, s2])

    result = list(traverse_json_schema(root))

    assert result == [root, s1, s2]


@pytest.mark.parametrize(
    "field_name",
    ["content_schema", "if_", "then", "else_", "contains", "additional_properties", "property_names"],
)
def test_traverse_single_nested_schema_field(field_name):
    child = JSONSchema(title="child")
    root = JSONSchema(**{field_name: child})

    result = list(traverse_json_schema(root))

    assert result == [root, child]


@pytest.mark.parametrize(
    "field_name",
    ["one_of", "prefix_items"],
)
def test_traverse_sequence_nested_schema_field(field_name):
    child1 = JSONSchema(title="child1")
    child2 = JSONSchema(title="child2")
    root = JSONSchema(**{field_name: [child1, child2]})

    result = list(traverse_json_schema(root))

    assert result == [root, child1, child2]


@pytest.mark.parametrize(
    "field_name",
    ["pattern_properties", "dependent_schemas", "defs"],
)
def test_traverse_mapping_nested_schema_field(field_name):
    child = JSONSchema(title="child")
    root = JSONSchema(**{field_name: {"key": child}})

    result = list(traverse_json_schema(root))

    assert result == [root, child]


@pytest.mark.parametrize(
    ["s1", "s2"],
    [
        (JSONSchema(title="foo", description="bar"), JSONSchema(title="foo", description="bar")),
        (JSONSchema(), JSONSchema()),
        (JSONSchema(extra_keywords={"a": 1, "b": 2}), JSONSchema(extra_keywords={"b": 2, "a": 1})),
    ],
    ids=["equal_fields", "empty", "extra_keywords_order_independent"],
)
def test_hash_equal_schemas_same_hash(s1, s2):
    assert approx_hash_json_schema(s1) == approx_hash_json_schema(s2)


def test_hash_different_title_different_hash():
    s1 = JSONSchema(title="foo")
    s2 = JSONSchema(title="bar")

    assert approx_hash_json_schema(s1) != approx_hash_json_schema(s2)


@pytest.mark.parametrize("value", [True, False])
def test_hash_bool_schema(value):
    assert approx_hash_json_schema(value) == hash(value)


def test_hash_nested_schema_field_contributes():
    s_with_items = JSONSchema(items=JSONSchema(title="Item"))
    s_without = JSONSchema()

    assert approx_hash_json_schema(s_with_items) != approx_hash_json_schema(s_without)


def test_replace_remote_ref_passes_through():
    root = JSONSchema(ref=RemoteRef("https://example.com/schema"))

    result = replace_json_schema_ref(root, "#/$defs/", {})

    assert result.ref == "https://example.com/schema"


def test_replace_no_ref_stays_omitted():
    root = JSONSchema(title="plain")

    result = replace_json_schema_ref(root, "#/$defs/", {})

    assert isinstance(result.ref, Omitted)


@pytest.mark.parametrize("value", [True, False])
def test_replace_bool_schema_returns_bool(value):
    assert replace_json_schema_ref(value, "#/$defs/", {}) is value


def test_replace_returns_resolved_json_schema_type():
    root = JSONSchema(title="plain")

    result = replace_json_schema_ref(root, "#/$defs/", {})

    assert isinstance(result, ResolvedJSONSchema)
