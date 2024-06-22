from abc import ABC
from collections import defaultdict
from typing import (
    Any,
    Callable,
    DefaultDict,
    Dict,
    Generic,
    Iterable,
    List,
    Mapping,
    Optional,
    Sequence,
    Tuple,
    Type,
    TypeVar,
)

from ..conversion.request_cls import CoercerRequest, LinkingRequest
from ..morphing.request_cls import DumperRequest, LoaderRequest
from ..provider.essential import (
    AggregateCannotProvide,
    CannotProvide,
    Mediator,
    Provider,
    Request,
    RequestChecker,
    RequestHandler,
)
from ..provider.located_request import LocatedRequest
from ..provider.loc_stack_tools import format_loc_stack
from ..provider.location import AnyLoc
from ..provider.request_checkers import AlwaysTrueRequestChecker
from ..utils import add_note, copy_exception_dunders, with_module
from .base_retort import BaseRetort
from .builtin_mediator import BuiltinMediator, RequestBus, T
from .request_bus import BasicRequestBus, ErrorRepresentor, RecursionResolver, RecursiveRequestBus, RequestRouter
from .routers import CheckerAndHandler, SimpleRouter, create_router_for_located_request


class FuncWrapper:
    __slots__ = ("__call__",)

    def __init__(self):
        self.__call__ = None

    def set_func(self, func):
        self.__call__ = func.__call__


CallableT = TypeVar("CallableT", bound=Callable)


class LocatedRequestCallableRecursionResolver(RecursionResolver[LocatedRequest, CallableT], Generic[CallableT]):
    def __init__(self) -> None:
        self._loc_to_stub: Dict[AnyLoc, FuncWrapper] = {}

    def track_recursion(self, request: LocatedRequest) -> Optional[Any]:
        if request.loc_stack.count(request.last_loc) == 1:
            return None

        stub = FuncWrapper()
        self._loc_to_stub[request.last_loc] = stub
        return stub

    def track_response(self, request: LocatedRequest, response: CallableT) -> None:
        if request.last_loc in self._loc_to_stub:
            self._loc_to_stub.pop(request.last_loc).set_func(response)


RequestT = TypeVar("RequestT", bound=Request)
LocatedRequestT = TypeVar("LocatedRequestT", bound=LocatedRequest)


class BaseRequestErrorRepresentor(ErrorRepresentor[RequestT], Generic[RequestT]):
    def __init__(self, not_found_desc: str):
        self._not_found_desc = not_found_desc

    def get_request_context_notes(self, request: RequestT) -> Iterable[str]:
        return ()

    def get_provider_not_found_description(self, request: RequestT) -> str:
        return self._not_found_desc


class LocatedRequestErrorRepresentor(BaseRequestErrorRepresentor[LocatedRequestT], Generic[LocatedRequestT]):
    def get_request_context_notes(self, request: LocatedRequestT) -> Iterable[str]:
        loc_stack_desc = format_loc_stack(request.loc_stack)
        yield f"Location: `{loc_stack_desc}`"


class LinkingRequestErrorRepresentor(ErrorRepresentor[LinkingRequest]):
    def get_request_context_notes(self, request: RequestT) -> Iterable[str]:
        return ()

    def get_provider_not_found_description(self, request: LinkingRequest) -> str:
        dst_desc = format_loc_stack(request.destination)
        return f"Cannot find paired field of `{dst_desc}` for linking"


class CoercerRequestErrorRepresentor(BaseRequestErrorRepresentor[CoercerRequest]):
    def get_request_context_notes(self, request: CoercerRequest) -> Iterable[str]:
        src_desc = format_loc_stack(request.src)
        dst_desc = format_loc_stack(request.dst)
        yield f"Linking: `{src_desc} => {dst_desc}`"


@with_module("adaptix")
class ProviderNotFoundError(Exception):
    def __init__(self, message: str):
        self.message = message

    def __str__(self):
        return self.message


class OperatingRetort(BaseRetort, Provider, ABC):
    """A retort that can operate as Retort but have no predefined providers and no high-level user interface"""

    def _provide_from_recipe(self, request: Request[T]) -> T:
        return self._create_mediator(request).provide_from_next()

    def get_request_handlers(self) -> Sequence[Tuple[Type[Request], RequestChecker, RequestHandler]]:
        def retort_request_handler(mediator, request):
            return self._provide_from_recipe(request)

        request_classes = {
            request_cls
            for provider in self._get_full_recipe()
            for request_cls, checker, handler in provider.get_request_handlers()
        }
        return [
            (request_class, AlwaysTrueRequestChecker(), retort_request_handler)
            for request_class in request_classes
        ]

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

    def _calculate_derived(self) -> None:
        super()._calculate_derived()
        self._request_cls_to_router = self._create_request_cls_to_router(self._full_recipe)
        self._request_cls_to_error_representor = {
            request_cls: self._create_error_representor(request_cls)
            for request_cls in self._request_cls_to_router
        }

    def _create_request_cls_to_router(self, full_recipe: Sequence[Provider]) -> Mapping[Type[Request], RequestRouter]:
        request_cls_to_checkers_and_handlers: DefaultDict[Type[Request], List[CheckerAndHandler]] = defaultdict(list)
        for provider in full_recipe:
            for request_cls, checker, handler in provider.get_request_handlers():
                request_cls_to_checkers_and_handlers[request_cls].append((checker, handler))

        return {
            request_cls: self._create_router(request_cls, checkers_and_handlers)
            for request_cls, checkers_and_handlers in request_cls_to_checkers_and_handlers.items()
        }

    def _create_router(
        self,
        request_cls: Type[RequestT],
        checkers_and_handlers: Sequence[CheckerAndHandler],
    ) -> RequestRouter[RequestT]:
        if issubclass(request_cls, LocatedRequest):
            return create_router_for_located_request(checkers_and_handlers)  # type: ignore[return-value]
        return SimpleRouter(checkers_and_handlers)

    def _create_error_representor(self, request_cls: Type[RequestT]) -> ErrorRepresentor[RequestT]:
        if issubclass(request_cls, LoaderRequest):
            return LocatedRequestErrorRepresentor("Cannot find loader")
        if issubclass(request_cls, DumperRequest):
            return LocatedRequestErrorRepresentor("Cannot find dumper")
        if issubclass(request_cls, LocatedRequest):
            return LocatedRequestErrorRepresentor(f"Can not satisfy {request_cls}")

        if issubclass(request_cls, CoercerRequest):
            return CoercerRequestErrorRepresentor("Cannot find coercer")  # type: ignore[return-value]
        if issubclass(request_cls, LinkingRequest):
            return LinkingRequestErrorRepresentor()  # type: ignore[return-value]

        return BaseRequestErrorRepresentor(f"Can not satisfy {request_cls}")

    def _create_recursion_resolver(self, request_cls: Type[RequestT]) -> Optional[RecursionResolver[RequestT, Any]]:
        if issubclass(request_cls, (LoaderRequest, DumperRequest)):
            return LocatedRequestCallableRecursionResolver()  # type: ignore[return-value]
        return None

    def _create_request_bus(
        self,
        request_cls: Type[RequestT],
        router: RequestRouter[RequestT],
        mediator_factory: Callable[[Request, int], Mediator],
    ) -> RequestBus:
        error_representor = self._request_cls_to_error_representor[request_cls]
        recursion_resolver = self._create_recursion_resolver(request_cls)
        if recursion_resolver is not None:
            return RecursiveRequestBus(
                router=router,
                error_representor=error_representor,
                mediator_factory=mediator_factory,
                recursion_resolver=recursion_resolver,
            )
        return BasicRequestBus(
            router=router,
            error_representor=error_representor,
            mediator_factory=mediator_factory,
        )

    def _create_no_request_bus_error_maker(self) -> Callable[[Request], CannotProvide]:
        def no_request_bus_error_maker(request: Request) -> CannotProvide:
            return CannotProvide(f"Can not satisfy {type(request)}")

        return no_request_bus_error_maker

    def _create_mediator(self, init_request: Request[T]) -> Mediator[T]:
        request_buses: Mapping[Type[Request], RequestBus]
        no_request_bus_error_maker = self._create_no_request_bus_error_maker()

        def mediator_factory(request, search_offset):
            return BuiltinMediator(
                request_buses=request_buses,
                request=request,
                search_offset=search_offset,
                no_request_bus_error_maker=no_request_bus_error_maker,
            )

        request_buses = {
            request_cls: self._create_request_bus(request_cls, router, mediator_factory)
            for request_cls, router in self._request_cls_to_router.items()
        }
        return mediator_factory(init_request, 0)
