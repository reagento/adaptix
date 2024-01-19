from abc import ABC
from enum import Enum, EnumMeta, Flag
from typing import Any, Mapping, Optional, Type

from ..common import Dumper, Loader, TypeHint
from ..morphing.provider_template import DumperProvider, LoaderProvider
from ..provider.essential import CannotProvide, Mediator
from ..provider.loc_stack_filtering import DirectMediator, LastLocMapChecker
from ..provider.provider_template import for_predicate
from ..provider.request_cls import LocMap, TypeHintLoc, get_type_from_request
from ..type_tools import normalize_type
from .load_error import BadVariantError, MsgError
from .request_cls import DumperRequest, LoaderRequest


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


class EnumNameProvider(BaseEnumProvider):
    """This provider represents enum members to the outside world by their name"""

    def _provide_loader(self, mediator: Mediator, request: LoaderRequest) -> Loader:
        enum = get_type_from_request(request)

        if issubclass(enum, Flag):
            raise CannotProvide(
                "Flag subclasses is not supported yet",
                is_terminal=True,
                is_demonstrative=True
            )

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
