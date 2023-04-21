import binascii
import re
from binascii import a2b_base64, b2a_base64
from dataclasses import dataclass, replace
from datetime import date, datetime, time, timedelta
from decimal import Decimal, InvalidOperation
from fractions import Fraction
from typing import Generic, Type, TypeVar, Union

from adaptix._internal.provider.model.special_cases_optimization import none_loader

from ..common import Dumper, Loader
from ..load_error import DatetimeFormatMismatch, TypeLoadError, ValueLoadError
from .essential import CannotProvide, Mediator
from .provider_template import DumperProvider, LoaderProvider, ProviderWithAttachableRC, for_predicate
from .request_cls import DumperRequest, LoaderRequest, StrictCoercionRequest, TypeHintLoc
from .request_filtering import create_request_checker

T = TypeVar('T')


def stub(arg):
    return arg


@dataclass
class ForAnyDateTime(ProviderWithAttachableRC):
    cls: Type[Union[date, time]]

    def __post_init__(self):
        self._request_checker = create_request_checker(self.cls)


@dataclass
class IsoFormatProvider(ForAnyDateTime, LoaderProvider, DumperProvider):
    def _provide_loader(self, mediator: Mediator, request: LoaderRequest) -> Loader:
        raw_loader = self.cls.fromisoformat

        def isoformat_loader(data):
            try:
                return raw_loader(data)
            except TypeError:
                raise TypeLoadError(str)
            except ValueError:
                raise ValueLoadError("Invalid isoformat string")

        return isoformat_loader

    def _provide_dumper(self, mediator: Mediator, request: DumperRequest) -> Dumper:
        return self.cls.isoformat


@dataclass
@for_predicate(datetime)
class DatetimeFormatProvider(LoaderProvider, DumperProvider):
    format: str

    def _provide_loader(self, mediator: Mediator, request: LoaderRequest) -> Loader:
        fmt = self.format

        def datetime_format_loader(data):
            try:
                return datetime.strptime(data, fmt)
            except ValueError:
                raise DatetimeFormatMismatch(fmt)
            except TypeError:
                raise TypeLoadError(str)

        return datetime_format_loader

    def _provide_dumper(self, mediator: Mediator, request: DumperRequest) -> Dumper:
        fmt = self.format

        def datetime_format_dumper(data: datetime):
            return data.strftime(fmt)

        return datetime_format_dumper


@for_predicate(timedelta)
class SecondsTimedeltaProvider(LoaderProvider, DumperProvider):
    _OK_TYPES = (int, float, Decimal)

    def _provide_loader(self, mediator: Mediator, request: LoaderRequest) -> Loader:
        ok_types = self._OK_TYPES

        def timedelta_loader(data):
            if type(data) not in ok_types:
                raise TypeLoadError(Union[int, float, Decimal])
            return timedelta(seconds=int(data), microseconds=int(data % 1 * 10 ** 6))

        return timedelta_loader

    def _provide_dumper(self, mediator: Mediator, request: DumperRequest) -> Dumper:
        return timedelta.total_seconds


@for_predicate(None)
class NoneProvider(LoaderProvider, DumperProvider):
    def _provide_loader(self, mediator: Mediator, request: LoaderRequest) -> Loader:
        return none_loader

    def _provide_dumper(self, mediator: Mediator, request: DumperRequest) -> Dumper:
        return stub


class Base64DumperMixin(DumperProvider):
    def _provide_dumper(self, mediator: Mediator, request: DumperRequest) -> Dumper:
        def bytes_base64_dumper(data):
            return b2a_base64(data, newline=False).decode('ascii')

        return bytes_base64_dumper


B64_PATTERN = re.compile(b'[A-Za-z0-9+/]*={0,2}')


@for_predicate(bytes)
class BytesBase64Provider(LoaderProvider, Base64DumperMixin):
    def _provide_loader(self, mediator: Mediator, request: LoaderRequest) -> Loader:
        def bytes_base64_loader(data):
            try:
                encoded = data.encode('ascii')
            except AttributeError:
                raise TypeLoadError(str)

            if not B64_PATTERN.fullmatch(encoded):
                raise ValueLoadError('Bad base64 string')

            try:
                return a2b_base64(encoded)
            except binascii.Error as e:
                raise ValueLoadError(str(e))

        return bytes_base64_loader


@for_predicate(bytearray)
class BytearrayBase64Provider(LoaderProvider, Base64DumperMixin):
    _BYTES_PROVIDER = BytesBase64Provider()

    def _provide_loader(self, mediator: Mediator, request: LoaderRequest) -> Loader:
        request.loc_map.get_or_raise(TypeHintLoc, lambda: CannotProvide)
        bytes_loader = self._BYTES_PROVIDER.apply_provider(
            mediator, replace(request, loc_map=request.loc_map.add(TypeHintLoc(bytes)))
        )

        def bytearray_base64_loader(data):
            return bytearray(bytes_loader(data))

        return bytearray_base64_loader


def _regex_dumper(data: re.Pattern):
    return data.pattern


@for_predicate(re.Pattern)
class RegexPatternProvider(LoaderProvider, DumperProvider):
    def __init__(self, flags: re.RegexFlag = re.RegexFlag(0)):
        self.flags = flags

    def _provide_loader(self, mediator: Mediator, request: LoaderRequest) -> Loader:
        flags = self.flags
        re_compile = re.compile

        def regex_loader(data):
            if not isinstance(data, str):
                raise TypeLoadError(str)

            try:
                return re_compile(data, flags)
            except re.error as e:
                raise ValueLoadError(str(e))

        return regex_loader

    def _provide_dumper(self, mediator: Mediator, request: DumperRequest) -> Dumper:
        return _regex_dumper


class ScalarLoaderProvider(LoaderProvider, Generic[T]):
    def __init__(self, pred: Type[T], strict_coercion_loader: Loader[T], lax_coercion_loader: Loader[T]):
        self._request_checker = create_request_checker(pred)
        self._pred = pred
        self._strict_coercion_loader = strict_coercion_loader
        self._lax_coercion_loader = lax_coercion_loader

    def _provide_loader(self, mediator: Mediator, request: LoaderRequest) -> Loader:
        strict_coercion = mediator.provide(StrictCoercionRequest(loc_map=request.loc_map))
        return self._strict_coercion_loader if strict_coercion else self._lax_coercion_loader


def int_strict_coercion_loader(data):
    if type(data) == int:  # pylint: disable=unidiomatic-typecheck
        return data
    raise TypeLoadError(int)


def int_lax_coercion_loader(data):
    try:
        return int(data)
    except ValueError as e:
        e_str = str(e)
        if e_str.startswith('invalid literal'):
            raise ValueLoadError("Bad string format")
        raise ValueLoadError(e_str)
    except TypeError:
        raise TypeLoadError(Union[int, float, str])


INT_LOADER_PROVIDER = ScalarLoaderProvider(
    pred=int,
    strict_coercion_loader=int_strict_coercion_loader,
    lax_coercion_loader=int_lax_coercion_loader,
)


def float_strict_coercion_loader(data):
    if type(data) in (float, int):
        return float(data)
    raise TypeLoadError(Union[float, int])


def float_lax_coercion_loader(data):
    try:
        return float(data)
    except ValueError as e:
        e_str = str(e)
        if e_str.startswith('could not convert string'):
            raise ValueLoadError("Bad string format")
        raise ValueLoadError(e_str)
    except TypeError:
        raise TypeLoadError(Union[int, float, str])


FLOAT_LOADER_PROVIDER = ScalarLoaderProvider(
    pred=float,
    strict_coercion_loader=float_strict_coercion_loader,
    lax_coercion_loader=float_lax_coercion_loader,
)


def str_strict_coercion_loader(data):
    if type(data) == str:  # pylint: disable=unidiomatic-typecheck
        return data
    raise TypeLoadError(str)


STR_LOADER_PROVIDER = ScalarLoaderProvider(
    pred=str,
    strict_coercion_loader=str_strict_coercion_loader,
    lax_coercion_loader=str,
)


def bool_strict_coercion_loader(data):
    if type(data) == bool:  # pylint: disable=unidiomatic-typecheck
        return data
    raise TypeLoadError(bool)


BOOL_LOADER_PROVIDER = ScalarLoaderProvider(
    pred=bool,
    strict_coercion_loader=bool_strict_coercion_loader,
    lax_coercion_loader=bool,
)


def decimal_strict_coercion_loader(data):
    if type(data) == str:  # pylint: disable=unidiomatic-typecheck
        try:
            return Decimal(data)
        except InvalidOperation:
            raise ValueLoadError("Bad string format")
    if type(data) == Decimal:  # pylint: disable=unidiomatic-typecheck
        return data
    raise TypeLoadError(Union[str, Decimal])


def decimal_lax_coercion_loader(data):
    try:
        return Decimal(data)
    except InvalidOperation:
        raise ValueLoadError("Bad string format")
    except TypeError:
        raise TypeLoadError(Union[str, Decimal])
    except ValueError as e:
        raise ValueLoadError(str(e))


DECIMAL_LOADER_PROVIDER = ScalarLoaderProvider(
    pred=Decimal,
    strict_coercion_loader=decimal_strict_coercion_loader,
    lax_coercion_loader=decimal_lax_coercion_loader,
)


def fraction_strict_coercion_loader(data):
    if type(data) in (str, Fraction):
        try:
            return Fraction(data)
        except ValueError:
            raise ValueLoadError("Bad string format")
    raise TypeLoadError(Union[str, Fraction])


def fraction_lax_coercion_loader(data):
    try:
        return Fraction(data)
    except TypeError:
        raise TypeLoadError(Union[str, Fraction])
    except ValueError as e:
        str_e = str(e)
        if str_e.startswith('Invalid literal'):
            raise ValueLoadError("Bad string format")
        raise ValueLoadError(str(e))


FRACTION_LOADER_PROVIDER = ScalarLoaderProvider(
    pred=Fraction,
    strict_coercion_loader=fraction_strict_coercion_loader,
    lax_coercion_loader=fraction_lax_coercion_loader,
)


def complex_strict_coercion_loader(data):
    if type(data) in (str, complex):
        try:
            return complex(data)
        except ValueError:
            raise ValueLoadError("Bad string format")
    raise TypeLoadError(Union[str, complex])


def complex_lax_coercion_loader(data):
    try:
        return complex(data)
    except TypeError:
        raise TypeLoadError(Union[str, complex])
    except ValueError:
        raise ValueLoadError("Bad string format")


COMPLEX_LOADER_PROVIDER = ScalarLoaderProvider(
    pred=complex,
    strict_coercion_loader=complex_strict_coercion_loader,
    lax_coercion_loader=complex_lax_coercion_loader,
)
