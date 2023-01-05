from dataclasses import dataclass
from typing import Any, Iterable, Optional

from .common import TypeHint

# __init__ of these classes do not call super().__init__,
# but it's ok! BaseException.__init__ do nothing useful


@dataclass(eq=False)
class LoadError(Exception):
    """The base class for the exceptions that are raised
    when the loader gets invalid input data
    """


@dataclass(eq=False)
class MsgError(LoadError):
    msg: Optional[str]


@dataclass(eq=False)
class ExtraFieldsError(LoadError):
    fields: Iterable[str]


@dataclass(eq=False)
class ExtraItemsError(LoadError):
    list_len: int


@dataclass(eq=False)
class NoRequiredFieldsError(LoadError):
    fields: Iterable[str]


@dataclass(eq=False)
class NoRequiredItemsError(LoadError):
    list_len: int


@dataclass(eq=False)
class TypeLoadError(LoadError):
    expected_type: TypeHint


@dataclass(eq=False)
class ExcludedTypeLoadError(LoadError):
    excluded_type: TypeHint


@dataclass(eq=False)
class UnionLoadError(LoadError):
    sub_errors: Iterable[LoadError]


@dataclass(eq=False)
class ValueLoadError(MsgError):
    pass


@dataclass(eq=False)
class ValidationError(MsgError):
    pass


@dataclass(eq=False)
class BadVariantError(LoadError):
    allowed_values: Iterable[Any]


@dataclass(eq=False)
class DatetimeFormatMismatch(LoadError):
    format: str
