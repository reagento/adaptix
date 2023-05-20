from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterable, Mapping, Optional, Tuple, Union

from ...common import EllipsisType
from ...essential import CannotProvide, Mediator, Provider
from ...model_tools.definitions import BaseField, BaseShape, is_valid_field_id
from ...struct_path import Path
from ..request_cls import LocatedRequest
from ..request_filtering import Pred, ProviderWithRC, RequestChecker
from ..static_provider import StaticProvider, static_provision_action
from .base import Key

RawKey = Union[Key, EllipsisType]
RawPath = Iterable[RawKey]
MapResult = Union[RawKey, RawPath, None]
NameMap = Union[
    Mapping[str, MapResult],
    Iterable[
        Union[
            Mapping[str, MapResult],
            Tuple[Pred, MapResult],
            Tuple[Pred, Callable[[BaseShape, BaseField], MapResult]],
            Provider,
        ]
    ],
]


@dataclass(frozen=True)
class NameMappingRequest(LocatedRequest[Optional[Path]]):
    shape: BaseShape
    field: BaseField


def resolve_map_result(field_id: str, map_result: MapResult) -> Optional[Path]:
    if map_result is None:
        return None
    if isinstance(map_result, (str, int)):
        return (map_result, )
    if isinstance(map_result, EllipsisType):
        return (field_id, )
    return tuple(field_id if isinstance(key, EllipsisType) else key for key in map_result)


class DictNameMappingProvider(StaticProvider):
    def __init__(self, name_map: Mapping[str, MapResult]):
        self._name_map = {key: resolve_map_result(key, map_result) for key, map_result in name_map.items()}
        self._validate()

    def _validate(self) -> None:
        invalid_keys = [key for key in self._name_map if not is_valid_field_id(key)]
        if invalid_keys:
            raise ValueError(
                'Keys of dict name mapping must be valid field_id (valid python identifier).'
                f' Keys {invalid_keys!r} does not meet this condition.'
            )

    @static_provision_action
    def _provide_input_name_layout(self, mediator: Mediator, request: NameMappingRequest) -> Optional[Path]:
        try:
            return self._name_map[request.field.id]
        except KeyError:
            raise CannotProvide


class ConstNameMappingProvider(StaticProvider, ProviderWithRC):
    def __init__(self, request_checker: RequestChecker, result: MapResult):
        self._request_checker = request_checker
        self._result = result

    def get_request_checker(self) -> Optional[RequestChecker]:
        return self._request_checker

    @static_provision_action
    def _provide_input_name_layout(self, mediator: Mediator, request: NameMappingRequest) -> Optional[Path]:
        self._request_checker.check_request(mediator, request)
        return resolve_map_result(request.field.id, self._result)


class FuncNameMappingProvider(StaticProvider, ProviderWithRC):
    def __init__(self, request_checker: RequestChecker, func: Callable[[BaseShape, BaseField], MapResult]):
        self._request_checker = request_checker
        self._func = func

    def get_request_checker(self) -> Optional[RequestChecker]:
        return self._request_checker

    @static_provision_action
    def _provide_input_name_layout(self, mediator: Mediator, request: NameMappingRequest) -> Optional[Path]:
        self._request_checker.check_request(mediator, request)
        result = self._func(request.shape, request.field)
        return resolve_map_result(request.field.id, result)


class AsListNameMappingProvider(StaticProvider):
    @static_provision_action
    def _provide_input_name_layout(self, mediator: Mediator, request: NameMappingRequest) -> Optional[Path]:
        idx = request.shape.fields.index(request.field)
        return (idx, )


@dataclass(frozen=True)
class NameMappingFilterRequest(LocatedRequest[None]):
    pass
