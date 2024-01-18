import re
from abc import ABC, abstractmethod
from copy import copy
from dataclasses import dataclass, replace
from inspect import isabstract, isgenerator
from typing import Any, Callable, ClassVar, Iterable, Optional, Pattern, Protocol, Sequence, Tuple, Type, TypeVar, Union

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
from .essential import AggregateCannotProvide, CannotProvide, Mediator, Provider, Request
from .request_cls import FieldLoc, GenericParamLoc, LocatedRequest, Location, TypeHintLoc, try_normalize_type

T = TypeVar('T')


class DirectMediator(Protocol):
    """This is copy of Mediator protocol but without provide_from_next() method"""

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


class RequestChecker(ABC):
    @abstractmethod
    def check_request(self, mediator: DirectMediator, request: Request) -> None:
        """Raise CannotProvide if the request does not meet the conditions"""

    def __or__(self, other: Any) -> 'RequestChecker':
        if isinstance(other, RequestChecker):
            return OrRequestChecker([self, other])
        return NotImplemented

    def __and__(self, other: Any) -> 'RequestChecker':
        if isinstance(other, RequestChecker):
            return AndRequestChecker([self, other])
        return NotImplemented

    def __xor__(self, other: Any) -> 'RequestChecker':
        if isinstance(other, RequestChecker):
            return XorRequestChecker(self, other)
        return NotImplemented

    def __invert__(self) -> 'RequestChecker':
        return NegRequestChecker(self)


class ProviderWithRC(Provider, ABC):
    @abstractmethod
    def get_request_checker(self) -> Optional[RequestChecker]:
        ...


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

        raise AggregateCannotProvide.make('', exceptions=sub_errors)


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
            raise AggregateCannotProvide.make('', exceptions=exceptions)


class LocatedRequestChecker(RequestChecker, ABC):
    LOCATION: ClassVar[Type[Location]]

    def check_request(self, mediator: DirectMediator, request: Request) -> None:
        if not isinstance(request, LocatedRequest):
            raise CannotProvide(f'Request must be instance of {LocatedRequest}')
        if self.LOCATION not in request.last_map:
            raise CannotProvide(f'Request location must be instance of {self.LOCATION}')
        self._check_location(mediator, request.last_map[self.LOCATION])

    @abstractmethod
    def _check_location(self, mediator: DirectMediator, loc: Any) -> None:
        ...


@dataclass(frozen=True)
class ExactFieldNameRC(LocatedRequestChecker):
    LOCATION = FieldLoc
    field_id: str

    def _check_location(self, mediator: DirectMediator, loc: FieldLoc) -> None:
        if self.field_id == loc.field_id:
            return
        raise CannotProvide(f'field_id must be a {self.field_id!r}')


@dataclass(frozen=True)
class ReFieldNameRC(LocatedRequestChecker):
    LOCATION = FieldLoc
    pattern: Pattern[str]

    def _check_location(self, mediator: DirectMediator, loc: FieldLoc) -> None:
        if self.pattern.fullmatch(loc.field_id):
            return

        raise CannotProvide(f'field_id must be matched by {self.pattern!r}')


@dataclass(frozen=True)
class ExactTypeRC(LocatedRequestChecker):
    LOCATION = TypeHintLoc
    norm: BaseNormType

    def _check_location(self, mediator: DirectMediator, loc: TypeHintLoc) -> None:
        if try_normalize_type(loc.type) == self.norm:
            return
        raise CannotProvide(f'{loc.type} must be a equal to {self.norm.source}')


@dataclass(frozen=True)
class OriginSubclassRC(LocatedRequestChecker):
    LOCATION = TypeHintLoc
    type_: type

    def _check_location(self, mediator: DirectMediator, loc: TypeHintLoc) -> None:
        norm = try_normalize_type(loc.type)
        if is_subclass_soft(norm.origin, self.type_):
            return
        raise CannotProvide(f'{loc.type} must be a subclass of {self.type_}')


@dataclass(frozen=True)
class ExactOriginRC(LocatedRequestChecker):
    LOCATION = TypeHintLoc
    origin: Any

    def _check_location(self, mediator: DirectMediator, loc: TypeHintLoc) -> None:
        if try_normalize_type(loc.type).origin == self.origin:
            return
        raise CannotProvide(f'{loc.type} must have origin {self.origin}')


class ExactOriginMergedProvider(Provider):
    def __init__(self, origins_to_providers: Sequence[Tuple[ExactOriginRC, Provider]]):
        self.origin_to_provider = {
            request_checker.origin: provider
            for request_checker, provider in reversed(origins_to_providers)
        }

    def apply_provider(self, mediator: Mediator[T], request: Request[T]) -> T:
        if not isinstance(request, LocatedRequest):
            raise CannotProvide(f'Request must be instance of {LocatedRequest}')

        loc = request.last_map.get_or_raise(
            TypeHintLoc,
            lambda: CannotProvide(f'Request location must be instance of {TypeHintLoc}')
        )
        norm = try_normalize_type(loc.type)
        try:
            provider = self.origin_to_provider[norm.origin]
        except KeyError:
            raise CannotProvide from None

        return provider.apply_provider(mediator, request)


@dataclass(frozen=True)
class LocStackEndRC(RequestChecker):
    request_checkers: Sequence[RequestChecker]

    def check_request(self, mediator: DirectMediator, request: Request[T]) -> None:
        if not isinstance(request, LocatedRequest):
            raise CannotProvide(f'Request must be instance of {LocatedRequest}')

        if len(request.loc_stack) < len(self.request_checkers):
            raise CannotProvide("LocStack is too small")

        for i, checker in enumerate(reversed(self.request_checkers), start=0):
            checker.check_request(
                mediator,
                replace(request, loc_stack=request.loc_stack[:len(request.loc_stack) - i]),
            )


@dataclass(frozen=True)
class GenericParamRC(LocatedRequestChecker):
    LOCATION = GenericParamLoc
    pos: int

    def _check_location(self, mediator: DirectMediator, loc: GenericParamLoc) -> None:
        if loc.generic_pos == self.pos:
            return
        raise CannotProvide(f'Generic param position {loc.generic_pos} must be equal to {self.pos}')


class AnyRequestChecker(RequestChecker):
    def check_request(self, mediator: DirectMediator, request: Request) -> None:
        return


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


def _create_request_checker_by_origin(origin):
    if is_protocol(origin) or isabstract(origin):
        return OriginSubclassRC(origin)
    return ExactOriginRC(origin)


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

    if is_bare_generic(pred):
        return _create_request_checker_by_origin(norm.origin)

    if is_generic(pred):
        raise ValueError(
            f'Can not create RequestChecker from {pred} generic alias (parametrized generic)'
        )

    if not is_generic(norm.origin) and not is_parametrized(pred):
        return _create_request_checker_by_origin(norm.origin)   # this is only an optimization
    return ExactTypeRC(norm)


Pat = TypeVar('Pat', bound='RequestPattern')


class RequestPattern:
    ANY = AnyRequestChecker()

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
        if isinstance(item, tuple) or isgenerator(item):
            return self._extend_stack(
                [OrRequestChecker([self._ensure_request_checker_from_pred(el) for el in item])]
            )
        return self._extend_stack([self._ensure_request_checker_from_pred(item)])

    def _ensure_request_checker(self: Pat, other: Union[Pat, RequestChecker]) -> RequestChecker:
        if isinstance(other, RequestChecker):
            return other
        return other.build_request_checker()

    def __or__(self: Pat, other: Union[Pat, RequestChecker]) -> Pat:
        return self._from_rc(
            self.build_request_checker() | self._ensure_request_checker(other)
        )

    def __ror__(self: Pat, other: Union[Pat, RequestChecker]) -> Pat:
        return self._from_rc(
            self._ensure_request_checker(other) | self.build_request_checker()
        )

    def __and__(self: Pat, other: Union[Pat, RequestChecker]) -> Pat:
        return self._from_rc(
            self.build_request_checker() & self._ensure_request_checker(other)
        )

    def __rand__(self: Pat, other: Union[Pat, RequestChecker]) -> Pat:
        return self._from_rc(
            self._ensure_request_checker(other) & self.build_request_checker()
        )

    def __xor__(self: Pat, other: Union[Pat, RequestChecker]) -> Pat:
        return self._from_rc(
            self.build_request_checker() ^ self._ensure_request_checker(other)
        )

    def __rxor__(self: Pat, other: Union[Pat, RequestChecker]) -> Pat:
        return self._from_rc(
            self._ensure_request_checker(other) ^ self.build_request_checker()
        )

    def __invert__(self: Pat) -> Pat:
        return self._from_rc(
            ~self.build_request_checker()
        )

    def __add__(self: Pat, other: Pat) -> Pat:
        return self._extend_stack(other._stack)

    def _ensure_request_checker_from_pred(self, pred: Any) -> RequestChecker:
        if isinstance(pred, RequestPattern):
            raise TypeError(
                "Can not use RequestPattern as predicate inside RequestPattern."
                " If you want to combine several RequestPattern, you can use `+` operator"
            )

        return create_request_checker(pred)

    def generic_arg(self: Pat, pos: int, pred: Pred) -> Pat:
        return self._extend_stack(
            [GenericParamRC(pos) & self._ensure_request_checker_from_pred(pred)]
        )

    def build_request_checker(self) -> RequestChecker:
        if len(self._stack) == 0:
            raise ValueError(
                'Can not produce RequestChecker from RequestPattern without stack.'
                ' You need to parametrize P object with predicates.'
            )
        if len(self._stack) == 1:
            return self._stack[0]
        return LocStackEndRC(self._stack)


P = RequestPattern(stack=())
