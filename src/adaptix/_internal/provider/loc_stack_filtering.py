import inspect
import operator
import re
from abc import ABC, abstractmethod
from copy import copy
from dataclasses import dataclass
from functools import reduce
from inspect import isabstract, isgenerator
from typing import Any, Callable, ClassVar, Iterable, Optional, Pattern, Protocol, Sequence, Type, TypeVar, Union, final

from ..common import TypeHint, VarTuple
from ..type_tools import (
    BaseNormType,
    NormTV,
    is_bare_generic,
    is_generic,
    is_parametrized,
    is_protocol,
    is_subclass_soft,
    normalize_type,
)
from ..type_tools.normalize_type import NotSubscribedError
from .essential import CannotProvide, Request
from .request_cls import FieldLoc, GenericParamLoc, Location, LocStack, TypeHintLoc

T = TypeVar('T')


class DirectMediator(Protocol):
    """This is a copy of Mediator protocol but without provide_from_next() method"""

    def provide(self, request: Request[T]) -> T:
        ...

    def delegating_provide(
        self,
        request: Request[T],
        error_describer: Optional[Callable[[CannotProvide], str]] = None,
    ) -> T:
        ...

    def mandatory_provide(
        self,
        request: Request[T],
        error_describer: Optional[Callable[[CannotProvide], str]] = None,
    ) -> T:
        ...

    def mandatory_provide_by_iterable(
        self,
        requests: Iterable[Request[T]],
        error_describer: Optional[Callable[[], str]] = None,
    ) -> Iterable[T]:
        ...


class LocStackChecker(ABC):
    @abstractmethod
    def check_loc_stack(self, mediator: DirectMediator, loc_stack: LocStack) -> bool:
        ...

    @final
    def __or__(self, other: Any) -> 'LocStackChecker':
        if isinstance(other, LocStackChecker):
            return OrLocStackChecker([self, other])
        return NotImplemented

    @final
    def __and__(self, other: Any) -> 'LocStackChecker':
        if isinstance(other, LocStackChecker):
            return AndLocStackChecker([self, other])
        return NotImplemented

    @final
    def __xor__(self, other: Any) -> 'LocStackChecker':
        if isinstance(other, LocStackChecker):
            return XorLocStackChecker([self, other])
        return NotImplemented

    @final
    def __invert__(self) -> 'LocStackChecker':
        return InvertLSC(self)


class InvertLSC(LocStackChecker):
    def __init__(self, lsc: LocStackChecker):
        self._lsc = lsc

    def check_loc_stack(self, mediator: DirectMediator, loc_stack: LocStack) -> bool:
        return not self._lsc.check_loc_stack(mediator, loc_stack)


class BinOperatorLSC(LocStackChecker, ABC):
    def __init__(self, loc_stack_checkers: Iterable[LocStackChecker]):
        self._loc_stack_checkers = loc_stack_checkers

    @abstractmethod
    def _reduce(self, elements: Iterable[bool], /) -> bool:
        ...

    def check_loc_stack(self, mediator: DirectMediator, loc_stack: LocStack) -> bool:
        return self._reduce(
            loc_stack_checker.check_loc_stack(mediator, loc_stack)
            for loc_stack_checker in self._loc_stack_checkers
        )


class OrLocStackChecker(BinOperatorLSC):
    _reduce = any  # type: ignore[assignment]


class AndLocStackChecker(BinOperatorLSC):
    _reduce = all  # type: ignore[assignment]


class XorLocStackChecker(BinOperatorLSC):
    def _reduce(self, elements: Iterable[bool], /) -> bool:
        return reduce(operator.xor, elements)


class LastLocMapChecker(LocStackChecker, ABC):
    _expected_location: ClassVar[Type[Location]]

    def __init_subclass__(cls, **kwargs):
        param_list = list(inspect.signature(cls._check_location).parameters.values())
        cls._expected_location = param_list[2].annotation

    @final
    def check_loc_stack(self, mediator: DirectMediator, loc_stack: LocStack) -> bool:
        loc_map = loc_stack[-1]
        if loc_map.has(self._expected_location):
            return self._check_location(mediator, loc_map[self._expected_location])
        return False

    @abstractmethod
    def _check_location(self, mediator: DirectMediator, loc: Any) -> bool:
        pass


@dataclass(frozen=True)
class ExactFieldNameLSC(LastLocMapChecker):
    field_id: str

    def _check_location(self, mediator: DirectMediator, loc: FieldLoc) -> bool:
        return self.field_id == loc.field_id


@dataclass(frozen=True)
class ReFieldNameLSC(LastLocMapChecker):
    pattern: Pattern[str]

    def _check_location(self, mediator: DirectMediator, loc: FieldLoc) -> bool:
        return self.pattern.fullmatch(loc.field_id) is not None


@dataclass(frozen=True)
class ExactTypeLSC(LastLocMapChecker):
    norm: BaseNormType

    def _check_location(self, mediator: DirectMediator, loc: TypeHintLoc) -> bool:
        try:
            norm = normalize_type(loc.type)
        except ValueError:
            return False
        return norm == self.norm


@dataclass(frozen=True)
class OriginSubclassLSC(LastLocMapChecker):
    type_: type

    def _check_location(self, mediator: DirectMediator, loc: TypeHintLoc) -> bool:
        try:
            norm = normalize_type(loc.type)
        except ValueError:
            return False
        return is_subclass_soft(norm.origin, self.type_)


@dataclass(frozen=True)
class ExactOriginLSC(LastLocMapChecker):
    origin: Any

    def _check_location(self, mediator: DirectMediator, loc: TypeHintLoc) -> bool:
        try:
            norm = normalize_type(loc.type)
        except ValueError:
            return False
        return norm.origin == self.origin


@dataclass(frozen=True)
class GenericParamLSC(LastLocMapChecker):
    pos: int

    def _check_location(self, mediator: DirectMediator, loc: GenericParamLoc) -> bool:
        return loc.generic_pos == self.pos


@dataclass(frozen=True)
class LocStackEndChecker(LocStackChecker):
    loc_stack_checkers: Sequence[LocStackChecker]

    def check_loc_stack(self, mediator: DirectMediator, loc_stack: LocStack) -> bool:
        if len(loc_stack) < len(self.loc_stack_checkers):
            return False

        for i, checker in enumerate(reversed(self.loc_stack_checkers), start=0):
            if not checker.check_loc_stack(mediator, loc_stack[:len(loc_stack) - i]):
                return False
        return True


class AnyLocStackChecker(LocStackChecker):
    def check_loc_stack(self, mediator: DirectMediator, loc_stack: LocStack) -> bool:
        return True


Pred = Union[str, re.Pattern, type, TypeHint, LocStackChecker, 'LocStackPattern']


def _create_non_type_hint_loc_stack_checker(pred: Pred) -> Optional[LocStackChecker]:
    if isinstance(pred, str):
        if pred.isidentifier():
            return ExactFieldNameLSC(pred)  # this is only an optimization
        return ReFieldNameLSC(re.compile(pred))

    if isinstance(pred, re.Pattern):
        return ReFieldNameLSC(pred)

    if isinstance(pred, LocStackChecker):
        return pred

    if isinstance(pred, LocStackPattern):
        return pred.build_loc_stack_checker()

    return None


def _create_loc_stack_checker_by_origin(origin):
    if is_protocol(origin) or isabstract(origin):
        return OriginSubclassLSC(origin)
    return ExactOriginLSC(origin)


def create_loc_stack_checker(pred: Pred) -> LocStackChecker:
    result = _create_non_type_hint_loc_stack_checker(pred)
    if result is not None:
        return result

    try:
        norm = normalize_type(pred)
    except NotSubscribedError:
        return ExactOriginLSC(pred)
    except ValueError:
        raise ValueError(f'Can not create LocStackChecker from {pred}')

    if isinstance(norm, NormTV):
        raise ValueError(f'Can not create LocStackChecker from {pred} type var')

    if is_bare_generic(pred):
        return _create_loc_stack_checker_by_origin(norm.origin)

    if is_generic(pred):
        raise ValueError(
            f'Can not create LocStackChecker from {pred} generic alias (parametrized generic)'
        )

    if not is_generic(norm.origin) and not is_parametrized(pred):
        return _create_loc_stack_checker_by_origin(norm.origin)   # this is only an optimization
    return ExactTypeLSC(norm)


Pat = TypeVar('Pat', bound='LocStackPattern')


class LocStackPattern:
    ANY = AnyLocStackChecker()

    def __init__(self, stack: VarTuple[LocStackChecker]):
        self._stack = stack

    @classmethod
    def _from_lsc(cls: Type[Pat], lsc: LocStackChecker) -> Pat:
        return cls((lsc, ))

    def _extend_stack(self: Pat, elements: Iterable[LocStackChecker]) -> Pat:
        self_copy = copy(self)
        self_copy._stack = self._stack + tuple(elements)  # pylint: disable=protected-access
        return self_copy

    def __getattr__(self: Pat, item: str) -> Pat:
        if item.startswith('__') and item.endswith('__'):
            raise AttributeError
        return self[item]

    def __getitem__(self: Pat, item: Union[Pred, VarTuple[Pred]]) -> Pat:
        if isinstance(item, tuple) or isgenerator(item):
            return self._extend_stack(
                [OrLocStackChecker([self._ensure_loc_stack_checker_from_pred(el) for el in item])]
            )
        return self._extend_stack([self._ensure_loc_stack_checker_from_pred(item)])

    def _ensure_loc_stack_checker(self: Pat, other: Union[Pat, LocStackChecker]) -> LocStackChecker:
        if isinstance(other, LocStackChecker):
            return other
        return other.build_loc_stack_checker()

    def __or__(self: Pat, other: Union[Pat, LocStackChecker]) -> Pat:
        return self._from_lsc(
            self.build_loc_stack_checker() | self._ensure_loc_stack_checker(other)
        )

    def __ror__(self: Pat, other: Union[Pat, LocStackChecker]) -> Pat:
        return self._from_lsc(
            self._ensure_loc_stack_checker(other) | self.build_loc_stack_checker()
        )

    def __and__(self: Pat, other: Union[Pat, LocStackChecker]) -> Pat:
        return self._from_lsc(
            self.build_loc_stack_checker() & self._ensure_loc_stack_checker(other)
        )

    def __rand__(self: Pat, other: Union[Pat, LocStackChecker]) -> Pat:
        return self._from_lsc(
            self._ensure_loc_stack_checker(other) & self.build_loc_stack_checker()
        )

    def __xor__(self: Pat, other: Union[Pat, LocStackChecker]) -> Pat:
        return self._from_lsc(
            self.build_loc_stack_checker() ^ self._ensure_loc_stack_checker(other)
        )

    def __rxor__(self: Pat, other: Union[Pat, LocStackChecker]) -> Pat:
        return self._from_lsc(
            self._ensure_loc_stack_checker(other) ^ self.build_loc_stack_checker()
        )

    def __invert__(self: Pat) -> Pat:
        return self._from_lsc(
            ~self.build_loc_stack_checker()
        )

    def __add__(self: Pat, other: Pat) -> Pat:
        return self._extend_stack(other._stack)

    def _ensure_loc_stack_checker_from_pred(self, pred: Any) -> LocStackChecker:
        if isinstance(pred, LocStackPattern):
            raise TypeError(
                "Can not use LocStackPattern as predicate inside LocStackPattern."
                " If you want to combine several LocStackPattern, you can use `+` operator"
            )

        return create_loc_stack_checker(pred)

    def generic_arg(self: Pat, pos: int, pred: Pred) -> Pat:
        return self._extend_stack(
            [GenericParamLSC(pos) & self._ensure_loc_stack_checker_from_pred(pred)]
        )

    def build_loc_stack_checker(self) -> LocStackChecker:
        if len(self._stack) == 0:
            raise ValueError(
                'Can not produce LocStackChecker from LocStackPattern without stack.'
                ' You need to parametrize P object with predicates.'
            )
        if len(self._stack) == 1:
            return self._stack[0]
        return LocStackEndChecker(self._stack)


P = LocStackPattern(stack=())
