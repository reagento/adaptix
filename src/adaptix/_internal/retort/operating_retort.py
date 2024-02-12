from abc import ABC
from typing import Any, Dict, Iterable, List, Mapping, Optional, Type

from ..common import TypeHint, VarTuple
from ..conversion.request_cls import CoercerRequest, LinkingRequest
from ..morphing.request_cls import DumperRequest, LoaderRequest
from ..provider.essential import AggregateCannotProvide, CannotProvide, Mediator, Provider, Request
from ..provider.request_cls import FieldLoc, LocatedRequest, LocMap, LocStack, TypeHintLoc, find_owner_with_field
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

    def track_recursion(self, request: Request[T]) -> Optional[Any]:
        if not isinstance(request, self.REQUEST_CLASSES):
            return None

        if request.loc_stack.count(request.last_map) == 1:
            return None

        stub = FuncWrapper()
        self._loc_map_to_stub[request.last_map] = stub
        return stub

    def process_request_result(self, request: Request[T], result: T) -> None:
        if isinstance(request, self.REQUEST_CLASSES) and request.last_map in self._loc_map_to_stub:
            self._loc_map_to_stub.pop(request.last_map).set_func(result)


@with_module('adaptix')
class NoSuitableProvider(Exception):
    def __init__(self, message: str):
        self.message = message


class BuiltinErrorRepresentor(ErrorRepresentor):
    _NO_PROVIDER_DESCRIPTION_METHOD: Mapping[Type[Request], str] = {
        LinkingRequest: '_get_linking_request_description',
        CoercerRequest: '_get_coercer_request_description',
    }
    _NO_PROVIDER_DESCRIPTION_CONST: Mapping[Type[Request], str] = {
        LoaderRequest: "There is no provider that can create specified loader",
        DumperRequest: "There is no provider that can create specified dumper",
    }

    def _get_linking_request_description(self, request: LinkingRequest) -> str:
        try:
            dst_owner_loc_map, dst_field_loc_map = find_owner_with_field(request.destination.to_loc_stack())
        except ValueError:
            return 'Cannot find coercer'

        dst_owner = self._get_type_desc(dst_owner_loc_map[TypeHintLoc].type)
        dst_field = dst_field_loc_map[FieldLoc].field_id
        return f"Cannot find paired field of `{dst_owner}.{dst_field}` for linking"

    def _get_coercer_request_description(self, request: CoercerRequest) -> str:
        try:
            src_owner_loc_map, src_field_loc_map = find_owner_with_field(request.src.to_loc_stack())
        except ValueError:
            return 'Cannot find coercer'

        try:
            dst_owner_loc_map, dst_field_loc_map = find_owner_with_field(request.dst.to_loc_stack())
        except ValueError:
            return 'Cannot find coercer'

        src_owner = self._get_type_desc(src_owner_loc_map[TypeHintLoc].type)
        src_field = src_field_loc_map[FieldLoc].field_id
        dst_owner = self._get_type_desc(dst_owner_loc_map[TypeHintLoc].type)
        dst_field = dst_field_loc_map[FieldLoc].field_id
        return f"Cannot find coercer for linking `{src_owner}.{src_field} -> {dst_owner}.{dst_field}`"

    def _get_type_desc(self, tp: TypeHint) -> str:
        try:
            return tp.__qualname__
        except AttributeError:
            return str(tp)

    def get_no_provider_description(self, request: Request) -> str:
        request_cls = type(request)
        if request_cls in self._NO_PROVIDER_DESCRIPTION_METHOD:
            return getattr(self, self._NO_PROVIDER_DESCRIPTION_METHOD[request_cls])(request)
        if request_cls in self._NO_PROVIDER_DESCRIPTION_CONST:
            return self._NO_PROVIDER_DESCRIPTION_CONST[request_cls]
        return f"There is no provider that can process {request}"

    _LOC_KEYS_ORDER = {fld: idx for idx, fld in enumerate(['type', 'field_id'])}

    def _get_loc_stack_context_notes(self, loc_desc: str, field_desc: str, loc_stack: LocStack) -> Iterable[str]:
        try:
            owner_loc_map, field_loc_map = find_owner_with_field(loc_stack)
        except ValueError:
            pass
        else:
            owner_type = owner_loc_map[TypeHintLoc].type
            field_id = field_loc_map[FieldLoc].field_id
            yield f'Exception was raised while processing {field_desc} {field_id!r} of {owner_type}'

        location_desc = ', '.join(
            f'{key}={value!r}'
            for key, value in sorted(
                (
                    (key, value)
                    for loc in loc_stack.last.values()
                    for key, value in vars(loc).items()
                ),
                key=lambda item: self._LOC_KEYS_ORDER.get(item[0], 1000),
            )
        )
        if location_desc:
            yield f'{loc_desc}: {location_desc}'

    def get_request_context_notes(self, request: Request) -> Iterable[str]:
        if isinstance(request, LocatedRequest):
            yield from self._get_loc_stack_context_notes(
                loc_desc='Location',
                field_desc='field',
                loc_stack=request.loc_stack,
            )


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
