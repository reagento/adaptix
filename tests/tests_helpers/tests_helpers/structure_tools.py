from dataclasses import dataclass
from typing import Any, Mapping, Union


@dataclass(slots=True)
class Exists:
    """Marker to check that a key exists in the dict (value type not checked)."""


@dataclass(slots=True)
class NotExists:
    """Marker to check that a key does NOT exist in the dict."""


EXISTS = Exists()
NOT_EXISTS = NotExists()


def _assert_list_structure(
    actual: list,
    expected: list,
    *,
    path: str,
    strict: bool,
) -> None:
    assert isinstance(actual, list), (
        f"At {path!r}: expected list, got {type(actual).__name__}"
    )
    if strict:
        assert len(actual) == len(expected), (
            f"At {path!r}: expected list of length {len(expected)}, got {len(actual)}"
        )
    else:
        assert len(actual) >= len(expected), (
            f"At {path!r}: expected at least {len(expected)} elements, got {len(actual)}"
        )
    for i, expected_item in enumerate(expected):
        current_path = f"{path}[{i}]"
        actual_item = actual[i]
        if isinstance(expected_item, (dict, list)):
            assert_structure(actual_item, expected_item, path=current_path, strict=strict)
        else:
            assert actual_item == expected_item, (
                f"At {current_path}: expected {expected_item!r}, got {actual_item!r}"
            )


def assert_structure(
    actual: Union[Mapping[str, Any], list],
    expected: Union[Mapping[str, Any], list],
    *,
    path: str = "",
    strict: bool = False,
) -> None:
    """
    Assert that a dict or list matches the expected structure.

    Supports nested dicts and lists.
    For dict values, supports:
    - EXISTS: check that key exists (any value)
    - NOT_EXISTS: check that key does NOT exist
    - Other values: direct equality check or recursive structure check

    Args:
        actual: The actual dict or list to check
        expected: Dict or list describing expected structure
        path: Current path for error messages (used internally for recursion)
        strict: If True, fail if actual has keys/elements not in expected

    Example:
        assert_structure(schema, {
            "$ref": "#/$defs/SimpleModel",
            "$defs": {
                "SimpleModel": {},
            },
        })
        assert_structure([{"a": 1}, {"b": 2}], [{"a": 1}, {"b": EXISTS}])
    """
    if isinstance(expected, list):
        _assert_list_structure(actual, expected, path=path, strict=strict)
        return

    # Check for extra keys in strict mode
    if strict:
        expected_keys = set(expected.keys())
        actual_keys = set(actual.keys())
        extra_keys = actual_keys - expected_keys
        if extra_keys:
            raise AssertionError(
                f"At {path!r}: unexpected keys: {sorted(extra_keys)}",
            )

    for key, expected_value in expected.items():
        current_path = f"{path}.{key}" if path else key

        if expected_value is NOT_EXISTS:
            assert key not in actual, (
                f"Key {current_path!r} should not exist, but found: {actual[key]!r}"
            )
            continue

        assert key in actual, f"Key {current_path!r} not found in dict"

        if expected_value is EXISTS:
            continue

        actual_value = actual[key]

        if isinstance(expected_value, (dict, list)):
            assert_structure(actual_value, expected_value, path=current_path, strict=strict)
        else:
            assert actual_value == expected_value, (
                f"At {current_path!r}: expected {expected_value!r}, got {actual_value!r}"
            )
