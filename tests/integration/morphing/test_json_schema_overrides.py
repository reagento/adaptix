from dataclasses import dataclass

import pytest
from tests_helpers.morphing import JSONSchemaFork, assert_morphing

from adaptix import Chain, P, ProviderNotFoundError, Retort, dumper, json_schema, loader
from adaptix._internal.definitions import Direction
from adaptix._internal.morphing.facade.func import DIALECT_2020_12, generate_json_schema
from adaptix._internal.morphing.json_schema.definitions import JSONSchema
from adaptix._internal.morphing.json_schema.patch import JSONSchemaPatch
from adaptix._internal.morphing.json_schema.providers import EraseJSONSchema, KeepJSONSchema
from adaptix._internal.morphing.json_schema.schema_model import JSONSchemaType


@dataclass
class Product:
    name: str
    price: float


_PRODUCT_DATA = {"name": "test", "price": 1.5}
_PRODUCT_LOADED = Product(name="test", price=1.5)


def _product_schema(name_prop: dict, price_prop: dict) -> JSONSchemaFork:
    def _make(product_extra: dict = {}) -> dict:  # noqa: B006
        return {
            "$ref": "#/$defs/Product",
            "$schema": DIALECT_2020_12,
            "$defs": {
                "Product": {
                    "title": "Product",
                    "type": "object",
                    "required": ["name", "price"],
                    "properties": {
                        "name": name_prop,
                        "price": price_prop,
                    },
                    **product_extra,
                },
            },
        }

    return JSONSchemaFork(
        input=_make({"additionalProperties": True}),
        output=_make(),
    )


_DEFAULT_SCHEMA = _product_schema({"type": "string"}, {"type": "number"})


def _product_schema_with_str_def(name_prop: dict, price_prop: dict, def_name: str) -> JSONSchemaFork:
    fork = _product_schema(name_prop, price_prop)
    str_def = {def_name: {"type": "string"}}
    return JSONSchemaFork(
        input={**fork.input, "$defs": {**fork.input["$defs"], **str_def}},
        output={**fork.output, "$defs": {**fork.output["$defs"], **str_def}},
    )


def test_json_schema_explicit_replaces_inferred():
    # explicit override is applied verbatim, even though it no longer matches
    # the field's actual (str) load/dump behavior -- that mismatch is the point of this test,
    # so it can't go through assert_morphing's data round-trip + jsonschema validation.
    retort = Retort(recipe=[
        json_schema(P[Product].name, JSONSchema(type=JSONSchemaType.INTEGER)),
    ])
    schema = generate_json_schema(retort, Product, Direction.INPUT)

    assert schema["$defs"]["Product"]["properties"]["name"] == {"type": "integer"}


def test_json_schema_explicit_empty_schema():
    retort = Retort(recipe=[
        json_schema(str, JSONSchema()),
    ])

    assert_morphing(
        retort=retort,
        tp=Product,
        data=_PRODUCT_DATA,
        loaded=_PRODUCT_LOADED,
        json_schema=_product_schema({}, {"type": "number"}),
    )


def test_json_schema_explicit_with_title_and_description():
    retort = Retort(recipe=[
        json_schema(P[Product].price, JSONSchema(title="Price", description="Product price")),
    ])

    assert_morphing(
        retort=retort,
        tp=Product,
        data=_PRODUCT_DATA,
        loaded=_PRODUCT_LOADED,
        json_schema=_product_schema(
            {"type": "string"},
            {"title": "Price", "description": "Product price"},
        ),
    )


def test_keep_json_schema_preserves_inferred_schema():
    retort = Retort(recipe=[json_schema(str, KeepJSONSchema())])

    assert_morphing(
        retort=retort,
        tp=Product,
        data=_PRODUCT_DATA,
        loaded=_PRODUCT_LOADED,
        json_schema=_DEFAULT_SCHEMA,
    )


def test_erase_json_schema_on_loader_raises_error():
    retort = Retort(recipe=[
        loader(str, lambda x: x, json_schema=EraseJSONSchema()),
    ])

    with pytest.raises(ProviderNotFoundError):
        generate_json_schema(retort, Product, Direction.INPUT)


def test_erase_json_schema_on_dumper_raises_error():
    retort = Retort(recipe=[
        dumper(str, lambda x: x, json_schema=EraseJSONSchema()),
    ])

    with pytest.raises(ProviderNotFoundError):
        generate_json_schema(retort, Product, Direction.OUTPUT)


def test_patch_merge_with_adds_description():
    retort = Retort(recipe=[
        json_schema(
            P[Product].name,
            JSONSchemaPatch().merge_with(JSONSchema(description="The product name"), Chain.LAST),
        ),
    ])

    assert_morphing(
        retort=retort,
        tp=Product,
        data=_PRODUCT_DATA,
        loaded=_PRODUCT_LOADED,
        json_schema=_product_schema(
            {"description": "The product name", "type": "string"},
            {"type": "number"},
        ),
    )


def test_patch_merge_with_chain_first_overrides_inferred():
    retort = Retort(recipe=[
        json_schema(
            P[Product].price,
            JSONSchemaPatch().merge_with(JSONSchema(type=JSONSchemaType.STRING), Chain.FIRST),
        ),
    ])
    schema = generate_json_schema(retort, Product, Direction.INPUT)

    assert schema["$defs"]["Product"]["properties"]["price"] == {"type": "string"}


def test_patch_merge_with_chain_last_base_wins_over_conflicting_override():
    retort = Retort(recipe=[
        json_schema(
            P[Product].name,
            JSONSchemaPatch().merge_with(JSONSchema(type=JSONSchemaType.INTEGER), Chain.LAST),
        ),
    ])

    assert_morphing(
        retort=retort,
        tp=Product,
        data=_PRODUCT_DATA,
        loaded=_PRODUCT_LOADED,
        json_schema=_product_schema(
            {"type": "string"},
            {"type": "number"},
        ),
    )


def test_patch_replace_title():
    retort = Retort(recipe=[
        json_schema(
            P[Product].name,
            JSONSchemaPatch().replace("title", lambda _: "CustomTitle"),
        ),
    ])

    assert_morphing(
        retort=retort,
        tp=Product,
        data=_PRODUCT_DATA,
        loaded=_PRODUCT_LOADED,
        json_schema=_product_schema(
            {"title": "CustomTitle", "type": "string"},
            {"type": "number"},
        ),
    )


def test_json_schema_inline_embeds_directly():
    retort = Retort(recipe=[json_schema(str, inline=True)])

    assert_morphing(
        retort=retort,
        tp=Product,
        data=_PRODUCT_DATA,
        loaded=_PRODUCT_LOADED,
        json_schema=_DEFAULT_SCHEMA,
    )


def test_json_schema_not_inline_uses_ref():
    retort = Retort(recipe=[json_schema(str, inline=False)])

    assert_morphing(
        retort=retort,
        tp=Product,
        data=_PRODUCT_DATA,
        loaded=_PRODUCT_LOADED,
        json_schema=_product_schema_with_str_def({"$ref": "#/$defs/str"}, {"type": "number"}, "str"),
    )


def test_json_schema_pinned_ref():
    retort = Retort(recipe=[json_schema(str, ref="MyString", inline=False)])

    assert_morphing(
        retort=retort,
        tp=Product,
        data=_PRODUCT_DATA,
        loaded=_PRODUCT_LOADED,
        json_schema=_product_schema_with_str_def(
            {"$ref": "#/$defs/MyString"}, {"type": "number"}, "MyString",
        ),
    )


def test_loader_custom_json_schema_kwarg_reflected_in_schema():
    retort = Retort(recipe=[
        loader(str, str, json_schema=JSONSchema(type=JSONSchemaType.STRING, title="CustomStr")),
    ])

    assert_morphing(
        retort=retort,
        tp=Product,
        data=_PRODUCT_DATA,
        loaded=_PRODUCT_LOADED,
        json_schema=_product_schema(
            {"title": "CustomStr", "type": "string"},
            {"type": "number"},
        ),
    )


def test_multiple_overrides_on_different_fields():
    retort = Retort(recipe=[
        json_schema(P[Product].name, JSONSchema(title="Name")),
        json_schema(P[Product].price, JSONSchema(title="Price")),
    ])

    assert_morphing(
        retort=retort,
        tp=Product,
        data=_PRODUCT_DATA,
        loaded=_PRODUCT_LOADED,
        json_schema=_product_schema(
            {"title": "Name"},
            {"title": "Price"},
        ),
    )
