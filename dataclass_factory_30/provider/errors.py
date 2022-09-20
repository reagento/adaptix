from dataclasses import dataclass
from typing import Any, Iterable, List, Optional

from ..common import TypeHint

# __init__ of these classes do not call super().__init__,
# but it's ok! BaseException.__init__ do nothing useful


@dataclass(eq=False)
class ParseError(Exception):
    """The base class for the exceptions that are raised
    when the parser gets invalid input data
    """


@dataclass(eq=False)
class MsgError(ParseError):
    msg: Optional[str]


@dataclass(eq=False)
class ExtraFieldsError(ParseError):
    fields: Iterable[str]


@dataclass(eq=False)
class ExtraItemsError(ParseError):
    list_len: int


@dataclass(eq=False)
class NoRequiredFieldsError(ParseError):
    fields: Iterable[str]


@dataclass(eq=False)
class NoRequiredItemsError(ParseError):
    list_len: int


@dataclass(eq=False)
class TypeParseError(ParseError):
    expected_type: TypeHint


@dataclass(eq=False)
class ExcludedTypeParseError(ParseError):
    excluded_type: TypeHint


@dataclass(eq=False)
class UnionParseError(ParseError):
    sub_errors: List[ParseError]


@dataclass(eq=False)
class ValueParseError(MsgError):
    pass


@dataclass(eq=False)
class ValidationError(MsgError):
    pass


@dataclass(eq=False)
class BadVariantError(ParseError):
    allowed_values: Iterable[Any]
