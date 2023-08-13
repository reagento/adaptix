from abc import ABC
from enum import Enum, EnumMeta, Flag
from typing import Any, Mapping, Optional, Type

from ..common import Dumper, Loader, TypeHint
from ..essential import CannotProvide, Mediator, Request
from ..load_error import BadVariantError, MsgError
from ..type_tools import normalize_type
from .provider_template import DumperProvider, LoaderProvider
from .request_cls import DumperRequest, LoaderRequest, LocatedRequest, LocMap, TypeHintLoc, get_type_from_request
from .request_filtering import DirectMediator, RequestChecker


class AnyEnumRC(RequestChecker):
    def check_request(self, mediator: DirectMediator, request: Request) -> None:
        if not isinstance(request, LocatedRequest):
            raise CannotProvide

        norm = normalize_type(get_type_from_request(request))

        if not isinstance(norm.origin, EnumMeta):
            raise CannotProvide


class BaseEnumProvider(LoaderProvider, DumperProvider, ABC):
    _request_checker = AnyEnumRC()


def _enum_name_dumper(data):
    return data.name


class EnumNameProvider(BaseEnumProvider):
    """This provider represents enum members to the outside world by their name"""

    def _provide_loader(self, mediator: Mediator, request: LoaderRequest) -> Loader:
        enum = get_type_from_request(request)

        if issubclass(enum, Flag):
            raise ValueError(f"Can not use {type(self).__name__} with Flag subclass {enum}")

        variants = [case.name for case in enum]

        def enum_loader(data):
            try:
                return enum[data]
            except KeyError:
                raise BadVariantError(variants)
            except TypeError:
                raise BadVariantError(variants)

        return enum_loader

    def _provide_dumper(self, mediator: Mediator, request: DumperRequest) -> Dumper:
        return _enum_name_dumper


class EnumValueProvider(BaseEnumProvider):
    def __init__(self, value_type: TypeHint):
        self._value_type = value_type

    def _provide_loader(self, mediator: Mediator, request: LoaderRequest) -> Loader:
        enum = get_type_from_request(request)
        value_loader = mediator.provide(
            LoaderRequest(
                loc_map=LocMap(
                    TypeHintLoc(type=self._value_type),
                )
            ),
        )

        def enum_loader(data):
            loaded_value = value_loader(data)
            try:
                return enum(loaded_value)
            except ValueError:
                raise MsgError("Bad enum value")

        return enum_loader

    def _provide_dumper(self, mediator: Mediator, request: DumperRequest) -> Dumper:
        value_dumper = mediator.provide(
            DumperRequest(
                loc_map=LocMap(
                    TypeHintLoc(type=self._value_type)
                )
            )
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
        enum = get_type_from_request(request)
        variants = [case.value for case in enum]

        value_to_member = self._get_exact_value_to_member(enum)
        if value_to_member is None:
            def enum_exact_loader(data):
                # since MyEnum(MyEnum.MY_CASE) == MyEnum.MY_CASE
                if type(data) == enum:  # pylint: disable=unidiomatic-typecheck
                    raise BadVariantError(variants)

                try:
                    return enum(data)
                except ValueError:
                    raise BadVariantError(variants)

            return enum_exact_loader

        def enum_exact_loader_v2m(data):
            try:
                return value_to_member[data]
            except KeyError:
                raise BadVariantError(variants)
            except TypeError:
                raise BadVariantError(variants)

        return enum_exact_loader_v2m

    def _get_exact_value_to_member(self, enum: Type[Enum]) -> Optional[Mapping[Any, Any]]:
        try:
            value_to_member = {case.value: case for case in enum}
        except TypeError:
            return None

        # pylint: disable=comparison-with-callable,protected-access
        if enum._missing_ != Enum._missing_:
            return None

        return value_to_member

    def _provide_dumper(self, mediator: Mediator, request: DumperRequest) -> Dumper:
        return _enum_exact_value_dumper
