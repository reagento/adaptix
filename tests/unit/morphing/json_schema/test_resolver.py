import pytest

from adaptix._internal.morphing.json_schema.definitions import JSONSchema, LocalRefSource, RemoteRef
from adaptix._internal.morphing.json_schema.mangling import IndexRefMangler
from adaptix._internal.morphing.json_schema.ref_generator import BuiltinRefGenerator
from adaptix._internal.morphing.json_schema.resolver import (
    BuiltinJSONSchemaResolver,
    CustomJSONSchemaHasher,
    RefMangler,
)
from adaptix._internal.provider.loc_stack_filtering import LocStack
from adaptix._internal.provider.location import TypeHintLoc


def make_src(tp, schema=None, pinned=None):
    if schema is None:
        schema = JSONSchema(title=getattr(tp, "__name__", str(tp)))
    return LocalRefSource(value=pinned, json_schema=schema, loc_stack=LocStack(TypeHintLoc(tp)))


def make_resolver(mangler=None):
    return BuiltinJSONSchemaResolver(
        ref_generator=BuiltinRefGenerator(),
        ref_mangler=mangler or IndexRefMangler(),
    )


PREFIX = "#/$defs/"


class _TypeA:
    pass


class _TypeB:
    pass


def test_single_ref_produces_one_def():
    src = make_src(_TypeA)
    root = JSONSchema(ref=src)

    defs, schemas = make_resolver().resolve([root], local_ref_prefix=PREFIX, occupied_refs=())

    assert list(defs.keys()) == ["_TypeA"]
    assert schemas[0].ref == f"{PREFIX}_TypeA"


def test_remote_ref_passes_through_unchanged():
    root = JSONSchema(ref=RemoteRef("https://example.com/schema"))

    defs, schemas = make_resolver().resolve([root], local_ref_prefix=PREFIX, occupied_refs=())

    assert defs == {}
    assert schemas[0].ref == "https://example.com/schema"


def test_no_refs_produces_empty_defs():
    root = JSONSchema(title="plain")

    defs, schemas = make_resolver().resolve([root], local_ref_prefix=PREFIX, occupied_refs=())

    assert defs == {}
    assert schemas[0].title == "plain"


def test_same_type_twice_deduplicates_to_one_def():
    shared_schema = JSONSchema(title="_TypeA")
    src1 = LocalRefSource(value=None, json_schema=shared_schema, loc_stack=LocStack(TypeHintLoc(_TypeA)))
    src2 = LocalRefSource(value=None, json_schema=shared_schema, loc_stack=LocStack(TypeHintLoc(_TypeA)))
    root1 = JSONSchema(ref=src1)
    root2 = JSONSchema(ref=src2)

    defs, schemas = make_resolver().resolve([root1, root2], local_ref_prefix=PREFIX, occupied_refs=())

    assert len(defs) == 1
    assert schemas[0].ref == schemas[1].ref


def test_different_schemas_same_type_produce_mangled_defs():
    src1 = LocalRefSource(value=None, json_schema=JSONSchema(title="V1"), loc_stack=LocStack(TypeHintLoc(_TypeA)))
    src2 = LocalRefSource(value=None, json_schema=JSONSchema(title="V2"), loc_stack=LocStack(TypeHintLoc(_TypeA)))
    root1 = JSONSchema(ref=src1)
    root2 = JSONSchema(ref=src2)

    defs, schemas = make_resolver().resolve([root1, root2], local_ref_prefix=PREFIX, occupied_refs=())

    assert len(defs) == 2
    assert schemas[0].ref != schemas[1].ref


def test_pinned_ref_used_as_def_key():
    src = make_src(_TypeA, pinned="MyCustomRef")
    root = JSONSchema(ref=src)

    defs, schemas = make_resolver().resolve([root], local_ref_prefix=PREFIX, occupied_refs=())

    assert list(defs.keys()) == ["MyCustomRef"]
    assert schemas[0].ref == f"{PREFIX}MyCustomRef"


def test_pinning_conflict_raises():
    src_a = make_src(_TypeA, schema=JSONSchema(title="A"), pinned="Conflict")
    src_b = make_src(_TypeB, schema=JSONSchema(title="B"), pinned="Conflict")
    root_a = JSONSchema(ref=src_a)
    root_b = JSONSchema(ref=src_b)

    with pytest.raises(ValueError, match="different sub schemas with pinned ref"):
        make_resolver().resolve([root_a, root_b], local_ref_prefix=PREFIX, occupied_refs=())


def test_occupied_refs_forces_mangled_name():
    src = make_src(_TypeA)
    root = JSONSchema(ref=src)

    defs, _ = make_resolver(IndexRefMangler()).resolve([root], local_ref_prefix=PREFIX, occupied_refs=("_TypeA",))

    assert list(defs.keys()) == ["_TypeA-1"]


def test_custom_local_ref_prefix():
    src = make_src(_TypeA)
    root = JSONSchema(ref=src)
    custom_prefix = "#/components/schemas/"

    _, schemas = make_resolver().resolve([root], local_ref_prefix=custom_prefix, occupied_refs=())

    assert schemas[0].ref == f"{custom_prefix}_TypeA"


class _IdentityMangler(RefMangler):
    def mangle_refs(self, occupied_refs, common_ref, sources_groups):
        return {g: common_ref for g in sources_groups}


def test_mangling_failure_raises():
    src1 = LocalRefSource(value=None, json_schema=JSONSchema(title="V1"), loc_stack=LocStack(TypeHintLoc(_TypeA)))
    src2 = LocalRefSource(value=None, json_schema=JSONSchema(title="V2"), loc_stack=LocStack(TypeHintLoc(_TypeA)))
    root1 = JSONSchema(ref=src1)
    root2 = JSONSchema(ref=src2)
    resolver = BuiltinJSONSchemaResolver(BuiltinRefGenerator(), _IdentityMangler())

    with pytest.raises(ValueError, match="cannot mangle some refs"):
        resolver.resolve([root1, root2], local_ref_prefix=PREFIX, occupied_refs=())


def test_multiple_unrelated_refs_produce_separate_defs():
    src_a = make_src(_TypeA)
    src_b = make_src(_TypeB)
    root_a = JSONSchema(ref=src_a)
    root_b = JSONSchema(ref=src_b)

    defs, schemas = make_resolver().resolve([root_a, root_b], local_ref_prefix=PREFIX, occupied_refs=())

    assert len(defs) == 2
    assert len(schemas) == 2


def test_hasher_equal_schemas_are_equal():
    h1 = CustomJSONSchemaHasher(JSONSchema(title="Foo", description="bar"))
    h2 = CustomJSONSchemaHasher(JSONSchema(title="Foo", description="bar"))

    assert h1 == h2
    assert hash(h1) == hash(h2)


def test_hasher_different_schemas_are_not_equal():
    h1 = CustomJSONSchemaHasher(JSONSchema(title="Foo"))
    h2 = CustomJSONSchemaHasher(JSONSchema(title="Bar"))

    assert h1 != h2


def test_hasher_empty_schemas_are_equal():
    h1 = CustomJSONSchemaHasher(JSONSchema())
    h2 = CustomJSONSchemaHasher(JSONSchema())

    assert h1 == h2
    assert hash(h1) == hash(h2)
