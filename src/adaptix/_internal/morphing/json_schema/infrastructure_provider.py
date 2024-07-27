from ...provider.essential import Mediator
from ...provider.located_request import LocatedRequestMethodsProvider
from ...provider.methods_provider import method_handler
from .definitions import JSONSchemaRef
from .request_cls import InlineJSONSchemaRequest, JSONSchemaRefRequest


class InlineJSONSchemaProvider(LocatedRequestMethodsProvider):
    def __init__(self, *, inline: bool):
        self._inline = inline

    @method_handler
    def provide_inline_json_schema(self, mediator: Mediator, request: InlineJSONSchemaRequest) -> bool:
        return self._inline


class JSONSchemaRefProvider(LocatedRequestMethodsProvider):
    def __init__(self, *, inline: bool):
        self._inline = inline

    @method_handler
    def provide_json_schema_ref(self, mediator: Mediator, request: JSONSchemaRefRequest) -> JSONSchemaRef:
        return JSONSchemaRef(
            value=self._get_reference_value(request),
            is_final=False,
            json_schema=request.json_schema,
            loc_stack=request.loc_stack,
        )

    def _get_reference_value(self, request: JSONSchemaRefRequest) -> str:
        return str(request.loc_stack.last.type)


class ConstantJSONSchemaRefProvider(LocatedRequestMethodsProvider):
    def __init__(self, ref_value: str):
        self._ref_value = ref_value

    @method_handler
    def provide_json_schema_ref(self, mediator: Mediator, request: JSONSchemaRefRequest) -> JSONSchemaRef:
        return JSONSchemaRef(
            value=self._ref_value,
            is_final=True,
            json_schema=request.json_schema,
            loc_stack=request.loc_stack,
        )
