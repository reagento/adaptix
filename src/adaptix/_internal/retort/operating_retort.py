from abc import ABC
from typing import Any, Dict, Iterable, List, Mapping, Optional, Type

from ..common import VarTuple
from ..morphing.request_cls import DumperRequest, LoaderRequest
from ..provider.essential import AggregateCannotProvide, CannotProvide, Mediator, Provider, Request
from ..provider.request_cls import FieldLoc, LocatedRequest, LocMap, TypeHintLoc, find_owner_with_field
from ..utils import copy_exception_dunders, with_module
from .base_retort import BaseRetort
from .mediator import ErrorRepresentor, RecursionResolver, T


class FuncWrapper:
    __slots__ = ('__call__',)

    def __init__(self):
        self.__call__ = None

    def set_func(self, func):
        self.__call__ = func.__call__


class MorphingRecursionResolver(RecursionResolver):
    REQUEST_CLASSES: VarTuple[Type[LocatedRequest]] = (LoaderRequest, DumperRequest)

    def __init__(self) -> None:
        self._loc_map_to_stub: Dict[LocMap, FuncWrapper] = {}

    def process_recursion(self, request: Request[T]) -> Optional[Any]:
        if not isinstance(request, self.REQUEST_CLASSES):
            return None

        if request.loc_stack.count(request.last_map) == 1:
            return None

        stub = FuncWrapper()
        self._loc_map_to_stub[request.last_map] = stub
        return stub

    def process_request_result(self, request: Request[T], result: T) -> None:
        if isinstance(request, self.REQUEST_CLASSES) and request.last_map in self._loc_map_to_stub:
            self._loc_map_to_stub[request.last_map].set_func(result)


@with_module('adaptix')
class NoSuitableProvider(Exception):
    def __init__(self, message: str):
        self.message = message


class BuiltinErrorRepresentor(ErrorRepresentor):
    _NO_PROVIDER_DESCRIPTION_MAP: Mapping[Type[Request], str] = {
        LoaderRequest: "There is no provider that can create specified loader",
        DumperRequest: "There is no provider that can create specified dumper",
    }

    def get_no_provider_description(self, request: Request) -> str:
        try:
            return self._NO_PROVIDER_DESCRIPTION_MAP[type(request)]
        except KeyError:
            return f"There is no provider that can process {request}"

    _LOC_KEYS_ORDER = {fld: idx for idx, fld in enumerate(['type', 'field_id'])}

    def get_request_context_notes(self, request: Request) -> Iterable[str]:
        if not isinstance(request, LocatedRequest):
            return

        location_desc = ', '.join(
            f'{key}={value!r}'
            for key, value in sorted(
                (
                    (key, value)
                    for loc in request.last_map.values()
                    for key, value in vars(loc).items()
                ),
                key=lambda item: self._LOC_KEYS_ORDER.get(item[0], 1000),
            )
        )
        if location_desc:
            yield f'Location: {location_desc}'

        try:
            owner_loc_map, field_loc_map = find_owner_with_field(request.loc_stack)
        except ValueError:
            pass
        else:
            owner_type = owner_loc_map[TypeHintLoc].type
            field_id = field_loc_map[FieldLoc].field_id
            yield f'Exception was raised while processing field {field_id!r} of {owner_type}'


class OperatingRetort(BaseRetort, Provider, ABC):
    """A retort that can operate as Retort but have no predefined providers and no high-level user interface"""

    def apply_provider(self, mediator: Mediator, request: Request[T]) -> T:
        return self._provide_from_recipe(request)

    def _facade_provide(self, request: Request[T], *, error_message: str) -> T:
        try:
            return self._provide_from_recipe(request)
        except CannotProvide as e:
            cause = self._get_exception_cause(e)
            raise NoSuitableProvider(error_message) from cause

    def _get_exception_cause(self, exc: CannotProvide) -> Optional[CannotProvide]:
        if isinstance(exc, AggregateCannotProvide):
            return self._extract_demonstrative_exc(exc)
        return exc if exc.is_demonstrative else None

    def _extract_demonstrative_exc(self, exc: AggregateCannotProvide) -> Optional[CannotProvide]:
        demonstrative_exc_list: List[CannotProvide] = []
        for sub_exc in exc.exceptions:
            if isinstance(sub_exc, AggregateCannotProvide):
                sub_exc = self._extract_demonstrative_exc(sub_exc)  # type: ignore[assignment]
                if sub_exc is not None:
                    demonstrative_exc_list.append(sub_exc)
            elif sub_exc.is_demonstrative:  # type: ignore[union-attr]
                demonstrative_exc_list.append(sub_exc)  # type: ignore[arg-type]

        if not exc.is_demonstrative and not demonstrative_exc_list:
            return None
        new_exc = exc.derive_upcasting(demonstrative_exc_list)
        copy_exception_dunders(source=exc, target=new_exc)
        return new_exc

    def _create_recursion_resolver(self) -> RecursionResolver:
        return MorphingRecursionResolver()

    def _get_error_representor(self) -> ErrorRepresentor:
        return BuiltinErrorRepresentor()
