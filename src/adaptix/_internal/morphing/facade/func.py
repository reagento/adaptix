from collections.abc import Container, Iterable, Mapping, Sequence
from contextlib import suppress
from dataclasses import fields
from typing import Any, TypeVar, overload

from ...common import TypeHint
from ...definitions import Direction
from ...morphing.model.crown_definitions import ExtraForbid
from ...name_style import NameStyle
from ...provider.loc_stack_filtering import P
from ..json_schema.definitions import JSONSchema, RemoteRef, ResolvedJSONSchema
from ..json_schema.mangling import CompoundRefMangler, IndexRefMangler, QualnameRefMangler
from ..json_schema.ref_generator import BuiltinRefGenerator
from ..json_schema.request_cls import JSONSchemaContext
from ..json_schema.resolver import BuiltinJSONSchemaResolver, JSONSchemaResolver
from ..json_schema.schema_model import JSONObject, JSONSchemaBuiltinFormat, _JSONSchemaCore
from ..load_error import TypeLoadError
from ..provider_template import ABCProxy
from .provider import loader, name_mapping
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
def dump(data: Any, tp: TypeHint | None = None, /) -> Any:
    ...


def dump(data: Any, tp: TypeHint | None = None, /) -> Any:
    return _default_retort.dump(data, tp)


def _ref_loader(data):
    if isinstance(data, str):
        return RemoteRef(value=data)
    raise TypeLoadError(expected_type=str, input_value=data)


def _format_loader(data):
    if isinstance(data, str):
        with suppress(ValueError):
            return JSONSchemaBuiltinFormat(data)
        return data
    raise TypeLoadError(expected_type=str, input_value=data)


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
            extra_in=ExtraForbid(),
            extra_out="extra_keywords",
        ),
        loader(P[JSONSchema].ref, _ref_loader),
        loader(P[JSONSchema].format, _format_loader),
    ],
)

DumpedJSONSchema = Mapping[str, Any]

DIALECT_2020_12 = "https://json-schema.org/draft/2020-12/schema"


def generate_json_schemas_namespace(
    query: Iterable[tuple[AdornedRetort, Direction, TypeHint]],
    *,
    resolver: JSONSchemaResolver = _global_resolver,
    local_ref_prefix: str = "#/$defs/",
    with_dialect_uri: bool = True,
    occupied_refs: Container[str] = (),
) -> tuple[DumpedJSONSchema, Sequence[DumpedJSONSchema]]:
    defs, schemas = resolver.resolve(
        [
            retort.make_json_schema(tp, JSONSchemaContext(direction=direction))
            for retort, direction, tp in query
        ],
        local_ref_prefix=local_ref_prefix,
        occupied_refs=occupied_refs,
    )

    dumped_defs = _json_schema_retort.dump(defs, dict[str, ResolvedJSONSchema])
    dumped_schemas = _json_schema_retort.dump(schemas, Sequence[ResolvedJSONSchema])

    if with_dialect_uri:
        for dumped_schema in dumped_schemas:
            dumped_schema["$schema"] = DIALECT_2020_12
    return dumped_defs, dumped_schemas


def generate_json_schema(
    retort: AdornedRetort,
    tp: TypeHint,
    direction: Direction,
    *,
    resolver: JSONSchemaResolver = _global_resolver,
    local_ref_prefix: str = "#/$defs/",
    with_dialect_uri: bool = True,
    occupied_refs: Container[str] = (),
) -> DumpedJSONSchema:
    defs, schemas = generate_json_schemas_namespace(
        [(retort, direction, tp)],
        resolver=resolver,
        local_ref_prefix=local_ref_prefix,
        with_dialect_uri=with_dialect_uri,
        occupied_refs=occupied_refs,
    )
    return {**schemas[0], "$defs": defs}


_lax_json_schema_retort = _json_schema_retort.extend(
    recipe=[name_mapping(extra_in="extra_keywords")],
)


def load_json_schema(data: JSONObject[Any], *, error_on_extra: bool = True) -> JSONSchema:
    """Creates a :class:`.JSONSchema` instance from a raw dictionary.
    Field names and their possible values follow the JSON Schema specification.

    The :class:`.JSONSchema` class fields comply with PEP8 and use enums.
    This function makes it possible to define schemas in their original notation.

    :param data: Dict after JSON parsing
    :param error_on_extra: When set to True, the function raises an error if unexpected fields are encountered.
        Otherwise, all unknown fields are stored in the ``extra_keywords`` field.
    :return: JSONSchema instance
    """
    if error_on_extra:
        return _json_schema_retort.load(data, JSONSchema)
    return _lax_json_schema_retort.load(data, JSONSchema)
