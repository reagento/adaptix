import math
from abc import ABC
from enum import Enum, EnumMeta, Flag
from typing import Any, Iterable, Mapping, Optional, Sequence, Type, TypeVar, Union

from typing_extensions import overload

from ..common import Dumper, Loader, TypeHint
from ..morphing.provider_template import DumperProvider, LoaderProvider
from ..provider.essential import Mediator
from ..provider.loc_stack_filtering import DirectMediator, LastLocMapChecker
from ..provider.provider_template import for_predicate
from ..provider.request_cls import LocMap, TypeHintLoc, get_type_from_request
from ..type_tools import normalize_type
from .load_error import BadVariantError, MsgError, MultipleBadVariant, TypeLoadError, ValueLoadError
from .request_cls import DumperRequest, LoaderRequest

FlagT = TypeVar("FlagT", bound=Flag)


class AnyEnumLSC(LastLocMapChecker):
    def _check_location(self, mediator: DirectMediator, loc: TypeHintLoc) -> bool:
        try:
            norm = normalize_type(loc.type)
        except ValueError:
            return False
        return isinstance(norm.origin, EnumMeta)


@for_predicate(AnyEnumLSC())
class BaseEnumProvider(LoaderProvider, DumperProvider, ABC):
    pass


def _enum_name_dumper(data):
    return data.name


def _enum_name_loader(enum, name):
    return enum[name]


class EnumNameProvider(BaseEnumProvider):
    """This provider represents enum members to the outside world by their name"""

    def _provide_loader(self, mediator: Mediator, request: LoaderRequest) -> Loader:
        enum = get_type_from_request(request)
        variants = [case.name for case in enum]

        def enum_loader(data):
            try:
                return enum[data]
            except KeyError:
                raise BadVariantError(variants, data) from None
            except TypeError:
                raise BadVariantError(variants, data)

        return enum_loader

    def _provide_dumper(self, mediator: Mediator, request: DumperRequest) -> Dumper:
        return _enum_name_dumper


class EnumValueProvider(BaseEnumProvider):
    def __init__(self, value_type: TypeHint):
        self._value_type = value_type

    def _provide_loader(self, mediator: Mediator, request: LoaderRequest) -> Loader:
        enum = get_type_from_request(request)
        value_loader = mediator.mandatory_provide(
            LoaderRequest(
                loc_stack=request.loc_stack.append_with(
                    LocMap(
                        TypeHintLoc(type=self._value_type),
                    )
                )
            ),
        )

        def enum_loader(data):
            loaded_value = value_loader(data)
            try:
                return enum(loaded_value)
            except ValueError:
                raise MsgError("Bad enum value", data)

        return enum_loader

    def _provide_dumper(self, mediator: Mediator, request: DumperRequest) -> Dumper:
        value_dumper = mediator.mandatory_provide(
            DumperRequest(
                loc_stack=request.loc_stack.append_with(
                    LocMap(
                        TypeHintLoc(type=self._value_type)
                    )
                )
            ),
        )

        def enum_dumper(data):
            return value_dumper(data.value)

        return enum_dumper


def _enum_exact_value_dumper(data):
    return data.value


def _enum_exact_value_loader(enum, value):
    return enum(value)


class EnumExactValueProvider(BaseEnumProvider):
    """This provider represents enum members to the outside world
    by their value without any processing
    """

    def _provide_loader(self, mediator: Mediator, request: LoaderRequest) -> Loader:
        return self._make_loader(get_type_from_request(request))

    def _make_loader(self, enum):
        variants = [case.value for case in enum]

        value_to_member = self._get_exact_value_to_member(enum)
        if value_to_member is None:
            def enum_exact_loader(data):
                # since MyEnum(MyEnum.MY_CASE) == MyEnum.MY_CASE
                if type(data) is enum:  # pylint: disable=unidiomatic-typecheck
                    raise BadVariantError(variants, data)

                try:
                    return enum(data)
                except ValueError:
                    raise BadVariantError(variants, data) from None

            return enum_exact_loader

        def enum_exact_loader_v2m(data):
            try:
                return value_to_member[data]
            except KeyError:
                raise BadVariantError(variants, data) from None
            except TypeError:
                raise BadVariantError(variants, data)

        return enum_exact_loader_v2m

    def _get_exact_value_to_member(self, enum: Type[Enum]) -> Optional[Mapping[Any, Any]]:
        try:
            value_to_member = {case.value: case for case in enum}
        except TypeError:
            return None

        # pylint: disable=comparison-with-callable,protected-access
        if getattr(enum._missing_, '__func__', None) != Enum._missing_.__func__:  # type: ignore[attr-defined]
            return None

        return value_to_member

    def _provide_dumper(self, mediator: Mediator, request: DumperRequest) -> Dumper:
        return _enum_exact_value_dumper


def _extract_non_compound_cases_from_flag(enum: Type[FlagT]) -> Iterable[FlagT]:
    return [case for case in enum.__members__.values() if not math.log2(case.value) % 1]


class FlagProvider(BaseEnumProvider):
    def __init__(
        self,
        allow_single_value: bool = False,
        allow_duplicates: bool = True,
        allow_compound: bool = True,
        by_exact_value: bool = False
    ):
        self._allow_single_value = allow_single_value
        self._allow_duplicates = allow_duplicates
        self._allow_compound = allow_compound
        self._by_exact_value = by_exact_value

        self._loader = _enum_exact_value_loader if by_exact_value else _enum_name_loader
        self._dumper = _enum_exact_value_dumper if by_exact_value else _enum_name_dumper

    def _get_cases(self, enum: Type[FlagT]) -> Iterable[FlagT]:
        if self._allow_compound:
            return enum.__members__.values()
        return _extract_non_compound_cases_from_flag(enum)

    @overload
    def _get_loader_process_data(self, data: Union[int, Iterable[int]], enum: Type[Flag]) -> Sequence[int]:
        ...

    @overload
    def _get_loader_process_data(self, data: Iterable[str], enum: Type[Flag]) -> Sequence[str]:
        ...

    def _get_loader_process_data(self, data, enum):
        if isinstance(data, (str, int)):
            if not self._allow_single_value:
                raise TypeLoadError(expected_type=Iterable[str], input_value=data)
            process_data = [data]
        else:
            process_data = list(data)

        if not self._allow_duplicates:
            if len(process_data) != len(set(process_data)):
                raise ValueLoadError(
                    msg=f"Duplicates in {enum} loader are not allowed",
                    input_value=process_data
                )

        return process_data

    def _provide_loader(self, mediator: Mediator, request: LoaderRequest) -> Loader:
        enum = get_type_from_request(request)

        def _flag_loader(data: Union[int, Iterable[int], Iterable[str]]) -> Flag:
            process_data = self._get_loader_process_data(data, enum)

            variants = [self._dumper(case) for case in self._get_cases(enum)]
            bad_variants = []
            result = enum(0)
            for item in process_data:
                if item not in variants:
                    bad_variants.append(item)
                    continue
                result = result | self._loader(enum, item)

            if bad_variants:
                raise MultipleBadVariant(
                    allowed_values=variants,
                    input_value=process_data,
                    invalid_values=bad_variants
                )

            return result

        return _flag_loader

    def _provide_dumper(self, mediator: Mediator, request: DumperRequest) -> Dumper:
        enum = get_type_from_request(request)

        def flag_dumper(value: Flag) -> Union[Iterable[int], Iterable[str]]:
            cases = self._get_cases(enum)
            if value in cases:
                return [self._dumper(value)]
            return [self._dumper(case) for case in cases if case in value]

        return flag_dumper
