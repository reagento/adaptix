from dataclasses import dataclass
from typing import Dict, Any, Callable, List, Tuple

from ..essential import Request, Mediator
from ..static_provider import StaticProvider, static_provision_action


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
