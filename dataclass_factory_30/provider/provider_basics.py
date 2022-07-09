from abc import ABC, abstractmethod
from dataclasses import dataclass
from inspect import isabstract
from typing import TypeVar, Union, Type, Callable, Any, Generic

from .definitions import ParseError, PARSER_COMPAT_EXCEPTIONS, SerializeError
from .essential import Provider, Mediator, CannotProvide, Request
from .request_cls import TypeHintRM, FieldRM
from ..common import TypeHint, Parser, Serializer, VarTuple
from ..type_tools import is_protocol, normalize_type, is_subclass_soft
from ..type_tools.normalize_type import NormTV, NotSubscribedError, BaseNormType

T = TypeVar('T')


class RequestChecker(ABC):
    @abstractmethod
    def get_allowed_request_classes(self) -> VarTuple[Type[Request]]:
        raise NotImplementedError

    @abstractmethod
    def _check_request(self, request) -> None:
        """Raise CannotProvide if the request does not meet the conditions"""
        raise NotImplementedError

    def __call__(self, request: Request) -> None:
        """Raise CannotProvide if the request does not meet the conditions"""
        allowed = self.get_allowed_request_classes()
        if isinstance(request, allowed):
            self._check_request(request)
        else:
            raise CannotProvide(f'Only instances of {allowed} are allowed')

    def __or__(self, other: 'RequestChecker') -> 'RequestChecker':
        return OrRequestChecker(self, other)

    def __and__(self, other: 'RequestChecker') -> 'RequestChecker':
        return AndRequestChecker(self, other)

    def __xor__(self, other: 'RequestChecker') -> 'RequestChecker':
        return XorRequestChecker(self, other)

    def __neg__(self) -> 'RequestChecker':
        return NegRequestChecker(self)


class NoInstanceCheckRC(RequestChecker, ABC):
    def __call__(self, request: Request) -> None:
        self._check_request(request)


class OrRequestChecker(NoInstanceCheckRC):
    def __init__(self, left: RequestChecker, right: RequestChecker):
        self._left = left
        self._right = right
        self._request_classes = tuple(
            set(left.get_allowed_request_classes()) | set(right.get_allowed_request_classes())
        )

    def get_allowed_request_classes(self) -> VarTuple[Type[Request]]:
        return self._request_classes

    def _check_request(self, request: Request) -> None:
        left_exc = None
        try:
            self._left(request)
        except CannotProvide as exc:
            left_exc = exc
        else:
            return

        try:
            self._right(request)
        except CannotProvide as right_exc:
            raise CannotProvide(sub_errors=[left_exc, right_exc])
        else:
            return


class AndRequestChecker(NoInstanceCheckRC):
    def __init__(self, left: RequestChecker, right: RequestChecker):
        self._left = left
        self._right = right
        self._request_classes = tuple(
            set(left.get_allowed_request_classes()) & set(right.get_allowed_request_classes())
        )

    def get_allowed_request_classes(self) -> VarTuple[Type[Request]]:
        return self._request_classes

    def _check_request(self, request: Request) -> None:
        self._left(request)
        self._right(request)


class NegRequestChecker(NoInstanceCheckRC):
    def __init__(self, rc: RequestChecker):
        self._rc = rc

    def get_allowed_request_classes(self) -> VarTuple[Type[Request]]:
        return (Request,)

    def _check_request(self, request: Request) -> None:
        try:
            self._rc(request)
        except CannotProvide:
            return
        else:
            raise CannotProvide


class XorRequestChecker(NoInstanceCheckRC):
    def __init__(self, left: RequestChecker, right: RequestChecker):
        self._left = left
        self._right = right
        self._request_classes = tuple(
            set(left.get_allowed_request_classes()) ^ set(right.get_allowed_request_classes())
        )

    def get_allowed_request_classes(self) -> VarTuple[Type[Request]]:
        return self._request_classes

    def _check_request(self, request: Request) -> None:
        exceptions = []

        try:
            self._left(request)
        except CannotProvide as exc:
            exceptions.append(exc)

        try:
            self._right(request)
        except CannotProvide as exc:
            exceptions.append(exc)

        if len(exceptions) == 0:
            raise CannotProvide

        if len(exceptions) == 2:
            raise CannotProvide(sub_errors=exceptions)


@dataclass
class FieldNameRC(RequestChecker):
    field_name: str

    def get_allowed_request_classes(self) -> VarTuple[Type[Request]]:
        return (FieldRM,)

    def _check_request(self, request: FieldRM) -> None:
        if self.field_name == request.name:
            return
        raise CannotProvide(f'field_name must be a {self.field_name!r}')


@dataclass
class ExactTypeRC(RequestChecker):
    norm: BaseNormType

    def get_allowed_request_classes(self) -> VarTuple[Type[Request]]:
        return (TypeHintRM,)

    def _check_request(self, request: TypeHintRM) -> None:
        if normalize_type(request.type) == self.norm:
            return
        raise CannotProvide(f'{request.type} must be a equal to {self.norm.source}')


@dataclass
class SubclassRC(RequestChecker):
    type_: type

    def get_allowed_request_classes(self) -> VarTuple[Type[Request]]:
        return (TypeHintRM,)

    def _check_request(self, request: TypeHintRM) -> None:
        norm = normalize_type(request.type)
        if is_subclass_soft(norm.origin, self.type_):
            return
        raise CannotProvide(f'{request.type} must be a subclass of {self.type_}')


@dataclass
class ExactOriginRC(RequestChecker):
    origin: Any

    def get_allowed_request_classes(self) -> VarTuple[Type[Request]]:
        return (TypeHintRM,)

    def _check_request(self, request: TypeHintRM) -> None:
        if normalize_type(request.type).origin == self.origin:
            return
        raise CannotProvide(f'{request.type} must have origin {self.origin}')


def create_type_hint_req_checker(tp: TypeHint) -> RequestChecker:
    try:
        norm = normalize_type(tp)
    except NotSubscribedError:
        return ExactOriginRC(tp)
    except ValueError:
        raise ValueError(f'Can not create RequestChecker from {tp}')

    if isinstance(norm, NormTV):
        raise ValueError(f'Can not create RequestChecker from {tp}')

    origin = norm.origin

    if is_protocol(origin) or isabstract(origin):
        return SubclassRC(tp)

    return ExactTypeRC(norm)


def create_req_checker(pred: Union[TypeHint, str, RequestChecker]) -> RequestChecker:
    if isinstance(pred, str):
        return FieldNameRC(pred)

    if isinstance(pred, RequestChecker):
        return pred

    return create_type_hint_req_checker(pred)


class NextProvider(Provider):
    def apply_provider(self, mediator: Mediator, request: Request[T]) -> T:
        return mediator.provide_from_next(request)


NEXT_PROVIDER = NextProvider()


class LimitingProvider(Provider):
    def __init__(self, request_checker: RequestChecker, provider: Provider):
        self._request_checker = request_checker
        self._provider = provider

    def apply_provider(self, mediator: Mediator, request: Request[T]) -> T:
        self._request_checker(request)
        return self._provider.apply_provider(mediator, request)

    def __repr__(self):
        return f"{type(self).__name__}({self._request_checker}, {self._provider})"


def foreign_parser(func: Callable[[Any], T]) -> Parser[T]:
    def foreign_parser_wrapper(arg):
        try:
            return func(arg)
        except PARSER_COMPAT_EXCEPTIONS as e:
            raise ParseError() from e

    return foreign_parser_wrapper


def foreign_serializer(func: Callable[[T], Any]) -> Serializer[T]:
    def foreign_serializer_wrapper(arg):
        try:
            return func(arg)
        except SerializeError:
            raise
        except Exception as e:
            raise SerializeError() from e

    return foreign_serializer_wrapper


class ValueProvider(Provider, Generic[T]):
    def __init__(self, req_cls: Type[Request[T]], value: T):
        self._req_cls = req_cls
        self._value = value

    def apply_provider(self, mediator: Mediator, request: Request):
        if not isinstance(request, self._req_cls):
            raise CannotProvide

        return self._value

    def __repr__(self):
        return f"{type(self).__name__}({self._req_cls}, {self._value})"


class FactoryProvider(Provider, Generic[T]):
    def __init__(self, req_cls: Type[Request[T]], factory: Callable[[], T]):
        self._req_cls = req_cls
        self._factory = factory

    def apply_provider(self, mediator: Mediator, request: Request):
        if not isinstance(request, self._req_cls):
            raise CannotProvide

        return self._factory()

    def __repr__(self):
        return f"{type(self).__name__}({self._req_cls}, {self._factory})"
