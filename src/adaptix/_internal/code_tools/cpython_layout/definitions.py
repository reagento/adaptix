from dataclasses import dataclass


@dataclass(frozen=True)
class CPythonLayout:
    version: tuple[int, int]
    object_refcount: int
    object_type: int
    object_size: int
    var_size: int
    list_items: int
    list_allocated: int
    tuple_items: int
    set_used: int
    type_basic_size: int | None = None
    type_getattro: int | None = None
    type_flags: int | None = None
    type_version: int | None = None
    type_cached_keys: int | None = None
    dict_used: int | None = None
    dict_keys: int | None = None
    dict_values: int | None = None
    keys_refcount: int | None = None
    keys_index_bytes: int | None = None
    keys_kind: int | None = None
    keys_nentries: int | None = None
    keys_indices: int | None = None
    unicode_entry_size: int | None = None
    unicode_entry_key: int | None = None
    unicode_entry_value: int | None = None
    general_entry_size: int | None = None
    general_entry_key: int | None = None
    general_entry_value: int | None = None
    values_capacity: int | None = None
    values_size: int | None = None
    values_valid: int | None = None
    values_items: int | None = None
    unicode_length: int | None = None
    unicode_hash: int | None = None
    unicode_state: int | None = None
    unicode_ascii_data: int | None = None
    bytes_data: int | None = None
    long_tag: int | None = None
    long_digits: int | None = None
    set_mask: int | None = None
    set_table: int | None = None
    set_entry_size: int | None = None
    member_descriptor_member: int | None = None
    member_type: int | None = None
    member_offset: int | None = None
    member_flags: int | None = None
    function_code: int | None = None
    function_defaults: int | None = None
    function_kwdefaults: int | None = None
    cell_contents: int | None = None
    cell_size: int | None = None
    thread_interpreter: int | None = None
    thread_eval_breaker: int | None = None
    thread_profile: int | None = None
    thread_trace: int | None = None
    interpreter_eval_frame: int | None = None
    datetime_hash: int | None = None
    datetime_has_tzinfo: int | None = None
    datetime_data: int | None = None
    datetime_tzinfo: int | None = None
    datetime_naive_size: int | None = None
    datetime_size: int | None = None
    date_size: int | None = None
    time_data: int | None = None
    time_tzinfo: int | None = None
    time_naive_size: int | None = None
    time_size: int | None = None
    timedelta_days: int | None = None
    timedelta_seconds: int | None = None
    timedelta_microseconds: int | None = None
    timedelta_size: int | None = None
    dictiter_dict: int | None = None
    dictiter_used: int | None = None
    dictiter_position: int | None = None
    dictiter_remaining: int | None = None
    abc_negative_cache: int | None = None
    abc_invalidation_counter: int | None = None
    timezone_offset: int | None = None
    timezone_size: int | None = None

    def offset(self, name: str) -> int:
        value = getattr(self, name, None)
        if value is None:
            raise RuntimeError(f"No offset {name!r} in CPython {self.version} layout")
        if not isinstance(value, int):
            raise TypeError(f"CPython layout field {name!r} is not an offset")
        return value
