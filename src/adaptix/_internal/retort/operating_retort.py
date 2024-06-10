from abc import ABC
from typing import Any, Dict, Iterable, List, Mapping, Optional, Type

from ..common import VarTuple
from ..conversion.request_cls import CoercerRequest, LinkingRequest
from ..morphing.request_cls import DumperRequest, LoaderRequest
from ..provider.essential import AggregateCannotProvide, CannotProvide, Mediator, Provider, Request
from ..provider.location import AnyLoc
from ..provider.request_cls import LocatedRequest, LocStack, format_loc_stack
from ..utils import add_note, copy_exception_dunders, with_module
from .base_retort import BaseRetort
from .mediator import ErrorRepresentor, RecursionResolver, T


class FuncWrapper:
    __slots__ = ("__call__",)

    def __init__(self):
        self.__call__ = None

    def set_func(self, func):
        self.__call__ = func.__call__


class MorphingRecursionResolver(RecursionResolver):
    REQUEST_CLASSES: VarTuple[Type[LocatedRequest]] = (LoaderRequest, DumperRequest)

    def __init__(self) -> None:
        self._loc_to_stub: Dict[AnyLoc, FuncWrapper] = {}

    def track_recursion(self, request: Request[T]) -> Optional[Any]:
        if not isinstance(request, self.REQUEST_CLASSES):
            return None

        if request.loc_stack.count(request.last_loc) == 1:
            return None

        stub = FuncWrapper()
        self._loc_to_stub[request.last_loc] = stub
        return stub

    def process_request_result(self, request: Request[T], result: T) -> None:
        if isinstance(request, self.REQUEST_CLASSES) and request.last_loc in self._loc_to_stub:
            self._loc_to_stub.pop(request.last_loc).set_func(result)


@with_module("adaptix")
class ProviderNotFoundError(Exception):
    def __init__(self, message: str):
        self.message = message

    def __str__(self):
        return self.message


class BuiltinErrorRepresentor(ErrorRepresentor):
    _NO_PROVIDER_DESCRIPTION_METHOD: Mapping[Type[Request], str] = {
        LinkingRequest: "_get_linking_request_description",
    }
    _NO_PROVIDER_DESCRIPTION_CONST: Mapping[Type[Request], str] = {
        LoaderRequest: "Cannot find loader",
        DumperRequest: "Cannot find dumper",
        CoercerRequest: "Cannot find coercer",
    }

    def _get_linking_request_description(self, request: LinkingRequest) -> str:
        dst_desc = self._get_loc_stack_desc(request.destination)
        return f"Cannot find paired field of `{dst_desc}` for linking"

    def get_no_provider_description(self, request: Request) -> str:
        request_cls = type(request)
        if request_cls in self._NO_PROVIDER_DESCRIPTION_METHOD:
            return getattr(self, self._NO_PROVIDER_DESCRIPTION_METHOD[request_cls])(request)
        if request_cls in self._NO_PROVIDER_DESCRIPTION_CONST:
            return self._NO_PROVIDER_DESCRIPTION_CONST[request_cls]
        return f"There is no provider that can process {request}"

    def _get_loc_stack_desc(self, loc_stack: LocStack[AnyLoc]) -> str:
        return format_loc_stack(loc_stack)

    def _get_located_request_context_notes(self, request: LocatedRequest) -> Iterable[str]:
        loc_stack_desc = self._get_loc_stack_desc(request.loc_stack)
        yield f"Location: `{loc_stack_desc}`"

    def _get_coercer_request_context_notes(self, request: CoercerRequest) -> Iterable[str]:
        src_desc = self._get_loc_stack_desc(request.src)
        dst_desc = self._get_loc_stack_desc(request.dst)
        yield f"Linking: `{src_desc} => {dst_desc}`"

    def get_request_context_notes(self, request: Request) -> Iterable[str]:
        if isinstance(request, LocatedRequest):
            yield from self._get_located_request_context_notes(request)
        elif isinstance(request, CoercerRequest):
            yield from self._get_coercer_request_context_notes(request)


class OperatingRetort(BaseRetort, Provider, ABC):
    """A retort that can operate as Retort but have no predefined providers and no high-level user interface"""

    def apply_provider(self, mediator: Mediator, request: Request[T]) -> T:
        return self._provide_from_recipe(request)

    def _facade_provide(self, request: Request[T], *, error_message: str) -> T:
        try:
            return self._provide_from_recipe(request)
        except CannotProvide as e:
            cause = self._get_exception_cause(e)
            exception = ProviderNotFoundError(error_message)
            if cause is not None:
                add_note(exception, "Note: The attached exception above contains verbose description of the problem")
            raise exception from cause

    def _get_exception_cause(self, exc: CannotProvide) -> Optional[CannotProvide]:
        if isinstance(exc, AggregateCannotProvide):
            return self._extract_demonstrative_exc(exc)
        return exc if exc.is_demonstrative else None

    def _extract_demonstrative_exc(self, exc: AggregateCannotProvide) -> Optional[CannotProvide]:
        demonstrative_exc_list: List[CannotProvide] = []
        for sub_exc in exc.exceptions:
            if isinstance(sub_exc, AggregateCannotProvide):
                sub_exc = self._extract_demonstrative_exc(sub_exc)  # type: ignore[assignment]  # noqa: PLW2901
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
