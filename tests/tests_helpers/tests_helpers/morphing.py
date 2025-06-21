from dataclasses import dataclass
from typing import Any

from adaptix import Direction, Omitted, Retort, TypeHint
from adaptix._internal.morphing.facade.func import DumpedJSONSchema, generate_json_schema

try:
    import jsonschema
except ImportError:
    jsonschema = None


try:
    import jsonschema_rs
except ImportError:
    jsonschema_rs = None


def _validate_json_schema(json_schema: DumpedJSONSchema) -> DumpedJSONSchema:
    if jsonschema is not None:
        jsonschema.Draft202012Validator.check_schema(json_schema)
    if jsonschema_rs is not None:
        jsonschema_rs.meta.validate(json_schema)
    return json_schema


def _validate_by_json_schema(data, json_schema: DumpedJSONSchema) -> None:
    if jsonschema is not None:
        jsonschema.Draft202012Validator(json_schema).validate(data)
    if jsonschema_rs is not None:
        jsonschema_rs.validate(json_schema, data)


@dataclass
class JSONSchemaFork:
    input: Any
    output: Any


def _resolve_fork(data, direction: Direction):
    if isinstance(data, JSONSchemaFork):
        if direction == Direction.INPUT:
            return data.input
        if direction == Direction.OUTPUT:
            return data.output
        raise ValueError
    if isinstance(data, dict):
        return {
            _resolve_fork(k, direction): _resolve_fork(v, direction)
            for k, v in data.items()
        }
    if isinstance(data, list):
        return [
            _resolve_fork(element, direction)
            for element in data
        ]
    return data


def assert_morphing(
    *,
    retort: Retort,
    tp: TypeHint,
    data: Any,
    loaded: Any,
    dumped: Any = Omitted(),
    json_schema: DumpedJSONSchema,
) -> None:
    produced_loaded = retort.load(data, tp)
    assert produced_loaded == loaded
    produced_dumped = retort.dump(produced_loaded, tp)
    expected_dumped = data if dumped == Omitted() else dumped
    assert produced_dumped == expected_dumped

    input_json_schema = generate_json_schema(retort, tp, direction=Direction.INPUT)
    output_json_schema = generate_json_schema(retort, tp, direction=Direction.OUTPUT)
    _validate_json_schema(input_json_schema)
    _validate_json_schema(output_json_schema)

    expected_input_json_schema = _resolve_fork(json_schema, Direction.INPUT)
    expected_output_json_schema = _resolve_fork(json_schema, Direction.OUTPUT)
    assert input_json_schema == expected_input_json_schema
    assert output_json_schema == expected_output_json_schema

    _validate_by_json_schema(data, input_json_schema)
    _validate_by_json_schema(produced_dumped, output_json_schema)
