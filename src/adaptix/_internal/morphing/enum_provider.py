import math
from abc import ABC, abstractmethod
from enum import Enum, EnumMeta, Flag
from functools import reduce
from operator import or_
from typing import Any, Hashable, Iterable, List, Mapping, MutableMapping, Optional, Sequence, Type, TypeVar, Union

from ..common import Dumper, Loader, TypeHint
from ..morphing.provider_template import DumperProvider, LoaderProvider
from ..name_style import NameStyle, convert_snake_style
from ..provider.essential import CannotProvide, Mediator
from ..provider.loc_stack_filtering import DirectMediator, LastLocMapChecker
from ..provider.provider_template import for_predicate
from ..provider.request_cls import LocMap, TypeHintLoc, get_type_from_request
from ..type_tools import is_subclass_soft, normalize_type
from .load_error import BadVariantError, DuplicatedValues, MsgError, MultipleBadVariant, OutOfRange, TypeLoadError
from .request_cls import DumperRequest, LoaderRequest

EnumT = TypeVar("EnumT", bound=Enum)
FlagT = TypeVar("FlagT", bound=Flag)


class BaseEnumMappingGenerator(ABC):
    @abstractmethod
    def generate_for_dumping(self, cases: Mapping[str, EnumT]) -> Mapping[EnumT, Hashable]:
        ...

    @abstractmethod
    def generate_for_loading(self, cases: Mapping[str, EnumT]) -> Mapping[str, Hashable]:
        ...


class ByNameEnumMappingGenerator(BaseEnumMappingGenerator):
    def __init__(
        self,
        name_style: Optional[NameStyle] = None,
        map: Optional[Mapping[Union[str, Enum], str]] = None  # noqa: A002
    ):
        self._name_style = name_style
        self._map = map if map is not None else {}

    def generate_for_dumping(self, cases: Mapping[str, EnumT]) -> Mapping[EnumT, str]:
        result = {}

        for case in cases.values():
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

    def generate_for_loading(self, cases: Mapping[str, EnumT]) -> Mapping[str, EnumT]:
        result: MutableMapping[str, EnumT] = {}

        for name, case in cases.items():
            if case in self._map and case not in result.values():
                mapped = self._map[case]
            elif name in self._map:
                mapped = self._map[name]
            elif self._name_style:
                mapped = convert_snake_style(name, self._name_style)
            else:
                mapped = name
            result[mapped] = case

        return result


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
        return is_subclass_soft(norm.origin, Flag)


@for_predicate(AnyEnumLSC())
class BaseEnumProvider(LoaderProvider, DumperProvider, ABC):
    pass


def _enum_name_dumper(data):
    return data.name


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


@for_predicate(FlagEnumLSC())
class FlagByExactValueProvider(BaseEnumProvider):
    def _provide_loader(self, mediator: Mediator, request: LoaderRequest) -> Loader:
        enum = get_type_from_request(request)
        flag_mask = reduce(or_, enum.__members__.values()).value

        if flag_mask < 0:
            raise CannotProvide(
                "Cannot create a loader for flag with negative values",
                is_terminal=True,
                is_demonstrative=True,
            )

        all_bits = 2 ** flag_mask.bit_length() - 1
        if all_bits != flag_mask:
            raise CannotProvide(
                "Cannot create a loader for flag with skipped bits",
                is_terminal=True,
                is_demonstrative=True,
            )

        def flag_loader(data):
            if type(data) is not int:   # pylint: disable=unidiomatic-typecheck
                raise TypeLoadError(int, data)

            if not 0 <= data <= flag_mask:
                raise OutOfRange(0, flag_mask, data)

            return enum(data)

        return flag_loader

    def _provide_dumper(self, mediator: Mediator, request: DumperRequest) -> Dumper:
        return _enum_exact_value_dumper


def _extract_non_compound_cases_from_flag(enum: Type[FlagT]) -> Mapping[str, FlagT]:
    return {name: case for name, case in enum.__members__.items() if not math.log2(case.value) % 1}


@for_predicate(FlagEnumLSC())
class FlagByListProvider(BaseEnumProvider):
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

    def _get_cases(self, enum: Type[FlagT]) -> Mapping[str, FlagT]:
        if self._allow_compound:
            return enum.__members__
        return _extract_non_compound_cases_from_flag(enum)

    def _provide_loader(self, mediator: Mediator, request: LoaderRequest) -> Loader:  # noqa: CCR001
        enum = get_type_from_request(request)

        allow_single_value = self._allow_single_value
        allow_duplicates = self._allow_duplicates

        cases = self._get_cases(enum)
        mapping = self._mapping_generator.generate_for_loading(cases)
        variants = list(mapping.keys())
        zero_case = enum(0)

        def flag_loader(data) -> Flag:
            if isinstance(data, Iterable) and type(data) is not str:  # pylint: disable=unidiomatic-typecheck
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

        mapping = self._mapping_generator.generate_for_dumping(cases)

        if need_to_reverse:
            cases_sequence = tuple(reversed(cases.values()))
        else:
            cases_sequence = tuple(cases.values())

        zero_case = enum(0)

        def flag_dumper(value: Flag) -> Sequence[Hashable]:
            result: List[Hashable] = []
            cases_sum = zero_case
            for case in cases_sequence:
                if case in value and case not in cases_sum:
                    cases_sum |= case
                    result.append(mapping[case])
            return list(reversed(result)) if need_to_reverse else result

        return flag_dumper
