from collections import deque
from dataclasses import dataclass
from typing import Any, Callable, Union, List, Optional, Deque, Iterable

from ..common import TypeHint
from ..utils import SingletonMeta


class NoDefault(metaclass=SingletonMeta):
    pass


@dataclass(frozen=True)
class DefaultValue:
    value: Any


@dataclass(frozen=True)
class DefaultFactory:
    factory: Callable[[], Any]


Default = Union[NoDefault, DefaultValue, DefaultFactory]

# Parser calling foreign functions should convert these exceptions to ParseError
PARSER_COMPAT_EXCEPTIONS = (ValueError, TypeError, AttributeError, LookupError)

# In most cases path is Union[str, int]
# but we decided to retain the option for a custom path
PathElement = Union[str, int, Any]


class ParseError(Exception):
    path: Deque[PathElement]

    def __init__(self, path: Optional[Deque[PathElement]] = None):
        if path is None:
            self.path = deque()
        else:
            self.path = path

        Exception.__init__(self)

    def append_path(self, element: PathElement):
        self.path.appendleft(element)

    def extend_path(self, sub_path: Iterable[PathElement]):
        self.path.extendleft(sub_path)

    def __str__(self):
        return f"{type(self).__name__}(path={self.path})"

    def __eq__(self, other):
        if type(self) == type(other):
            return vars(self) == vars(other)
        return NotImplemented


class MsgError(ParseError):
    def __init__(self, msg: str, path: Optional[Deque[PathElement]] = None):
        self.msg = msg
        ParseError.__init__(self, path)


class ExtraFieldsError(ParseError):
    def __init__(self, fields: Iterable[str], path: Optional[Deque[PathElement]] = None):
        self.fields = fields
        ParseError.__init__(self, path)


class ExtraItemsError(ParseError):
    def __init__(self, list_len: int, path: Optional[Deque[PathElement]] = None):
        self.list_len = list_len
        ParseError.__init__(self, path)


class NoRequiredFieldsError(ParseError):
    def __init__(self, fields: Iterable[str], path: Optional[Deque[PathElement]] = None):
        self.fields = fields
        ParseError.__init__(self, path)


class NoRequiredItemsError(ParseError):
    def __init__(self, indexes: Iterable[int], path: Optional[Deque[PathElement]] = None):
        self.indexes = indexes
        ParseError.__init__(self, path)


class TypeParseError(ParseError):
    def __init__(self, expected_type: TypeHint, path: Optional[Deque[PathElement]] = None):
        self.expected_type = expected_type
        ParseError.__init__(self, path)


class ExcludedTypeParseError(ParseError):
    def __init__(self, excluded_type: TypeHint, path: Optional[Deque[PathElement]] = None):
        self.excluded_type = excluded_type
        ParseError.__init__(self, path)


class UnionParseError(ParseError):
    def __init__(self, sub_errors: List[ParseError], path: Optional[Deque[PathElement]] = None):
        self.sub_errors = sub_errors
        ParseError.__init__(self, path)
