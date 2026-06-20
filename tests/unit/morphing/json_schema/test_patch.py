import pytest

from adaptix import Chain
from adaptix._internal.morphing.json_schema.definitions import JSONSchema
from adaptix._internal.morphing.json_schema.patch import JSONSchemaPatch


def apply_patch(patch: JSONSchemaPatch, schema: JSONSchema) -> JSONSchema:
    for patcher in patch.get_patchers():
        schema = patcher(schema)
    return schema


def test_replace_sets_field():
    schema = JSONSchema(title="old")

    result = apply_patch(JSONSchemaPatch().replace("title", lambda _: "new"), schema)

    assert result.title == "new"


def test_replace_receives_old_value():
    schema = JSONSchema(title="base")
    received = []

    apply_patch(JSONSchemaPatch().replace("title", lambda v: received.append(v) or v), schema)

    assert received == ["base"]


def test_replace_omitted_field():
    schema = JSONSchema()

    result = apply_patch(JSONSchemaPatch().replace("description", lambda _: "added"), schema)

    assert result.description == "added"


def test_mutate_copy_does_not_modify_original():
    schema = JSONSchema(required=["a", "b"])

    apply_patch(
        JSONSchemaPatch().mutate_copy("required", lambda lst: lst.append("c")),
        schema,
    )

    assert schema.required == ["a", "b"]


def test_mutate_copy_new_schema_has_mutation():
    schema = JSONSchema(required=["a"])

    result = apply_patch(
        JSONSchemaPatch().mutate_copy("required", lambda lst: lst.append("b")),
        schema,
    )

    assert result.required == ["a", "b"]


def test_mutate_copy_shallow_does_not_deep_copy():
    inner = {"x": [1, 2]}
    schema = JSONSchema(extra_keywords={"nested": inner})

    result = apply_patch(
        JSONSchemaPatch().mutate_copy("extra_keywords", lambda d: d.update({"new_key": "val"})),
        schema,
    )

    assert result.extra_keywords == {"nested": inner, "new_key": "val"}


def test_mutate_deepcopy_does_not_modify_original():
    inner_list = [1, 2]
    schema = JSONSchema(extra_keywords={"items": inner_list})

    apply_patch(
        JSONSchemaPatch().mutate_deepcopy("extra_keywords", lambda d: d["items"].append(99)),
        schema,
    )

    assert inner_list == [1, 2]


def test_mutate_deepcopy_inner_is_separate_object():
    inner_list = [1, 2]
    schema = JSONSchema(extra_keywords={"items": inner_list})

    result = apply_patch(
        JSONSchemaPatch().mutate_deepcopy("extra_keywords", lambda _: None),
        schema,
    )

    assert result.extra_keywords["items"] == [1, 2]
    assert result.extra_keywords["items"] is not inner_list


def test_merge_with_chain_first_override_wins():
    base = JSONSchema(title="base", description="base_desc")
    override = JSONSchema(description="new_desc")

    result = apply_patch(JSONSchemaPatch().merge_with(override, Chain.FIRST), base)

    assert result.title == "base"
    assert result.description == "new_desc"


def test_merge_with_chain_last_base_wins():
    base = JSONSchema(title="base", description="base_desc")
    override = JSONSchema(description="new_desc")

    result = apply_patch(JSONSchemaPatch().merge_with(override, Chain.LAST), base)

    assert result.title == "base"
    assert result.description == "base_desc"


def test_merge_with_chain_first_omitted_field_does_not_overwrite():
    base = JSONSchema(title="keep_me")
    override = JSONSchema(description="added")

    result = apply_patch(JSONSchemaPatch().merge_with(override, Chain.FIRST), base)

    assert result.title == "keep_me"
    assert result.description == "added"


def test_merge_with_default_chain_is_first():
    base = JSONSchema(title="base")
    override = JSONSchema(title="override")

    result = apply_patch(JSONSchemaPatch().merge_with(override), base)

    assert result.title == "override"


def test_merge_with_empty_override_leaves_base_unchanged():
    base = JSONSchema(title="t", description="d")

    result = apply_patch(JSONSchemaPatch().merge_with(JSONSchema(), Chain.FIRST), base)

    assert result.title == "t"
    assert result.description == "d"


def test_multiple_patchers_applied_in_order():
    schema = JSONSchema(title="a")
    patch = (
        JSONSchemaPatch()
        .replace("title", lambda t: t + "b")
        .replace("title", lambda t: t + "c")
    )

    result = apply_patch(patch, schema)

    assert result.title == "abc"


def test_builder_is_immutable():
    original = JSONSchemaPatch()

    extended = original.replace("title", lambda _: "x")

    assert list(original.get_patchers()) == []
    assert len(list(extended.get_patchers())) == 1


def test_builder_each_method_returns_new_instance():
    p = JSONSchemaPatch()
    instances = [
        p,
        p.replace("title", lambda _: "x"),
        p.mutate_copy("required", lambda lst: lst),
        p.merge_with(JSONSchema()),
        p.mutate_deepcopy("extra_keywords", lambda d: d),
    ]
    assert len(set(instances)) == len(instances)


def test_get_patchers_empty_by_default():
    assert list(JSONSchemaPatch().get_patchers()) == []


def test_get_patchers_returns_all_patchers():
    patch = (
        JSONSchemaPatch()
        .replace("title", lambda _: "x")
        .replace("description", lambda _: "y")
        .merge_with(JSONSchema())
    )

    assert len(list(patch.get_patchers())) == 3
