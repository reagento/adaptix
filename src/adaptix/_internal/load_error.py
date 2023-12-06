import dataclasses
from dataclasses import dataclass
from functools import partial
from typing import Any, Iterable, Optional

from .common import TypeHint, VarTuple
from .compat import CompatExceptionGroup
from .utils import with_module


def _str_by_fields(cls):
    template = ', '.join("%s={self.%s!r}" % (fld.name, fld.name) for fld in dataclasses.fields(cls))
    body = f'def __str__(self):\n    return f"{template}"'
    ns = {}
    exec(body, ns, ns)  # noqa: DUO105  # pylint: disable=exec-used
    cls.__str__ = ns['__str__']
    return cls


def custom_exception(cls=None, /, *, str_by_fields: bool = True, public_module: bool = True):
    if cls is None:
        return partial(custom_exception, str_by_fields=str_by_fields, public_module=public_module)

    if str_by_fields:
        cls = _str_by_fields(cls)
    if public_module:
        cls = with_module('adaptix.load_error')(cls)
    return cls


# __init__ of these classes do not call super().__init__, but it's ok!
# BaseException.__init__ does nothing useful


@custom_exception(str_by_fields=False)
@dataclass(eq=False, init=False)
class LoadError(Exception):
    """The base class for the exceptions that are raised
    when the loader gets invalid input data
    """


@custom_exception(str_by_fields=False)
@dataclass(eq=False, init=False)
class LoadExceptionGroup(CompatExceptionGroup[LoadError], LoadError):
    """The base class integrating ``ExceptionGroup`` into the ``LoadError`` hierarchy"""

    message: str
    exceptions: VarTuple[LoadError]


@custom_exception(str_by_fields=False)
@dataclass(eq=False, init=False)
class AggregateLoadError(LoadExceptionGroup):
    """The class collecting distinct load errors"""


@custom_exception(str_by_fields=False)
@dataclass(eq=False, init=False)
class UnionLoadError(LoadExceptionGroup):
    pass


@custom_exception
@dataclass(eq=False)
class MsgError(LoadError):
    msg: Optional[str]
    input_value: Any


@custom_exception
@dataclass(eq=False)
class ExtraFieldsError(LoadError):
    fields: Iterable[str]
    input_value: Any


@custom_exception
@dataclass(eq=False)
class ExtraItemsError(LoadError):
    expected_len: int
    input_value: Any


@custom_exception
@dataclass(eq=False)
class NoRequiredFieldsError(LoadError):
    fields: Iterable[str]
    input_value: Any


@custom_exception
@dataclass(eq=False)
class NoRequiredItemsError(LoadError):
    expected_len: int
    input_value: Any


@custom_exception
@dataclass(eq=False)
class TypeLoadError(LoadError):
    expected_type: TypeHint
    input_value: Any


@custom_exception
@dataclass(eq=False)
class ExcludedTypeLoadError(TypeLoadError):
    expected_type: TypeHint
    excluded_type: TypeHint
    input_value: Any


@custom_exception(str_by_fields=False)
@dataclass(eq=False)
class ValueLoadError(MsgError):
    pass


@custom_exception(str_by_fields=False)
@dataclass(eq=False)
class ValidationError(MsgError):
    pass


@custom_exception
@dataclass(eq=False)
class BadVariantError(LoadError):
    allowed_values: Iterable[Any]
    input_value: Any


@custom_exception
@dataclass(eq=False)
class DatetimeFormatMismatch(LoadError):
    format: str
    input_value: Any
