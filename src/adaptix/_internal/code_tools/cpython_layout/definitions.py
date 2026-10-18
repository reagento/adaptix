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
    type_basic_size: int
    type_getattro: int
    type_flags: int
    type_version: int
    type_cached_keys: int
    dict_used: int
    dict_keys: int
    dict_values: int
    unicode_length: int
    unicode_hash: int
    unicode_state: int
    unicode_ascii_data: int
    bytes_data: int
    set_mask: int
    set_table: int
    set_entry_size: int
    member_descriptor_member: int
    member_type: int
    member_offset: int
    member_flags: int
    function_code: int
    function_defaults: int
    function_kwdefaults: int
    cell_contents: int
    cell_size: int
    thread_interpreter: int
    thread_profile: int
    thread_trace: int
    interpreter_eval_frame: int
    datetime_hash: int
    datetime_has_tzinfo: int
    datetime_data: int
    datetime_tzinfo: int
    datetime_naive_size: int
    datetime_size: int
    date_size: int
    time_data: int
    time_tzinfo: int
    time_naive_size: int
    time_size: int
    timedelta_days: int
    timedelta_seconds: int
    timedelta_microseconds: int
    timedelta_size: int
    dictiter_dict: int
    dictiter_used: int
    dictiter_position: int
    dictiter_remaining: int
    abc_negative_cache: int
    abc_invalidation_counter: int
    timezone_offset: int
    timezone_size: int
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
    long_tag: int | None = None
    long_digits: int | None = None
    thread_eval_breaker: int | None = None

    def offset(self, name: str) -> int:
        value = getattr(self, name, None)
        if value is None:
            raise RuntimeError(f"No offset {name!r} in CPython {self.version} layout")
        if not isinstance(value, int):
            raise TypeError(f"CPython layout field {name!r} is not an offset")
        return value
