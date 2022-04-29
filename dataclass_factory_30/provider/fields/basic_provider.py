from abc import ABC, abstractmethod
from typing import Union

from ..essential import Request
from .definitions import InputNameMappingRequest, OutputNameMappingRequest, ExtraSkip, ExtraForbid, ExtraCollect
from ..static_provider import StaticProvider, static_provision_action, Mediator
from dataclass_factory_30.provider.fields.definitions import InpNameMapping, OutNameMapping

ExtraPolicy = Union[ExtraSkip, ExtraForbid, ExtraCollect]


class CfgExtraPolicy(Request[ExtraPolicy]):
    pass


class NameMappingProvider(StaticProvider, ABC):
    @abstractmethod
    @static_provision_action(InputNameMappingRequest)
    def _provide_input_name_mapping(self, mediator: Mediator, request: InputNameMappingRequest) -> InpNameMapping:
        pass

    @abstractmethod
    @static_provision_action(OutputNameMappingRequest)
    def _provide_output_name_mapping(self, mediator: Mediator, request: OutputNameMappingRequest) -> OutNameMapping:
        pass
