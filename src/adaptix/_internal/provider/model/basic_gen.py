import itertools
import string
from dataclasses import dataclass, replace
from typing import (
    Any,
    Callable,
    Collection,
    Container,
    Dict,
    Iterable,
    List,
    Mapping,
    Sequence,
    Set,
    Tuple,
    TypeVar,
    Union,
)

from ...code_tools import ClosureCompiler, CodeBuilder, get_literal_expr
from ...model_tools import InputField, OutputField
from ..essential import Mediator, Request
from ..static_provider import StaticProvider, static_provision_action
from .crown_definitions import (
    BaseCrown,
    BaseDictCrown,
    BaseFieldCrown,
    BaseFigure,
    BaseListCrown,
    BaseNameLayout,
    BaseNoneCrown,
    ExtraCollect,
    ExtraTargets,
    InpCrown,
    InpDictCrown,
    InpExtraMove,
    InpFieldCrown,
    InpListCrown,
    InpNoneCrown,
    OutExtraMove,
)
from .definitions import VarBinder


@dataclass
class CodeGenHookData:
    namespace: Dict[str, Any]
    source: str


CodeGenHook = Callable[[CodeGenHookData], None]


def stub_code_gen_hook(data: CodeGenHookData):
    pass


@dataclass(frozen=True)
class CodeGenHookRequest(Request[CodeGenHook]):
    pass


class CodeGenAccumulator(StaticProvider):
    """Accumulates all generated code. It may be useful for debugging"""

    def __init__(self) -> None:
        self.list: List[Tuple[Sequence[Request], CodeGenHookData]] = []

    @static_provision_action
    def _provide_code_gen_hook(self, mediator: Mediator, request: CodeGenHookRequest) -> CodeGenHook:
        request_stack = mediator.request_stack

        def hook(data: CodeGenHookData):
            self.list.append((request_stack, data))

        return hook


T = TypeVar('T')


def _concatenate_iters(args: Iterable[Iterable[T]]) -> Collection[T]:
    return list(itertools.chain.from_iterable(args))


def _inner_collect_used_direct_fields(crown: BaseCrown) -> Iterable[str]:
    if isinstance(crown, BaseDictCrown):
        return _concatenate_iters(
            _inner_collect_used_direct_fields(sub_crown)
            for sub_crown in crown.map.values()
        )
    if isinstance(crown, BaseListCrown):
        return _concatenate_iters(
            _inner_collect_used_direct_fields(sub_crown)
            for sub_crown in crown.map
        )
    if isinstance(crown, BaseFieldCrown):
        return [crown.name]
    if isinstance(crown, BaseNoneCrown):
        return []
    raise TypeError


def _collect_used_direct_fields(crown: BaseCrown) -> Set[str]:
    lst = _inner_collect_used_direct_fields(crown)

    used_set = set()
    for f_name in lst:
        if f_name in used_set:
            raise ValueError(f"Field {f_name!r} is duplicated at crown")
        used_set.add(f_name)

    return used_set


def get_skipped_fields(figure: BaseFigure, name_layout: BaseNameLayout) -> Collection[str]:
    used_direct_fields = _collect_used_direct_fields(name_layout.crown)
    if isinstance(name_layout.extra_move, ExtraTargets):
        extra_targets = name_layout.extra_move.fields
    else:
        extra_targets = ()

    return [
        field.name for field in figure.fields
        if field.name not in used_direct_fields and field.name not in extra_targets
    ]


def _inner_get_extra_targets_at_crown(extra_targets: Container[str], crown: BaseCrown) -> Collection[str]:
    if isinstance(crown, BaseDictCrown):
        return _concatenate_iters(
            _inner_get_extra_targets_at_crown(extra_targets, sub_crown)
            for sub_crown in crown.map.values()
        )
    if isinstance(crown, BaseListCrown):
        return _concatenate_iters(
            _inner_get_extra_targets_at_crown(extra_targets, sub_crown)
            for sub_crown in crown.map
        )
    if isinstance(crown, BaseFieldCrown):
        return [crown.name] if crown.name in extra_targets else []
    if isinstance(crown, BaseNoneCrown):
        return []
    raise TypeError


def get_extra_targets_at_crown(name_layout: BaseNameLayout) -> Collection[str]:
    if not isinstance(name_layout.extra_move, ExtraTargets):
        return []

    return _inner_get_extra_targets_at_crown(name_layout.extra_move.fields, name_layout.crown)


def get_optional_fields_at_list_crown(
    fields_map: Mapping[str, Union[InputField, OutputField]],
    crown: BaseCrown,
) -> Collection[str]:
    if isinstance(crown, BaseDictCrown):
        return _concatenate_iters(
            get_optional_fields_at_list_crown(fields_map, sub_crown)
            for sub_crown in crown.map.values()
        )
    if isinstance(crown, BaseListCrown):
        return _concatenate_iters(
            (
                [sub_crown.name]
                if fields_map[sub_crown.name].is_optional else
                []
            )
            if isinstance(sub_crown, BaseFieldCrown) else
            get_optional_fields_at_list_crown(fields_map, sub_crown)
            for sub_crown in crown.map
        )
    if isinstance(crown, (BaseFieldCrown, BaseNoneCrown)):
        return []
    raise TypeError


def get_wild_extra_targets(figure: BaseFigure, extra_move: Union[InpExtraMove, OutExtraMove]) -> Collection[str]:
    if not isinstance(extra_move, ExtraTargets):
        return []

    return [
        target for target in extra_move.fields
        if target not in figure.fields_dict.keys()
    ]


Fig = TypeVar('Fig', bound=BaseFigure)


def strip_figure_fields(figure: Fig, skipped_fields: Collection[str]) -> Fig:
    return replace(
        figure,
        fields=tuple(
            field for field in figure.fields
            if field.name not in skipped_fields
        ),
    )


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
        value_literal = get_literal_expr(value)
        if value_literal is None:
            global_name = f"g_{name}"
            global_namespace_dict[global_name] = value
            builder += f"{name} = {global_name}"
        else:
            builder += f"{name} = {value_literal}"

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


def has_collect_policy(crown: InpCrown) -> bool:
    if isinstance(crown, InpDictCrown):
        return crown.extra_policy == ExtraCollect() or any(
            has_collect_policy(sub_crown)
            for sub_crown in crown.map.values()
        )
    if isinstance(crown, InpListCrown):
        return any(
            has_collect_policy(sub_crown)
            for sub_crown in crown.map
        )
    if isinstance(crown, (InpFieldCrown, InpNoneCrown)):
        return False
    raise TypeError
