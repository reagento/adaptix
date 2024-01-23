import math
from abc import ABC, abstractmethod
from enum import Enum, EnumMeta, Flag
from typing import Any, Hashable, Iterable, Mapping, Optional, Sequence, Type, TypeVar, Union, final

from ..common import Dumper, Loader, TypeHint
from ..morphing.provider_template import DumperProvider, LoaderProvider
from ..name_style import NameStyle, convert_snake_style
from ..provider.essential import Mediator
from ..provider.loc_stack_filtering import DirectMediator, LastLocMapChecker
from ..provider.provider_template import for_predicate
from ..provider.request_cls import LocMap, TypeHintLoc, get_type_from_request
from ..type_tools import normalize_type
from .load_error import BadVariantError, DuplicatedValues, MsgError, MultipleBadVariant, TypeLoadError
from .request_cls import DumperRequest, LoaderRequest

EnumT = TypeVar("EnumT", bound=Enum)
FlagT = TypeVar("FlagT", bound=Flag)


class BaseEnumMappingGenerator(ABC):
    @abstractmethod
    def _generate_mapping(self, cases: Iterable[EnumT]) -> Mapping[EnumT, Hashable]:
        ...

    @final
    def generate_for_dumping(self, cases: Iterable[EnumT]) -> Mapping[EnumT, Hashable]:
        return self._generate_mapping(cases)

    @final
    def generate_for_loading(self, cases: Iterable[EnumT]) -> Mapping[Hashable, EnumT]:
        return {
            mapping_result: case
            for case, mapping_result in self._generate_mapping(cases).items()
        }


class ByNameEnumMappingGenerator(BaseEnumMappingGenerator):
    def __init__(
        self,
        name_style: Optional[NameStyle] = None,
        map: Optional[Mapping[Union[str, Enum], str]] = None  # noqa: A002
    ):
        self._name_style = name_style
        self._map = map if map is not None else {}

    def _generate_mapping(self, cases: Iterable[EnumT]) -> Mapping[EnumT, str]:
        result = {}

        for case in cases:
            if case in self._map:
                mapped = self._map[case]
            elif case.name in self._map:
                mapped = self._map[case.name]
            elif self._name_style:
                mapped = convert_snake_style(case.name, self._name_style)
            else:
                mapped = case.name
            result[case] = mapped

        return result


class ByExactValueEnumMappingGenerator(BaseEnumMappingGenerator):
    def _generate_mapping(self, cases: Iterable[EnumT]) -> Mapping[EnumT, Hashable]:
        return {case: case.value for case in cases}


class AnyEnumLSC(LastLocMapChecker):
    def _check_location(self, mediator: DirectMediator, loc: TypeHintLoc) -> bool:
        try:
            norm = normalize_type(loc.type)
        except ValueError:
            return False
        return isinstance(norm.origin, EnumMeta)


class FlagEnumLSC(LastLocMapChecker):
    def _check_location(self, mediator: DirectMediator, loc: TypeHintLoc) -> bool:
        try:
            norm = normalize_type(loc.type)
        except ValueError:
            return False
        return issubclass(norm.origin, Flag)


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


def _extract_non_compound_cases_from_flag(enum: Type[FlagT]) -> Sequence[FlagT]:
    return [case for case in enum.__members__.values() if not math.log2(case.value) % 1]


@for_predicate(FlagEnumLSC())
class FlagProvider(BaseEnumProvider):
    def __init__(
        self,
        mapping_generator: BaseEnumMappingGenerator,
        allow_single_value: bool = False,
        allow_duplicates: bool = True,
        allow_compound: bool = True,
    ):
        self._mapping_generator = mapping_generator
        self._allow_single_value = allow_single_value
        self._allow_duplicates = allow_duplicates
        self._allow_compound = allow_compound

    def _get_cases(self, enum: Type[FlagT]) -> Sequence[FlagT]:
        if self._allow_compound:
            return list(enum.__members__.values())
        return _extract_non_compound_cases_from_flag(enum)

    def _provide_loader(self, mediator: Mediator, request: LoaderRequest) -> Loader:  # noqa: CCR001
        enum = get_type_from_request(request)

        allow_single_value = self._allow_single_value
        allow_duplicates = self._allow_duplicates

        cases = self._get_cases(enum)
        mapping = self._mapping_generator.generate_for_loading(cases)
        variants = list(mapping.keys())
        zero_case = enum(0)

        # pylint: disable=locally-disabled, unidiomatic-typecheck
        def flag_loader(data) -> Flag:
            if isinstance(data, Iterable) and type(data) != str:  # noqa: E721
                process_data = tuple(data)
            else:
                if not allow_single_value:
                    raise TypeLoadError(
                        expected_type=Union[Iterable[str], Iterable[int]],
                        input_value=data
                    )
                process_data = (data,)

            if not allow_duplicates:
                if len(process_data) != len(set(process_data)):
                    raise DuplicatedValues(data)

            bad_variants = []
            result = zero_case
            for item in process_data:
                if item not in variants:
                    bad_variants.append(item)
                    continue
                result |= mapping[item]

            if bad_variants:
                raise MultipleBadVariant(
                    allowed_values=variants,
                    invalid_values=bad_variants,
                    input_value=data,
                )

            return result

        return flag_loader

    def _provide_dumper(self, mediator: Mediator, request: DumperRequest) -> Dumper:
        enum = get_type_from_request(request)

        cases = self._get_cases(enum)
        need_to_reverse = self._allow_compound and cases != _extract_non_compound_cases_from_flag(enum)
        if need_to_reverse:
            cases = tuple(reversed(cases))

        mapping = self._mapping_generator.generate_for_dumping(cases)
        zero_case = enum(0)

        def flag_dumper(value: Flag) -> Sequence[Hashable]:
            result = []
            cases_sum = zero_case
            for case in cases:
                if case in value and case not in cases_sum:
                    cases_sum |= case
                    result.append(mapping[case])
            return list(reversed(result)) if need_to_reverse else result

        return flag_dumper
