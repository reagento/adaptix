from dataclasses import dataclass, replace
from typing import Tuple, TypeVar

from ..common import TypeHint
from ..datastructures import ImmutableStack
from ..definitions import DebugTrail
from ..type_tools import BaseNormType, is_parametrized, normalize_type
from ..utils import pairs
from .essential import CannotProvide, Request
from .location import AnyLoc, FieldLoc, InputFuncFieldLoc, TypeHintLoc

LocStackT = TypeVar("LocStackT", bound="LocStack")
AnyLocT_co = TypeVar("AnyLocT_co", bound=AnyLoc, covariant=True)


class LocStack(ImmutableStack[AnyLocT_co]):
    def replace_last_type(self: LocStackT, tp: TypeHint, /) -> LocStackT:
        return self.replace_last(replace(self.last, type=tp))


def _format_type(tp: TypeHint) -> str:
    if isinstance(tp, type) and not is_parametrized(tp):
        return tp.__qualname__
    str_tp = str(tp)
    if str_tp.startswith("typing."):
        return str_tp[7:]
    return str_tp


def format_loc_stack(loc_stack: LocStack[AnyLoc]) -> str:
    fmt_tp = _format_type(loc_stack.last.type)

    try:
        field_loc = loc_stack.last.cast(FieldLoc)
    except TypeError:
        return fmt_tp
    else:
        fmt_field = f"{field_loc.field_id}: {fmt_tp}"

    if loc_stack.last.is_castable(InputFuncFieldLoc):
        func_field_loc = loc_stack.last.cast(InputFuncFieldLoc)
        func_name = getattr(func_field_loc.func, "__qualname__", None) or repr(func_field_loc.func)
        return f"{func_name}({fmt_field})"

    if len(loc_stack) >= 2:  # noqa: PLR2004
        src_owner = _format_type(loc_stack[-2].type)
        return f"{src_owner}.{fmt_field}"
    return fmt_tp


T = TypeVar("T")


@dataclass(frozen=True)
class LocatedRequest(Request[T]):
    loc_stack: LocStack

    @property
    def last_loc(self) -> AnyLoc:
        return self.loc_stack.last


def get_type_from_request(request: LocatedRequest) -> TypeHint:
    return request.last_loc.cast_or_raise(TypeHintLoc, CannotProvide).type


def try_normalize_type(tp: TypeHint) -> BaseNormType:
    try:
        return normalize_type(tp)
    except ValueError:
        raise CannotProvide(f"{tp} can not be normalized")


class StrictCoercionRequest(LocatedRequest[bool]):
    pass


class DebugTrailRequest(LocatedRequest[DebugTrail]):
    pass


def find_owner_with_field(stack: LocStack) -> Tuple[TypeHintLoc, FieldLoc]:
    for next_loc, prev_loc in pairs(reversed(stack)):
        if next_loc.is_castable(FieldLoc):
            return prev_loc, next_loc
    raise ValueError
