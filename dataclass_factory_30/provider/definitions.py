from dataclasses import dataclass
from typing import Iterable, List

from ..common import TypeHint

# Parser calling foreign functions should convert these exceptions to ParseError
PARSER_COMPAT_EXCEPTIONS = (
    ValueError, TypeError, LookupError,
    AssertionError, ArithmeticError, AttributeError,
)

# __init__ of these classes do not call super().__init__,
# but it's ok! BaseException.__init__ do nothing useful


@dataclass
class ParseError(Exception):
    pass


@dataclass
class MsgError(ParseError):
    msg: str


@dataclass
class ExtraFieldsError(ParseError):
    fields: Iterable[str]


@dataclass
class ExtraItemsError(ParseError):
    list_len: int


@dataclass
class NoRequiredFieldsError(ParseError):
    fields: Iterable[str]


@dataclass
class NoRequiredItemsError(ParseError):
    indexes: Iterable[int]


@dataclass
class TypeParseError(ParseError):
    expected_type: TypeHint


@dataclass
class ExcludedTypeParseError(ParseError):
    excluded_type: TypeHint


@dataclass
class UnionParseError(ParseError):
    sub_errors: List[ParseError]


@dataclass
class SerializeError(Exception):
    pass
