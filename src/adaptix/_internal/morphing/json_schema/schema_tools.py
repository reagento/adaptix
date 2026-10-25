from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import fields
from textwrap import dedent, indent
from typing import Any, TypeVar

from adaptix import TypeHint

from ...utils import Omittable, Omitted
from .definitions import JSONSchema, LocalRefSource, RemoteRef, ResolvedJSONSchema
from .schema_model import JSONNumeric, JSONObject, JSONSchemaBuiltinFormat, JSONSchemaT, JSONSchemaType, JSONValue, RefT

_non_generic_fields_types = [
    Omittable[JSONSchemaType | Sequence[JSONSchemaType]],  # type: ignore[misc]
    Omittable[JSONSchemaBuiltinFormat | str],  # type: ignore[misc]
    Omittable[JSONNumeric],  # type: ignore[misc]
    Omittable[int],  # type: ignore[misc]
    Omittable[str],  # type: ignore[misc]
    Omittable[bool],  # type: ignore[misc]
    Omittable[Sequence[str]],  # type: ignore[misc]
    Omittable[JSONObject[Sequence[str]]],  # type: ignore[misc]
    Omittable[JSONValue],  # type: ignore[misc]
    Omittable[Sequence[JSONValue]],  # type: ignore[misc]
    Omittable[JSONObject[bool]],  # type: ignore[misc]
    JSONObject[JSONValue],
]

_base_json_schema_templates = {
    **{tp: None for tp in _non_generic_fields_types},
    Omittable[Sequence[JSONSchemaT]]: dedent(  # type: ignore[misc, valid-type]
        """
        if __value__ != Omitted():
            for item in __value__:
                yield from __traverser__(item)
        """,
    ),
    Omittable[JSONSchemaT]: dedent(  # type: ignore[misc, valid-type]
        """
        if __value__ != Omitted():
            yield from __traverser__(__value__)
        """,
    ),
    Omittable[JSONObject[JSONSchemaT]]: dedent(  # type: ignore[misc, valid-type]
        """
        if __value__ != Omitted():
            for item in __value__.values():
                yield from __traverser__(item)
        """,
    ),
    Omittable[RefT]: None,  # type: ignore[misc, valid-type]
}
_json_schema_templates = {
    **_base_json_schema_templates,
    Omittable[RefT]: dedent(  # type: ignore[misc, valid-type]
        """
        if __value__ != Omitted() and isinstance(__value__, LocalRefSource):
            yield from __traverser__(__value__.json_schema)
        """,
    ),
}


def _generate_json_schema_traverser(
    function_name: str,
    file_name: str,
    templates: Mapping[TypeHint, str | None],
    cls: type[JSONSchemaT],
) -> Callable[[JSONSchemaT], Iterable[JSONSchemaT]]:
    result = []
    for fld in fields(cls):  # type: ignore[arg-type]
        template = templates[fld.type]
        if template is None:
            continue

        result.append(
            template
            .replace("__value__", f"obj.{fld.name}")
            .replace("__traverser__", function_name)
            .strip("\n"),
        )

    module_code = dedent(
        f"""
        def {function_name}(obj, /):
            if isinstance(obj, bool):
                return

            yield obj

        """,
    ) + "\n\n".join(indent(item, " " * 4) for item in result)
    namespace: dict[str, Any] = {"Omitted": Omitted, "LocalRefSource": LocalRefSource}
    exec(compile(module_code, file_name, "exec"), namespace, namespace)  # noqa: S102
    return namespace[function_name]


traverse_json_schema = _generate_json_schema_traverser(
    function_name="traverse_json_schema",
    file_name="<traverse_json_schema generation>",
    templates=_json_schema_templates,
    cls=JSONSchema,
)
traverse_resolved_json_schema = _generate_json_schema_traverser(
    function_name="traverse_resolved_json_schema",
    file_name="<traverse_resolved_json_schema generation>",
    templates=_base_json_schema_templates,
    cls=ResolvedJSONSchema,
)


_to_resolved_json_schema_templates = {
    **{tp: "__value__" for tp in _non_generic_fields_types},
    Omittable[Sequence[JSONSchemaT]]: (  # type: ignore[misc, valid-type]
        "Omitted() if __value__ == Omitted() else [__replacer__(item, __prefix__, __ctx__) for item in __value__]"
    ),
    Omittable[JSONSchemaT]: (  # type: ignore[misc, valid-type]
        "Omitted() if __value__ == Omitted() else __replacer__(__value__, __prefix__, __ctx__)"
    ),
    Omittable[JSONObject[JSONSchemaT]]: (  # type: ignore[misc, valid-type]
        "Omitted() if __value__ == Omitted() else"
        " {key: __replacer__(value, __prefix__, __ctx__) for key, value in __value__.items()}"
    ),
    Omittable[RefT]: (  # type: ignore[misc, valid-type]
        "Omitted() if __value__ == Omitted() else"
        " (__value__.value if isinstance(__value__, RemoteRef) else __prefix__ + __ctx__[__value__])"
    ),
}


JSONSchemaSourceT = TypeVar("JSONSchemaSourceT")
JSONSchemaTargetT = TypeVar("JSONSchemaTargetT")
ContextT = TypeVar("ContextT")


def _generate_json_schema_replacer(
    function_name: str,
    file_name: str,
    templates: Mapping[TypeHint, str | None],
    source_cls: type[JSONSchemaSourceT],
    target_cls: type[JSONSchemaTargetT],
    context: type[ContextT],
) -> Callable[[JSONSchemaSourceT, str, ContextT], JSONSchemaTargetT]:
    result = []
    for fld in fields(target_cls):  # type: ignore[arg-type]
        template = templates[fld.type]
        if template is None:
            continue

        result.append(
            template
            .replace("__value__", f"obj.{fld.name}")
            .replace("__replacer__", function_name)
            .replace("__ctx__", "ctx")
            .replace("__prefix__", "prefix")
            + ",",
        )

    body = "\n".join(indent(item, " " * 8) for item in result)
    module_code = dedent(
        f"""
        def {function_name}(obj, prefix, ctx, /):
            if isinstance(obj, bool):
                return obj

            return {target_cls.__name__}(
            {body}
            )
        """,
    )
    namespace: dict[str, Any] = {target_cls.__name__: target_cls, "Omitted": Omitted, "RemoteRef": RemoteRef}
    exec(compile(module_code, file_name, "exec"), namespace, namespace)  # noqa: S102
    return namespace[function_name]


replace_json_schema_ref = _generate_json_schema_replacer(
    function_name="replace_json_schema_ref",
    file_name="<replace_json_schema_ref generation>",
    templates=_to_resolved_json_schema_templates,
    source_cls=JSONSchema,
    target_cls=ResolvedJSONSchema,
    context=Mapping[LocalRefSource[JSONSchema], str],  # type: ignore[type-abstract]
)


class HashGetter:
    __slots__ = ("_hash_value", )

    def __init__(self, hash_value: int):
        self._hash_value = hash_value

    def __hash__(self):
        return self._hash_value


def _hash_json_value(value: JSONValue) -> int:
    if isinstance(value, Sequence) and type(value) is not str:
        return hash(tuple(map(lambda x: HashGetter(_hash_json_value(x)), value)))  # noqa: C417
    if isinstance(value, Mapping):
        return hash(frozenset(map(lambda x: (x[0], HashGetter(_hash_json_value(x[1]))), value.items())))  # noqa: C417
    return hash(value)


def _check_omitted(template: str) -> str:
    return f"OMITTED_HASH if __value__ is OMITTED else ({template})"


def _json_object_hasher(item_hasher_template: str) -> str:
    item_hasher = item_hasher_template.replace("__value__", "x[1]")
    return f"hash(frozenset(map(lambda x: (x[0], HashGetter({item_hasher})), __value__.items())))"


def _sequence_hasher(item_hasher_template: str) -> str:
    item_hasher = item_hasher_template.replace("__value__", "y")
    return f"hash(tuple(map(lambda y: HashGetter({item_hasher}), __value__)))"


_approx_hash_templates = {
    Omittable[JSONSchemaType | Sequence[JSONSchemaType]]: (  # type: ignore[misc]
        f"{_sequence_hasher('hash(__value__)')} if isinstance(__value__, Sequence) else hash(__value__)"
    ),
    Omittable[JSONSchemaBuiltinFormat | str]: "hash(__value__)",  # type: ignore[misc]
    Omittable[JSONNumeric]: "hash(__value__)",  # type: ignore[misc]
    Omittable[int]: "hash(__value__)",  # type: ignore[misc]
    Omittable[str]: "hash(__value__)",  # type: ignore[misc]
    Omittable[bool]: "hash(__value__)",  # type: ignore[misc]
    Omittable[Sequence[str]]: (  # type: ignore[misc]
        _check_omitted("hash(tuple(__value__))")
    ),
    Omittable[JSONObject[Sequence[str]]]: (  # type: ignore[misc]
        _check_omitted(_json_object_hasher("hash(tuple(__value__))"))
    ),
    Omittable[JSONValue]: (  # type: ignore[misc]
        _check_omitted("_hash_json_value(__value__)")
    ),
    Omittable[Sequence[JSONValue]]: (  # type: ignore[misc]
        _check_omitted(_sequence_hasher("_hash_json_value(__value__)"))
    ),
    Omittable[JSONObject[bool]]: (  # type: ignore[misc]
        _check_omitted("hash(frozenset(__value__.items()))")
    ),
    JSONObject[JSONValue]: (
        _json_object_hasher("_hash_json_value(__value__)")
    ),
    Omittable[Sequence[JSONSchemaT]]: (  # type: ignore[misc, valid-type]
        _check_omitted(_sequence_hasher("__schema_hasher__(__value__)"))
    ),
    Omittable[JSONSchemaT]: (  # type: ignore[misc, valid-type]
        _check_omitted("__schema_hasher__(__value__)")
    ),
    Omittable[JSONObject[JSONSchemaT]]: (  # type: ignore[misc, valid-type]
        _check_omitted(_json_object_hasher("__schema_hasher__(__value__)"))
    ),
    Omittable[RefT]: "hash(__value__)",  # type: ignore[misc, valid-type]
}


def _generate_json_schema_hasher(
    function_name: str,
    file_name: str,
    templates: Mapping[TypeHint, str | None],
    source_cls: type[JSONSchemaSourceT],
) -> Callable[[JSONSchemaSourceT], int]:
    result = []
    for fld in fields(source_cls):  # type: ignore[arg-type]
        template = templates[fld.type]
        if template is None:
            continue

        hasher = (
            template
            .replace("__value__", f"obj.{fld.name}")
            .replace("__schema_hasher__", function_name)
        )
        result.append(f"HashGetter({hasher}),")

    body = "\n".join(indent(item, " " * 12) for item in result)
    module_code = dedent(
        f"""
        def {function_name}(obj, /):
            if isinstance(obj, bool):
                return hash(obj)

            return hash(
                (
                {body}
                )
            )
        """,
    )
    namespace: dict[str, Any] = {
        "OMITTED": Omitted(),
        "OMITTED_HASH": hash(Omitted()),
        "_hash_json_value": _hash_json_value,
        "HashGetter": HashGetter,
        "Sequence": Sequence,
    }
    exec(compile(module_code, file_name, "exec"), namespace, namespace)  # noqa: S102
    return namespace[function_name]


approx_hash_json_schema = _generate_json_schema_hasher(
    function_name="approx_hash_json_schema",
    file_name="<approx_hash_json_schema generation>",
    templates=_approx_hash_templates,
    source_cls=JSONSchema,
)
