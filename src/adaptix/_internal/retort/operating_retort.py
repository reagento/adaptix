from typing import Any, Callable, Dict, Generic, Iterable, Optional, Sequence, Type, TypeVar

from ..conversion.request_cls import CoercerRequest, LinkingRequest
from ..morphing.json_schema.definitions import JSONSchema
from ..morphing.json_schema.request_cls import InlineJSONSchemaRequest, JSONSchemaRefRequest, JSONSchemaRequest
from ..morphing.request_cls import DumperRequest, LoaderRequest
from ..provider.essential import Mediator, Provider, Request
from ..provider.loc_stack_tools import format_loc_stack
from ..provider.located_request import LocatedRequest, LocatedRequestMethodsProvider
from ..provider.location import AnyLoc
from ..provider.methods_provider import method_handler
from .request_bus import ErrorRepresentor, RecursionResolver, RequestRouter
from .routers import CheckerAndHandler, SimpleRouter, create_router_for_located_request
from .searching_retort import SearchingRetort


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

    def track_request(self, request: LocatedRequest) -> Optional[Any]:
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


class JSONSchemaMiddlewareProvider(LocatedRequestMethodsProvider):
    @method_handler
    def provide_json_schema(self, mediator: Mediator, request: JSONSchemaRequest) -> JSONSchema:
        loc_stack = request.loc_stack
        ctx = request.ctx
        json_schema = mediator.provide_from_next()
        inline = mediator.mandatory_provide(InlineJSONSchemaRequest(loc_stack=loc_stack, ctx=ctx))
        if inline:
            return json_schema
        ref = mediator.mandatory_provide(JSONSchemaRefRequest(loc_stack=loc_stack, json_schema=json_schema, ctx=ctx))
        return JSONSchema(ref=ref)


class OperatingRetort(SearchingRetort):
    """A retort that can operate as Retort but have no predefined providers and no high-level user interface"""

    def _get_recipe_head(self) -> Sequence[Provider]:
        return (
            JSONSchemaMiddlewareProvider(),
        )

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
