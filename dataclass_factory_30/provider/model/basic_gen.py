import itertools
import string
from dataclasses import dataclass, replace
from typing import Dict, Any, Callable, List, Tuple, TypeVar, Iterable, Set

from .crown_definitions import BaseCrown, BaseDictCrown, BaseListCrown, BaseFieldCrown, BaseNoneCrown, BaseFigure
from .definitions import WithSkippedFields, ExtraTargets, VarBinder
from ..essential import Request, Mediator
from ..static_provider import StaticProvider, static_provision_action
from ...code_tools import CodeBuilder, ClosureCompiler


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

    @static_provision_action
    def _provide_code_gen_hook(self, mediator: Mediator, request: CodeGenHookRequest) -> CodeGenHook:
        def hook(data: CodeGenHookData):
            self.list.append((request.initial_request, data))

        return hook


T = TypeVar('T')


def _merge_iters(args: Iterable[Iterable[T]]) -> List[T]:
    return list(itertools.chain.from_iterable(args))


class DirectFieldsCollectorMixin:
    def _inner_collect_used_direct_fields(self, crown: BaseCrown) -> List[str]:
        if isinstance(crown, BaseDictCrown):
            return _merge_iters(
                self._inner_collect_used_direct_fields(sub_crown)
                for sub_crown in crown.map.values()
            )
        if isinstance(crown, BaseListCrown):
            return _merge_iters(
                self._inner_collect_used_direct_fields(sub_crown)
                for sub_crown in crown.map
            )
        if isinstance(crown, BaseFieldCrown):
            return [crown.name]
        if isinstance(crown, BaseNoneCrown):
            return []
        raise TypeError

    def _collect_used_direct_fields(self, crown: BaseCrown) -> Set[str]:
        lst = self._inner_collect_used_direct_fields(crown)

        used_set = set()
        for f_name in lst:
            if f_name in used_set:
                raise ValueError(f"Field {f_name!r} is duplicated at crown")
            used_set.add(f_name)

        return used_set


Fig = TypeVar('Fig', bound=BaseFigure)


def strip_figure(figure: Fig, skipped_fields_container: WithSkippedFields) -> Fig:
    extra = figure.extra
    if isinstance(extra, ExtraTargets):
        extra = ExtraTargets(
            tuple(
                field_name for field_name in extra.fields
                if field_name not in skipped_fields_container.skipped_fields
            )
        )

    new_figure = replace(
        figure,
        fields=tuple(
            field for field in figure.fields
            if field.name not in skipped_fields_container.skipped_fields
        ),
        extra=extra,
    )

    return new_figure


class NameSanitizer:
    _AVAILABLE_CHARS = set(string.ascii_letters + string.digits)

    def sanitize(self, name: str) -> str:
        if name == "":
            return ""

        first_letter = name[0]

        if first_letter not in string.ascii_letters:
            return self.sanitize(name[1:])

        return first_letter + "".join(
            c for c in name[1:] if c in self._AVAILABLE_CHARS
        )


def compile_closure_with_globals_capturing(
    compiler: ClosureCompiler,
    code_gen_hook: CodeGenHook,
    binder: VarBinder,
    namespace: Dict[str, object],
    body_builders: Iterable[CodeBuilder],
    *,
    closure_name: str,
    file_name: str,
):
    builder = CodeBuilder()

    global_namespace_dict = {}
    for name, value in namespace.items():
        global_name = f"g_{name}"
        global_namespace_dict[global_name] = value
        builder += f"{name} = {global_name}"

    builder.empty_line()

    with builder(f"def {closure_name}({binder.data}):"):
        for body_builder in body_builders:
            builder.extend(body_builder)

    builder += f"return {closure_name}"

    code_gen_hook(
        CodeGenHookData(
            namespace=global_namespace_dict,
            source=builder.string(),
        )
    )

    return compiler.compile(
        builder,
        file_name,
        global_namespace_dict,
    )
