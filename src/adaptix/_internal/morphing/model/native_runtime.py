from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any, cast

from adaptix._internal.compat import CompatExceptionGroup
from adaptix._internal.definitions import DebugTrail
from adaptix._internal.model_tools.definitions import (
    DefaultFactory,
    DefaultFactoryWithSelf,
    DefaultValue,
    InputField,
    OutputField,
)
from adaptix._internal.morphing.load_error import (
    AggregateLoadError,
    ExcludedTypeLoadError,
    ExtraFieldsLoadError,
    ExtraItemsLoadError,
    NoRequiredFieldsLoadError,
    NoRequiredItemsLoadError,
    TypeLoadError,
)
from adaptix._internal.morphing.model.crown_definitions import (
    CrownPath,
    ExtraCollect,
    ExtraForbid,
    InpDictCrown,
    InpListCrown,
    Sieve,
)
from adaptix._internal.special_cases_optimization import get_default_clause
from adaptix._internal.struct_trail import extend_trail, render_trail_as_note

MISSING = object()
READ_ERROR = object()


class LoadState:
    def __init__(self, debug_trail: DebugTrail, model_identity: str):
        self.debug_trail = debug_trail
        self.model_identity = model_identity
        self.values: dict[str, Any] = {}
        self.errors: list[Exception] = []
        self.has_unexpected_error = False
        self.missing_reported = False
        self.extra: Any = {}

    def error(self, error: Exception, path: CrownPath, *, unexpected: bool = False) -> None:
        if self.debug_trail == DebugTrail.DISABLE:
            raise error
        if path:
            extend_trail(error, path)
        if self.debug_trail == DebugTrail.FIRST:
            raise error
        self.errors.append(error)
        self.has_unexpected_error |= unexpected


@dataclass(frozen=True)
class LoadNodeSpec:
    crown: InpDictCrown | InpListCrown
    path: CrownPath
    required_keys: frozenset[str]
    strict_coercion: bool
    collect_extra: bool


class LoadNode:
    def __init__(self, spec: LoadNodeSpec, data: Any):
        self.spec = spec
        self.data = data
        self.checked = False
        self.aborted = False
        self.missing_reported = False
        self.extra: Any = (
            {} if isinstance(spec.crown, InpDictCrown) else
            [{} for _ in spec.crown.map]
        )


def enter_load_node(spec: LoadNodeSpec, state: LoadState, data: Any) -> LoadNode:
    node = LoadNode(spec, data)
    if isinstance(spec.crown, InpListCrown) and spec.strict_coercion and type(data) is str:
        node.aborted = True
        state.error(ExcludedTypeLoadError(Sequence, str, data), spec.path)
    if not spec.path:
        state.extra = node.extra
    return node


def bad_load_type(state: LoadState, node: LoadNode) -> None:
    expected = Mapping if isinstance(node.spec.crown, InpDictCrown) else Sequence
    node.aborted = True
    state.error(TypeLoadError(expected, node.data), node.spec.path)


def missing_load_value(state: LoadState, node: LoadNode) -> None:
    if isinstance(node.spec.crown, InpDictCrown):
        if not node.missing_reported:
            node.missing_reported = True
            state.error(
                NoRequiredFieldsLoadError(node.spec.required_keys - set(node.data), node.data),
                node.spec.path,
            )
    elif state.debug_trail != DebugTrail.ALL:
        state.error(NoRequiredItemsLoadError(len(node.spec.crown.map), node.data), node.spec.path)


def read_optional_mapping(key: str, state: LoadState, node: LoadNode):
    checked = node.checked
    node.checked = True
    if not checked:
        try:
            getter = node.data.get
        except AttributeError:
            bad_load_type(state, node)
            return READ_ERROR
        except Exception as error:
            state.error(error, (*node.spec.path, key), unexpected=True)
            return READ_ERROR
    try:
        if checked:
            # Membership and get can have different semantics for user mappings.
            return node.data[key] if key in node.data else MISSING  # noqa: SIM401
        return getter(key, MISSING)
    except Exception as error:
        state.error(error, (*node.spec.path, key), unexpected=True)
        return READ_ERROR


def read_indexed(key: str | int, state: LoadState, node: LoadNode, *, optional: bool):
    checked = node.checked
    node.checked = True
    try:
        return node.data[key]
    except (KeyError, IndexError, TypeError) as error:
        if isinstance(error, KeyError if isinstance(key, str) else IndexError):
            if not optional:
                missing_load_value(state, node)
            return MISSING
        if not checked:
            bad_load_type(state, node)
        else:
            state.error(error, (*node.spec.path, key), unexpected=True)
    except Exception as error:
        state.error(error, (*node.spec.path, key), unexpected=True)
    return READ_ERROR


def read_load_value(
    key: str | int,
    field: InputField | None,
    state: LoadState,
    node: LoadNode,
    *,
    use_default: bool,
):
    if node.aborted:
        return MISSING
    optional = field is not None and field.is_optional
    value = (
        read_optional_mapping(key, state, node) if optional and isinstance(key, str) else
        read_indexed(key, state, node, optional=optional)
    )
    if value is READ_ERROR:
        return MISSING
    if value is MISSING and field is not None and optional and use_default:
        default = field.default
        if isinstance(default, DefaultValue):
            state.values[field.id] = default.value
        elif isinstance(default, DefaultFactory):
            state.values[field.id] = default.factory()
    return value


def leave_load_node(state: LoadState, node: LoadNode) -> None:
    if node.aborted:
        return
    spec = node.spec
    if not node.checked:
        expected = Mapping if isinstance(spec.crown, InpDictCrown) else Sequence
        if not isinstance(node.data, expected):
            bad_load_type(state, node)
            return
    if isinstance(spec.crown, InpDictCrown):
        check_dict_extra(state, node, spec.crown)
    else:
        size = len(node.data)
        expected_len = len(spec.crown.map)
        if size < expected_len:
            state.error(NoRequiredItemsLoadError(expected_len, node.data), spec.path)
        elif size > expected_len and spec.crown.extra_policy == ExtraForbid():
            state.error(ExtraItemsLoadError(expected_len, node.data), spec.path)


def check_dict_extra(state: LoadState, node: LoadNode, crown: InpDictCrown) -> None:
    if isinstance(crown.extra_policy, (ExtraForbid, ExtraCollect)):
        extra_keys = set(node.data) - crown.map.keys()
        if extra_keys and crown.extra_policy == ExtraForbid():
            state.error(ExtraFieldsLoadError(extra_keys, node.data), node.spec.path)
        elif crown.extra_policy == ExtraCollect():
            for key in extra_keys:
                node.extra[key] = node.data[key]


def attach_load_extra(key: str | int, parent: LoadNode, child: LoadNode) -> None:
    if child.spec.collect_extra:
        parent.extra[key] = child.extra


def handle_load_error(path: CrownPath, state: LoadState, error: BaseException):
    if not isinstance(error, Exception):
        raise error
    state.error(error, path)
    return MISSING


def handle_flat_load_access_error(
    required_keys: frozenset[str],
    key: str,
    state: LoadState | None,
    data: Any,
    error: BaseException,
    *,
    first: bool,
):
    if not isinstance(error, Exception):
        raise error
    if isinstance(error, KeyError):
        if state is not None and state.missing_reported:
            return MISSING
        if state is not None:
            state.missing_reported = True
        missing_error = NoRequiredFieldsLoadError(required_keys - set(data), data)
        if state is None:
            raise missing_error
        state.error(missing_error, ())
    elif first and isinstance(error, (TypeError, IndexError)):
        type_error = TypeLoadError(Mapping, data)
        if state is not None and state.debug_trail == DebugTrail.ALL:
            raise AggregateLoadError(f"while loading model {state.model_identity}", (type_error,))
        raise type_error
    elif state is None:
        raise error
    else:
        state.error(error, (key,), unexpected=True)
    return MISSING


def get_load_extra(field: InputField, state: LoadState, *, use_extra: bool):
    if use_extra:
        return state.extra
    if field.is_required:
        return {}
    if isinstance(field.default, DefaultValue):
        state.values[field.id] = field.default.value
    elif isinstance(field.default, DefaultFactory):
        state.values[field.id] = field.default.factory()
    return MISSING


def finish_load(state: LoadState) -> None:
    if state.errors:
        group: type[CompatExceptionGroup] = CompatExceptionGroup if state.has_unexpected_error else AggregateLoadError
        raise group(
            f"while loading model {state.model_identity}",
            [render_trail_as_note(error) for error in state.errors],
        )


class DumpState:
    def __init__(self, debug_trail: DebugTrail, model_identity: str, data: Any):
        self.debug_trail = debug_trail
        self.model_identity = model_identity
        self.data = data
        self.errors: list[Exception] = []

    def error(self, error: Exception, field: OutputField | None) -> None:
        if self.debug_trail == DebugTrail.DISABLE:
            raise error
        if field is not None:
            extend_trail(error, (field.accessor.trail_element,))
        if self.debug_trail == DebugTrail.FIRST:
            raise error
        self.errors.append(error)


def handle_dump_access_error(field: OutputField, state: DumpState | None, error: BaseException):
    if not isinstance(error, Exception):
        raise error
    access_error = field.accessor.access_error
    if access_error is not None and isinstance(error, access_error):
        return MISSING
    if state is None:
        raise error
    state.error(error, field)
    return MISSING


def handle_dump_error(field: OutputField | None, state: DumpState, error: BaseException):
    if not isinstance(error, Exception):
        raise error
    state.error(error, field)
    return MISSING


def filter_dump_value(sieve: Sieve, data: Any, value: Any):
    default = get_default_clause(sieve)
    if default is None:
        keep = cast(Callable[[Any], bool], sieve)(value)
    elif isinstance(default, DefaultValue):
        keep = (
            value is not default.value if default.value is None or type(default.value) is bool else
            value != default.value
        )
    elif isinstance(default, DefaultFactory):
        keep = value != default.factory()
    elif isinstance(default, DefaultFactoryWithSelf):
        keep = value != default.factory(data)
    else:
        raise TypeError(f"Unknown sieve default: {default}")
    return value if keep else MISSING


def dump_has_errors(state: DumpState | None) -> bool:
    return state is not None and bool(state.errors)


def filter_dump_structure(sieve: Sieve, state: DumpState | None, value: Any, data: Any):
    return MISSING if state is not None and state.errors else filter_dump_value(sieve, data, value)


def update_dump_extra(state: DumpState | None, result: dict, extra: Any) -> None:
    # After a field fails in ALL mode, subsequent field conversions are used to
    # collect errors. Their results must not be consumed as valid extra data.
    if state is None or not state.errors:
        result.update(extra)


def finish_dump(state: DumpState) -> None:
    if state.errors:
        raise CompatExceptionGroup(
            f"while dumping model {state.model_identity}",
            [render_trail_as_note(error) for error in state.errors],
        )
