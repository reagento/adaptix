from collections.abc import Iterable, Mapping, Sequence
from dataclasses import fields
from typing import Any, Optional, TypeVar, overload

from ...common import TypeHint
from ...definitions import Direction
from ...name_style import NameStyle
from ..json_schema.definitions import ResolvedJSONSchema
from ..json_schema.mangling import CompoundRefMangler, IndexRefMangler, QualnameRefMangler
from ..json_schema.ref_generator import BuiltinRefGenerator
from ..json_schema.request_cls import JSONSchemaContext
from ..json_schema.resolver import BuiltinJSONSchemaResolver, JSONSchemaResolver
from ..json_schema.schema_model import JSONSchemaDialect, _JSONSchemaCore
from ..provider_template import ABCProxy
from .provider import name_mapping
from .retort import AdornedRetort, Retort

_default_retort = Retort()
T = TypeVar("T")


@overload
def load(data: Any, tp: type[T], /) -> T:
    ...


@overload
def load(data: Any, tp: TypeHint, /) -> Any:
    ...


def load(data: Any, tp: TypeHint, /):
    return _default_retort.load(data, tp)


@overload
def dump(data: T, tp: type[T], /) -> Any:
    ...


@overload
def dump(data: Any, tp: Optional[TypeHint] = None, /) -> Any:
    ...


def dump(data: Any, tp: Optional[TypeHint] = None, /) -> Any:
    return _default_retort.dump(data, tp)


_global_resolver = BuiltinJSONSchemaResolver(
    ref_generator=BuiltinRefGenerator(),
    ref_mangler=CompoundRefMangler(QualnameRefMangler(), IndexRefMangler()),
)
_json_schema_retort = Retort(
    recipe=[
        ABCProxy(Sequence, list),
        name_mapping(
            omit_default=True,
            name_style=NameStyle.CAMEL,
            map={
                fld.name: f"${fld.name}"
                for fld in fields(_JSONSchemaCore)
            },
        ),
    ],
)

DumpedJSONSchema = Mapping[str, Any]


def generate_json_schemas(
    retort: AdornedRetort,
    tps: Iterable[TypeHint],
    *,
    direction: Direction,
    resolver: JSONSchemaResolver = _global_resolver,
    dialect: str = JSONSchemaDialect.DRAFT_2020_12,
    local_ref_prefix: str = "#/$defs/",
) -> tuple[DumpedJSONSchema, Iterable[DumpedJSONSchema]]:
    ctx = JSONSchemaContext(dialect=dialect, direction=direction)
    defs, schemas = resolver.resolve(
        (),
        [retort.make_json_schema(tp, ctx) for tp in tps],
        local_ref_prefix=local_ref_prefix,
    )
    dumped_defs = _json_schema_retort.dump(defs, dict[str, ResolvedJSONSchema])
    dumped_schemas = _json_schema_retort.dump(schemas, Iterable[ResolvedJSONSchema])
    return dumped_defs, dumped_schemas


def generate_json_schema(
    retort: AdornedRetort,
    tp: TypeHint,
    *,
    direction: Direction,
    resolver: JSONSchemaResolver = _global_resolver,
    dialect: str = JSONSchemaDialect.DRAFT_2020_12,
    local_ref_prefix: str = "#/$defs/",
) -> DumpedJSONSchema:
    defs, [schema] = generate_json_schemas(
        retort,
        [tp],
        direction=direction,
        resolver=resolver,
        dialect=dialect,
        local_ref_prefix=local_ref_prefix,
    )
    return {**schema, "$defs": defs}
