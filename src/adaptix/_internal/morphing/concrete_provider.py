import binascii
import re
import typing
from binascii import a2b_base64, b2a_base64
from dataclasses import dataclass, replace
from datetime import date, datetime, time, timedelta
from decimal import Decimal, InvalidOperation
from fractions import Fraction
from typing import Generic, Type, TypeVar, Union

from ..common import Dumper, Loader
from ..feature_requirement import HAS_PY_311, HAS_SELF_TYPE
from ..provider.essential import CannotProvide, Mediator
from ..provider.loc_stack_filtering import P, create_loc_stack_checker
from ..provider.provider_template import for_predicate
from ..provider.request_cls import LocatedRequest, StrictCoercionRequest, TypeHintLoc, find_owner_with_field
from ..provider.static_provider import static_provision_action
from ..special_cases_optimization import as_is_stub
from .load_error import FormatMismatchLoadError, TypeLoadError, ValueLoadError
from .provider_template import DumperProvider, LoaderProvider, ProviderWithAttachableLSC
from .request_cls import DumperRequest, LoaderRequest

T = TypeVar('T')


@dataclass
class IsoFormatProvider(LoaderProvider, DumperProvider):
    cls: Type[Union[date, time]]

    def __post_init__(self):
        self._loc_stack_checker = create_loc_stack_checker(self.cls)

    def _provide_loader(self, mediator: Mediator, request: LoaderRequest) -> Loader:
        raw_loader = self.cls.fromisoformat

        def isoformat_loader(data):
            try:
                return raw_loader(data)
            except TypeError:
                raise TypeLoadError(str, data)
            except ValueError:
                raise ValueLoadError("Invalid isoformat string", data)

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
                raise FormatMismatchLoadError(fmt, data)
            except TypeError:
                raise TypeLoadError(str, data)

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
                raise TypeLoadError(Union[int, float, Decimal], data)
            return timedelta(seconds=int(data), microseconds=int(data % 1 * 10 ** 6))

        return timedelta_loader

    def _provide_dumper(self, mediator: Mediator, request: DumperRequest) -> Dumper:
        return timedelta.total_seconds


def none_loader(data):
    if data is None:
        return None
    raise TypeLoadError(None, data)


@for_predicate(None)
class NoneProvider(LoaderProvider, DumperProvider):
    def _provide_loader(self, mediator: Mediator, request: LoaderRequest) -> Loader:
        return none_loader

    def _provide_dumper(self, mediator: Mediator, request: DumperRequest) -> Dumper:
        return as_is_stub


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
                raise TypeLoadError(str, data)

            if not B64_PATTERN.fullmatch(encoded):
                raise ValueLoadError('Bad base64 string', data)

            try:
                return a2b_base64(encoded)
            except binascii.Error as e:
                raise ValueLoadError(str(e), data)

        return bytes_base64_loader


@for_predicate(bytearray)
class BytearrayBase64Provider(LoaderProvider, Base64DumperMixin):
    _BYTES_PROVIDER = BytesBase64Provider()

    def _provide_loader(self, mediator: Mediator, request: LoaderRequest) -> Loader:
        request.last_map.get_or_raise(TypeHintLoc, lambda: CannotProvide)
        bytes_loader = self._BYTES_PROVIDER.apply_provider(
            mediator,
            replace(request, loc_stack=request.loc_stack.add_to_last_map(TypeHintLoc(bytes)))
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
                raise TypeLoadError(str, data)

            try:
                return re_compile(data, flags)
            except re.error as e:
                raise ValueLoadError(str(e), data)

        return regex_loader

    def _provide_dumper(self, mediator: Mediator, request: DumperRequest) -> Dumper:
        return _regex_dumper


class ScalarLoaderProvider(LoaderProvider, Generic[T]):
    def __init__(self, pred: Type[T], strict_coercion_loader: Loader[T], lax_coercion_loader: Loader[T]):
        self._loc_stack_checker = create_loc_stack_checker(pred)
        self._pred = pred
        self._strict_coercion_loader = strict_coercion_loader
        self._lax_coercion_loader = lax_coercion_loader

    def _provide_loader(self, mediator: Mediator, request: LoaderRequest) -> Loader:
        strict_coercion = mediator.mandatory_provide(StrictCoercionRequest(loc_stack=request.loc_stack))
        return self._strict_coercion_loader if strict_coercion else self._lax_coercion_loader


def int_strict_coercion_loader(data):
    if type(data) is int:  # pylint: disable=unidiomatic-typecheck
        return data
    raise TypeLoadError(int, data)


def int_lax_coercion_loader(data):
    try:
        return int(data)
    except ValueError as e:
        e_str = str(e)
        if e_str.startswith('invalid literal'):
            raise ValueLoadError("Bad string format", data)
        raise ValueLoadError(e_str, data)
    except TypeError:
        raise TypeLoadError(Union[int, float, str], data)


INT_LOADER_PROVIDER = ScalarLoaderProvider(
    pred=int,
    strict_coercion_loader=int_strict_coercion_loader,
    lax_coercion_loader=int_lax_coercion_loader,
)


def float_strict_coercion_loader(data):
    if type(data) in (float, int):
        return float(data)
    raise TypeLoadError(Union[float, int], data)


def float_lax_coercion_loader(data):
    try:
        return float(data)
    except ValueError as e:
        e_str = str(e)
        if e_str.startswith('could not convert string'):
            raise ValueLoadError("Bad string format", data)
        raise ValueLoadError(e_str, data)
    except TypeError:
        raise TypeLoadError(Union[int, float, str], data)


FLOAT_LOADER_PROVIDER = ScalarLoaderProvider(
    pred=float,
    strict_coercion_loader=float_strict_coercion_loader,
    lax_coercion_loader=float_lax_coercion_loader,
)


def str_strict_coercion_loader(data):
    if type(data) is str:  # pylint: disable=unidiomatic-typecheck
        return data
    raise TypeLoadError(str, data)


STR_LOADER_PROVIDER = ScalarLoaderProvider(
    pred=str,
    strict_coercion_loader=str_strict_coercion_loader,
    lax_coercion_loader=str,
)


def bool_strict_coercion_loader(data):
    if type(data) is bool:  # pylint: disable=unidiomatic-typecheck
        return data
    raise TypeLoadError(bool, data)


BOOL_LOADER_PROVIDER = ScalarLoaderProvider(
    pred=bool,
    strict_coercion_loader=bool_strict_coercion_loader,
    lax_coercion_loader=bool,
)


def decimal_strict_coercion_loader(data):
    if type(data) is str:  # pylint: disable=unidiomatic-typecheck
        try:
            return Decimal(data)
        except InvalidOperation:
            raise ValueLoadError("Bad string format", data)
    if type(data) is Decimal:  # pylint: disable=unidiomatic-typecheck
        return data
    raise TypeLoadError(Union[str, Decimal], data)


def decimal_lax_coercion_loader(data):
    try:
        return Decimal(data)
    except InvalidOperation:
        raise ValueLoadError("Bad string format", data)
    except TypeError:
        raise TypeLoadError(Union[str, Decimal], data)
    except ValueError as e:
        raise ValueLoadError(str(e), data)


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
            raise ValueLoadError("Bad string format", data)
    raise TypeLoadError(Union[str, Fraction], data)


def fraction_lax_coercion_loader(data):
    try:
        return Fraction(data)
    except TypeError:
        raise TypeLoadError(Union[str, Fraction], data)
    except ValueError as e:
        str_e = str(e)
        if str_e.startswith('Invalid literal'):
            raise ValueLoadError("Bad string format", data)
        raise ValueLoadError(str(e), data)


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
            raise ValueLoadError("Bad string format", data)
    raise TypeLoadError(Union[str, complex], data)


def complex_lax_coercion_loader(data):
    try:
        return complex(data)
    except TypeError:
        raise TypeLoadError(Union[str, complex], data)
    except ValueError:
        raise ValueLoadError("Bad string format", data)


COMPLEX_LOADER_PROVIDER = ScalarLoaderProvider(
    pred=complex,
    strict_coercion_loader=complex_strict_coercion_loader,
    lax_coercion_loader=complex_lax_coercion_loader,
)


@for_predicate(typing.Self if HAS_SELF_TYPE else ~P.ANY)
class SelfTypeProvider(ProviderWithAttachableLSC):
    @static_provision_action
    def _provide_substitute(self, mediator: Mediator, request: LocatedRequest) -> Loader:
        self._apply_loc_stack_checker(mediator, request)

        try:
            owner_loc_map, _field_loc_map = find_owner_with_field(request.loc_stack)
        except ValueError:
            raise CannotProvide(
                'Owner type is not found',
                is_terminal=True,
                is_demonstrative=True
            ) from None

        return mediator.delegating_provide(
            replace(
                request,
                loc_stack=request.loc_stack.add_to_last_map(owner_loc_map[TypeHintLoc])
            ),
        )


@for_predicate(typing.LiteralString if HAS_PY_311 else ~P.ANY)
class LiteralStringProvider(LoaderProvider, DumperProvider):
    def _provide_loader(self, mediator: Mediator, request: LoaderRequest) -> Loader:
        strict_coercion = mediator.mandatory_provide(StrictCoercionRequest(loc_stack=request.loc_stack))
        return str_strict_coercion_loader if strict_coercion else str  # type: ignore[return-value]

    def _provide_dumper(self, mediator: Mediator, request: DumperRequest) -> Dumper:
        return as_is_stub
