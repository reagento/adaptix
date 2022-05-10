from dataclasses import dataclass
from typing import Dict, Any, Callable, List, Tuple, Union, Iterable

from .. import FieldRM
from ..essential import Request, Mediator
from ..static_provider import StaticProvider, static_provision_action
from ...code_tools import PrefixManglerBase, MangledConstant, mangling_method


@dataclass
class CodeGenHookData:
    namespace: Dict[str, Any]
    source: str


CodeGenHook = Callable[[CodeGenHookData], None]


def stub_code_gen_hook(data: CodeGenHookData):
    pass


@dataclass(frozen=True)
class CodeGenHookRequest(Request[CodeGenHook]):
    initial_request: Request


class CodeGenAccumulator(StaticProvider):
    """Accumulates all generated code. It may be useful for debugging"""

    def __init__(self):
        self.list: List[Tuple[Request, CodeGenHookData]] = []

    @static_provision_action(CodeGenHookRequest)
    def _provide_code_gen_hook(self, mediator: Mediator, request: CodeGenHookRequest) -> CodeGenHook:
        def hook(data: CodeGenHookData):
            self.list.append((request.initial_request, data))

        return hook


class VarBinder(PrefixManglerBase):
    data = MangledConstant("data")
    extra = MangledConstant("extra")
    opt_fields = MangledConstant("opt_fields")

    @mangling_method("field_")
    def field(self, field: FieldRM) -> str:
        return field.name

    @mangling_method("raw_field_")
    def raw_field(self, field_name: str) -> str:
        return field_name

    @mangling_method("parser_")
    def field_parser(self, field_name: str) -> str:
        return field_name
