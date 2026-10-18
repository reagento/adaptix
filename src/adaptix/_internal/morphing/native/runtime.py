from collections.abc import Iterable, Mapping
from decimal import InvalidOperation

from adaptix._internal.compat import CompatExceptionGroup
from adaptix._internal.definitions import DebugTrail
from adaptix._internal.morphing.load_error import (
    AggregateLoadError,
    ExcludedTypeLoadError,
    LoadError,
    TypeLoadError,
    UnionLoadError,
    ValueLoadError,
)
from adaptix._internal.morphing.model.native_runtime import MISSING
from adaptix._internal.struct_trail import ItemKey, append_trail, render_trail_as_note


class ErrorState:
    def __init__(self):
        self.errors = []
        self.has_unexpected_error = False


def handle_error(debug_trail, loading, state, index, error):
    if not isinstance(error, Exception):
        raise error
    append_trail(error, index)
    if debug_trail == DebugTrail.FIRST:
        raise error
    state.errors.append(error)
    if loading and not isinstance(error, LoadError):
        state.has_unexpected_error = True
    return MISSING


def check_list_input(data):
    # Even exact lists can be registered as virtual Mapping subclasses.
    from adaptix._internal.morphing.iterable_provider import CollectionsMapping  # noqa: PLC0415

    if isinstance(data, CollectionsMapping):
        raise ExcludedTypeLoadError(Iterable, Mapping, data)


def check_tuple_input(data):
    from adaptix._internal.morphing.constant_length_tuple_provider import CollectionsMapping  # noqa: PLC0415

    if isinstance(data, CollectionsMapping):
        raise ExcludedTypeLoadError(tuple, Mapping, data)


def dictionary_error(debug_trail, loading, is_key, state, key, error):
    return handle_error(debug_trail, loading, state, ItemKey(key) if is_key else key, error)


def optional_error(tp, data, error):
    try:
        raise error
    except LoadError as cause:
        raise UnionLoadError(f"while loading {tp}", [TypeLoadError(None, data), cause])


def decimal_error(data, error):
    if isinstance(error, InvalidOperation):
        raise ValueLoadError("Bad string format", data)
    raise error


def retry_scalar(function, data, error):
    return function(data)


def finish_errors(message, loading, state, *, errors_factory=list):
    if state.errors:
        group = AggregateLoadError if loading and not state.has_unexpected_error else CompatExceptionGroup
        raise group(message, errors_factory(render_trail_as_note(error) for error in state.errors))


def finish_iterable(origin, loading, state):
    direction = "loading" if loading else "dumping"
    finish_errors(f"while {direction} iterable {origin}", loading, state,
                  errors_factory=tuple if loading and not state.has_unexpected_error else list)


def finish_tuple(loading, state):
    finish_errors(f"while {'loading' if loading else 'dumping'} tuple", loading, state)


def finish_dictionary(loading, state):
    finish_errors(f"while {'loading' if loading else 'dumping'} {dict}", loading, state)
