import binascii
import re
from binascii import a2b_base64, b2a_base64
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from typing import Type, TypeVar, Union

from ..common import Dumper, Loader
from ..load_error import DatetimeFormatMismatch, TypeLoadError, ValueLoadError
from ..type_tools import normalize_type
from .essential import CannotProvide, Mediator, Request
from .provider_template import DumperProvider, LoaderProvider, ProviderWithRC, for_origin
from .request_cls import DumperRequest, LoaderRequest, TypeHintLocation, replace_type
from .request_filtering import ExactTypeRC

T = TypeVar('T')


def stub(arg):
    return arg


@dataclass
class ForAnyDateTime(ProviderWithRC):
    cls: Type[Union[date, time]]

    def __post_init__(self):
        self._request_checker = ExactTypeRC(normalize_type(self.cls))

    def _check_request(self, mediator: Mediator[T], request: Request[T]) -> None:
        self._request_checker.check_request(mediator, request)


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
@for_origin(datetime)
class DatetimeFormatProvider(LoaderProvider, DumperProvider):
    format: str

    def _provide_loader(self, mediator: Mediator, request: LoaderRequest) -> Loader:
        fmt = self.format

        def datetime_format_loader(value):
            try:
                return datetime.strptime(value, fmt)
            except ValueError:
                raise DatetimeFormatMismatch(fmt)
            except TypeError:
                raise TypeLoadError(str)

        return datetime_format_loader

    def _provide_dumper(self, mediator: Mediator, request: DumperRequest) -> Dumper:
        fmt = self.format

        def datetime_format_dumper(value: datetime):
            return value.strftime(fmt)

        return datetime_format_dumper


@for_origin(timedelta)
class SecondsTimedeltaProvider(LoaderProvider, DumperProvider):
    _OK_TYPES = (int, float, Decimal)

    def _provide_loader(self, mediator: Mediator, request: LoaderRequest) -> Loader:
        ok_types = self._OK_TYPES

        def timedelta_loader(data):
            if type(data) not in ok_types:
                raise TypeLoadError(float)
            return timedelta(seconds=int(data), microseconds=int(data % 1 * 10 ** 6))

        return timedelta_loader

    def _provide_dumper(self, mediator: Mediator, request: DumperRequest) -> Dumper:
        return timedelta.total_seconds


def none_loader(data):
    if data is None:
        return None
    raise TypeLoadError(None)


@for_origin(None)
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


@for_origin(bytes)
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


@for_origin(bytearray)
class BytearrayBase64Provider(LoaderProvider, Base64DumperMixin):
    _BYTES_PROVIDER = BytesBase64Provider()

    def _provide_loader(self, mediator: Mediator, request: LoaderRequest) -> Loader:
        if not isinstance(request.loc, TypeHintLocation):
            raise CannotProvide

        bytes_loader = self._BYTES_PROVIDER.apply_provider(
            mediator, replace_type(request, bytes)
        )

        def bytearray_base64_loader(data):
            return bytearray(bytes_loader(data))

        return bytearray_base64_loader


def _regex_dumper(data: re.Pattern):
    return data.pattern


@for_origin(re.Pattern)
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
