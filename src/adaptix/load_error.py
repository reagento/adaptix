from adaptix._internal.morphing.load_error import (
    AggregateLoadError,
    BadVariantLoadError,
    DuplicatedValuesLoadError,
    ExcludedTypeLoadError,
    ExtraFieldsLoadError,
    ExtraItemsLoadError,
    FormatMismatchLoadError,
    LoadError,
    LoadExceptionGroup,
    MsgLoadError,
    MultipleBadVariantLoadError,
    NoRequiredFieldsLoadError,
    NoRequiredItemsLoadError,
    OutOfRangeLoadError,
    TypeLoadError,
    UnionLoadError,
    ValidationLoadError,
    ValueLoadError,
)
from adaptix._internal.utils import create_deprecated_alias_getter

__all__ = (
    'LoadError',
    'LoadExceptionGroup',
    'AggregateLoadError',
    'UnionLoadError',
    'MsgLoadError',
    'ExtraFieldsLoadError',
    'ExtraItemsLoadError',
    'NoRequiredFieldsLoadError',
    'NoRequiredItemsLoadError',
    'TypeLoadError',
    'ExcludedTypeLoadError',
    'ValueLoadError',
    'ValidationLoadError',
    'BadVariantLoadError',
    'FormatMismatchLoadError',
    'DuplicatedValuesLoadError',
    'OutOfRangeLoadError',
    'MultipleBadVariantLoadError'
)


__getattr__ = create_deprecated_alias_getter(
    __name__,
    {
        'MsgError': 'MsgLoadError',
        'ExtraFieldsError': 'ExtraFieldsLoadError',
        'ExtraItemsError': 'ExtraItemsLoadError',
        'NoRequiredFieldsError': 'NoRequiredFieldsLoadError',
        'NoRequiredItemsError': 'NoRequiredItemsLoadError',
        'ValidationError': 'ValidationLoadError',
        'BadVariantError': 'BadVariantLoadError',
        'DatetimeFormatMismatch': 'FormatMismatchLoadError',
    },
)
