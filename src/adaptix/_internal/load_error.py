import dataclasses
from dataclasses import dataclass
from functools import partial
from typing import TYPE_CHECKING, Any, Iterable, Optional, Sequence

from .common import TypeHint, VarTuple
from .compat import CompatExceptionGroup


def _str_by_field(cls):
    template = ', '.join("%s={self.%s!r}" % (fld.name, fld.name) for fld in dataclasses.fields(cls))
    body = f'def __str__(self):\n    return f"{template}"'
    ns = {}
    exec(body, ns, ns)  # noqa: DUO105  # pylint: disable=exec-used
    cls.__str__ = ns['__str__']
    return cls


def _public_module(cls):
    cls.__module__ = 'adaptix.load_error'
    return cls


def custom_exception(cls=None, /, *, str_by_fields: bool = True, public_module: bool = True):
    if cls is None:
        return partial(custom_exception, str_by_fields=str_by_fields, public_module=public_module)

    if str_by_fields:
        cls = _str_by_field(cls)
    if public_module:
        cls = _public_module(cls)
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
class LoadExceptionGroup(CompatExceptionGroup, LoadError):
    message: str
    exceptions: VarTuple[LoadError]

    if TYPE_CHECKING:
        def __init__(self, message: str, exceptions: Sequence[LoadError]):
            pass


@custom_exception(str_by_fields=False)
@dataclass(eq=False)
class MsgError(LoadError):
    msg: Optional[str]

    def __str__(self):
        return self.msg


@custom_exception
@dataclass(eq=False)
class ExtraFieldsError(LoadError):
    fields: Iterable[str]


@custom_exception
@dataclass(eq=False)
class ExtraItemsError(LoadError):
    list_len: int


@custom_exception
@dataclass(eq=False)
class NoRequiredFieldsError(LoadError):
    fields: Iterable[str]


@custom_exception
@dataclass(eq=False)
class NoRequiredItemsError(LoadError):
    list_len: int


@custom_exception
@dataclass(eq=False)
class TypeLoadError(LoadError):
    expected_type: TypeHint


@custom_exception
@dataclass(eq=False)
class ExcludedTypeLoadError(LoadError):
    excluded_type: TypeHint


@custom_exception(str_by_fields=False)
@dataclass(eq=False, init=False)
class UnionLoadError(LoadExceptionGroup):
    pass


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


@custom_exception
@dataclass(eq=False)
class DatetimeFormatMismatch(LoadError):
    format: str
