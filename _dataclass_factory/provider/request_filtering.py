import re
from abc import ABC, abstractmethod
from copy import copy
from dataclasses import dataclass
from inspect import isabstract
from typing import Any, ClassVar, Iterable, Optional, Pattern, Protocol, Sequence, Type, TypeVar, Union

from ..common import TypeHint, VarTuple
from ..type_tools import BaseNormType, NormTV, is_parametrized, is_protocol, is_subclass_soft, normalize_type
from ..type_tools.normalize_type import NotSubscribedError
from .essential import CannotProvide, Request
from .request_cls import FieldLocation, LocatedRequest, Location, TypeHintLocation

T = TypeVar('T')


class DirectMediator(Protocol):
    """This is copy of Mediator protocol but without provide_from_next() method"""

    def provide(self, request: Request[T]) -> T:
        ...

    @property
    def request_stack(self) -> Sequence[Request[Any]]:
        ...


class RequestChecker(ABC):
    @abstractmethod
    def check_request(self, mediator: DirectMediator, request: Request) -> None:
        """Raise CannotProvide if the request does not meet the conditions"""

    def __or__(self, other: 'RequestChecker') -> 'RequestChecker':
        return OrRequestChecker([self, other])

    def __and__(self, other: 'RequestChecker') -> 'RequestChecker':
        return AndRequestChecker([self, other])

    def __xor__(self, other: 'RequestChecker') -> 'RequestChecker':
        return XorRequestChecker(self, other)

    def __invert__(self) -> 'RequestChecker':
        return NegRequestChecker(self)


class OrRequestChecker(RequestChecker):
    def __init__(self, request_checkers: Iterable[RequestChecker]):
        self._request_checkers = request_checkers

    def check_request(self, mediator: DirectMediator, request: Request) -> None:
        sub_errors = []

        for checker in self._request_checkers:
            try:
                checker.check_request(mediator, request)
            except CannotProvide as e:
                sub_errors.append(e)
            else:
                return

        raise CannotProvide(sub_errors=sub_errors)


class AndRequestChecker(RequestChecker):
    def __init__(self, request_checkers: Iterable[RequestChecker]):
        self._request_checkers = request_checkers

    def check_request(self, mediator: DirectMediator, request: Request) -> None:
        for checker in self._request_checkers:
            checker.check_request(mediator, request)


class NegRequestChecker(RequestChecker):
    def __init__(self, rc: RequestChecker):
        self._rc = rc

    def check_request(self, mediator: DirectMediator, request: Request) -> None:
        try:
            self._rc.check_request(mediator, request)
        except CannotProvide:
            return
        else:
            raise CannotProvide


class XorRequestChecker(RequestChecker):
    def __init__(self, left: RequestChecker, right: RequestChecker):
        self._left = left
        self._right = right

    def check_request(self, mediator: DirectMediator, request: Request) -> None:
        exceptions = []

        try:
            self._left.check_request(mediator, request)
        except CannotProvide as exc:
            exceptions.append(exc)

        try:
            self._right.check_request(mediator, request)
        except CannotProvide as exc:
            exceptions.append(exc)

        if len(exceptions) == 0:
            raise CannotProvide

        if len(exceptions) == 2:
            raise CannotProvide(sub_errors=exceptions)


class LocatedRequestChecker(RequestChecker, ABC):
    LOCATION: ClassVar[Type[Location]]

    def check_request(self, mediator: DirectMediator, request: Request) -> None:
        if not isinstance(request, LocatedRequest):
            raise CannotProvide(f'Request must be instance of {LocatedRequest}')
        if not isinstance(request.loc, self.LOCATION):
            raise CannotProvide(f'Request location must be instance of {self.LOCATION}')
        self._check_location(mediator, request.loc)

    @abstractmethod
    def _check_location(self, mediator: DirectMediator, loc: Any) -> None:
        ...


@dataclass
class ExactFieldNameRC(LocatedRequestChecker):
    LOCATION = FieldLocation
    field_name: str

    def _check_location(self, mediator: DirectMediator, loc: FieldLocation) -> None:
        if self.field_name == loc.name:
            return
        raise CannotProvide(f'field_name must be a {self.field_name!r}')


@dataclass
class ReFieldNameRC(LocatedRequestChecker):
    LOCATION = FieldLocation
    pattern: Pattern[str]

    def _check_location(self, mediator: DirectMediator, loc: FieldLocation) -> None:
        if self.pattern.fullmatch(loc.name):
            return

        raise CannotProvide(f'field_name must be matched by {self.pattern!r}')


@dataclass
class ExactTypeRC(LocatedRequestChecker):
    LOCATION = TypeHintLocation
    norm: BaseNormType

    def _check_location(self, mediator: DirectMediator, loc: TypeHintLocation) -> None:
        if normalize_type(loc.type) == self.norm:
            return
        raise CannotProvide(f'{loc.type} must be a equal to {self.norm.source}')


@dataclass
class OriginSubclassRC(LocatedRequestChecker):
    LOCATION = TypeHintLocation
    type_: type

    def _check_location(self, mediator: DirectMediator, loc: TypeHintLocation) -> None:
        norm = normalize_type(loc.type)
        if is_subclass_soft(norm.origin, self.type_):
            return
        raise CannotProvide(f'{loc.type} must be a subclass of {self.type_}')


@dataclass
class ExactOriginRC(LocatedRequestChecker):
    LOCATION = TypeHintLocation
    origin: Any

    def _check_location(self, mediator: DirectMediator, loc: TypeHintLocation) -> None:
        if normalize_type(loc.type).origin == self.origin:
            return
        raise CannotProvide(f'{loc.type} must have origin {self.origin}')


class RequestStackCutter(DirectMediator):
    def __init__(self, mediator: DirectMediator, end_offset: int):
        self._mediator = mediator
        self._end_offset = end_offset

    def provide(self, request: Request[T]) -> T:
        return self._mediator.provide(request)

    @property
    def request_stack(self) -> Sequence[Request[Any]]:
        return self._mediator.request_stack[:-self._end_offset or None]


@dataclass
class StackEndRC(RequestChecker):
    request_checkers: Sequence[RequestChecker]

    def check_request(self, mediator: DirectMediator, request: Request[T]) -> None:
        stack = mediator.request_stack
        offset = len(stack) - len(self.request_checkers)

        if offset < 0:
            raise CannotProvide("Request stack is too small")

        for i, (checker, stack_request) in enumerate(zip(self.request_checkers, stack[offset:]), start=0):
            checker.check_request(
                RequestStackCutter(mediator, i),
                stack_request,
            )


class AnyRequestChecker(RequestChecker):
    def check_request(self, mediator: DirectMediator, request: Request) -> None:
        return


def _create_origin_request_checker(norm: BaseNormType) -> RequestChecker:
    if is_protocol(norm.origin) or isabstract(norm.origin):
        return OriginSubclassRC(norm.origin)

    return ExactOriginRC(norm.origin)


def match_origin(tp: TypeHint) -> RequestChecker:
    if is_parametrized(tp):
        raise ValueError("TypeHint must be not parametrized")

    try:
        norm = normalize_type(tp)
    except NotSubscribedError:
        return ExactOriginRC(tp)
    except ValueError:
        raise ValueError(f'Can not create RequestChecker from {tp}')

    return _create_origin_request_checker(norm)


Pred = Union[str, re.Pattern, type, TypeHint, RequestChecker, 'RequestPattern']


def _create_non_type_hint_request_checker(pred: Pred) -> Optional[RequestChecker]:
    if isinstance(pred, str):
        if pred.isidentifier():
            return ExactFieldNameRC(pred)  # this is only an optimization
        return ReFieldNameRC(re.compile(pred))

    if isinstance(pred, re.Pattern):
        return ReFieldNameRC(pred)

    if isinstance(pred, RequestChecker):
        return pred

    if isinstance(pred, RequestPattern):
        return pred.build_request_checker()

    return None


def create_request_checker(pred: Pred) -> RequestChecker:
    result = _create_non_type_hint_request_checker(pred)
    if result is not None:
        return result

    try:
        norm = normalize_type(pred)
    except NotSubscribedError:
        return ExactOriginRC(pred)
    except ValueError:
        raise ValueError(f'Can not create RequestChecker from {pred}')

    if isinstance(norm, NormTV):
        raise ValueError(f'Can not create RequestChecker from {pred} type var')

    if not is_parametrized(pred):
        if norm.args:
            raise ValueError(
                f'Can not create RequestChecker from non-parametrized generic {pred}.'
                f' You should parametrize it or wrap with match_origin()'
            )
        return _create_origin_request_checker(norm)

    return ExactTypeRC(norm)


Pat = TypeVar('Pat', bound='RequestPattern')


class RequestPattern:
    def __init__(self, stack: VarTuple[RequestChecker]):
        self._stack = stack

    @classmethod
    def _from_rc(cls: Type[Pat], rc: RequestChecker) -> Pat:
        return cls((rc, ))

    def _extend_stack(self: Pat, elements: Iterable[RequestChecker]) -> Pat:
        self_copy = copy(self)
        self_copy._stack = self._stack + tuple(elements)  # pylint: disable=protected-access
        return self_copy

    def __getattr__(self: Pat, item: str) -> Pat:
        if item.startswith('__') and item.endswith('__'):
            raise AttributeError
        return self[item]

    def __getitem__(self: Pat, item: Union[Pred, VarTuple[Pred]]) -> Pat:
        if isinstance(item, tuple):
            return self._extend_stack(
                [OrRequestChecker(self._ensure_request_checker(el) for el in item)]
            )
        return self._extend_stack([self._ensure_request_checker(item)])

    def __or__(self: Pat, other: Pat) -> Pat:
        return self._from_rc(
            self.build_request_checker() | other.build_request_checker()
        )

    def __and__(self: Pat, other: Pat) -> Pat:
        return self._from_rc(
            self.build_request_checker() & other.build_request_checker()
        )

    def __xor__(self: Pat, other: Pat) -> Pat:
        return self._from_rc(
            self.build_request_checker() ^ other.build_request_checker()
        )

    def __invert__(self: Pat) -> Pat:
        return self._from_rc(
            ~self.build_request_checker()
        )

    def __add__(self: Pat, other: Pat) -> Pat:
        return self._extend_stack(other._stack)

    def _ensure_request_checker(self, pred: Any) -> RequestChecker:
        if isinstance(pred, RequestPattern):
            raise TypeError(
                "Can not use RequestPattern as predicate inside RequestPattern."
                " If you want to combine several RequestPattern, you can use `+` operator"
            )

        return create_request_checker(pred)

    def build_request_checker(self) -> RequestChecker:
        if len(self._stack) == 1:
            return self._stack[0]
        return StackEndRC(self._stack)


P = RequestPattern(stack=())
