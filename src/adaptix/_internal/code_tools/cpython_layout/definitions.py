from dataclasses import dataclass


@dataclass(frozen=True)
class DictKeysLayout:
    refcount: int
    index_bytes: int
    kind: int
    nentries: int
    indices: int
    unicode_entry_size: int
    unicode_entry_key: int
    unicode_entry_value: int
    general_entry_size: int
    general_entry_key: int
    general_entry_value: int


@dataclass(frozen=True)
class InlineValuesLayout:
    items: int
    capacity: int
    size: int
    valid: int


@dataclass(frozen=True)
class LongLayout:
    tag: int
    digits: int


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
    dict_keys_layout: DictKeysLayout | None = None
    inline_values: InlineValuesLayout | None = None
    long_layout: LongLayout | None = None
    thread_eval_breaker: int | None = None

    def require_dict_keys(self) -> DictKeysLayout:
        if self.dict_keys_layout is None:
            raise RuntimeError(f"CPython {self.version} exposes no dictionary keys layout")
        return self.dict_keys_layout

    def require_inline_values(self) -> InlineValuesLayout:
        if self.inline_values is None:
            raise RuntimeError(f"CPython {self.version} exposes no inline values layout")
        return self.inline_values

    def require_long(self) -> LongLayout:
        if self.long_layout is None:
            raise RuntimeError(f"CPython {self.version} exposes no integer layout")
        return self.long_layout
