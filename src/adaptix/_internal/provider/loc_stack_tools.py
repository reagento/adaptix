
from ..common import TypeHint
from ..type_tools import is_parametrized
from ..utils import pairs
from .loc_stack_filtering import LocStack
from .location import AnyLoc, FieldLoc, InputFuncFieldLoc, TypeHintLoc


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


def find_owner_with_field(stack: LocStack) -> tuple[TypeHintLoc, FieldLoc]:
    for next_loc, prev_loc in pairs(reversed(stack)):
        if next_loc.is_castable(FieldLoc):
            return prev_loc, next_loc
    raise ValueError
