from dataclasses import dataclass, field as dc_field
from typing import Collection, Dict, List, Optional, cast

# TODO: Add support for path in map
from ..model_tools import BaseFigure, DefaultFactory, DefaultValue, ExtraTargets, NoDefault, OutputField
from .essential import Mediator
from .model import (
    BaseCrown,
    BaseDictCrown,
    BaseFieldCrown,
    BaseListCrown,
    BaseNameMapping,
    BaseNameMappingRequest,
    BaseNoneCrown,
    CfgExtraPolicy,
    ExtraCollect,
    ExtraPolicy,
    Filler,
    InpCrown,
    InpDictCrown,
    InpExtraPolicyDict,
    InpExtraPolicyList,
    InpFieldCrown,
    InpListCrown,
    InpNoneCrown,
    InputNameMapping,
    InputNameMappingRequest,
    NameMappingProvider,
    OutCrown,
    OutDictCrown,
    OutFieldCrown,
    OutListCrown,
    OutNoneCrown,
    OutputNameMapping,
    OutputNameMappingRequest,
    RootInpCrown,
    RootOutCrown,
    Sieve,
)
from .name_style import NameStyle, convert_snake_style


@dataclass(frozen=True)
class NameMapper(NameMappingProvider):
    """A NameMapper decides which fields will be presented
    to the outside world and how they will look.

    The mapping process consists of two stages:
    1. Determining which fields are presented
    2. Mutating names of presented fields

    Parameters that are responsible for
    filtering of available have such priority
    1. skip
    2. only | only_mapped
    3. skip_internal

    Fields selected by only and only_mapped are unified.
    Rules with higher priority overlap other rules.

    Mutating parameters works in that way:
    Mapper tries to use the value from the map.
    If the field is not presented in the map,
    trim trailing underscore and convert name style.

    The field must follow snake_case to could be converted.

    If you try to skip required input field,
    class will raise error
    """

    skip: List[str] = dc_field(default_factory=list)
    only_mapped: bool = False
    only: Optional[List[str]] = None
    skip_internal: bool = True

    map: Dict[str, str] = dc_field(default_factory=dict)
    trim_trailing_underscore: bool = True
    name_style: Optional[NameStyle] = None

    omit_default: bool = True  # TODO: may be ask factory for this parameter

    def _should_skip(self, name: str) -> bool:
        if name in self.skip:
            return True

        if self.only_mapped or self.only is not None:
            if self.only_mapped and name in self.map:
                return False

            if self.only is not None and name in self.only:
                return False

            return True

        if self.skip_internal and name.startswith('_'):
            return True

        return False

    def _convert_name(self, name: str) -> str:
        try:
            name = self.map[name]
        except KeyError:
            if self.trim_trailing_underscore:
                name = name.rstrip('_')

            if self.name_style is not None:
                name = convert_snake_style(name, self.name_style)

        return name

    def _get_extra_targets(self, figure: BaseFigure) -> Collection[str]:
        if isinstance(figure.extra, ExtraTargets):
            return set(figure.extra.fields)
        return []

    def _provide_name_mapping(self, mediator: Mediator, request: BaseNameMappingRequest) -> BaseNameMapping:
        extra_targets = self._get_extra_targets(request.figure)

        return BaseNameMapping(
            crown=BaseDictCrown(
                map={
                    self._convert_name(fld.name): BaseFieldCrown(fld.name)
                    for fld in request.figure.fields
                    if not (
                        self._should_skip(fld.name)
                        or
                        fld.name in extra_targets
                    )
                },
            ),
            skipped_extra_targets=list(filter(self._should_skip, extra_targets)),
        )

    def _to_inp_crown(
        self,
        base: BaseCrown,
        dict_extra: InpExtraPolicyDict,
        list_extra: InpExtraPolicyList,
    ) -> InpCrown:
        if isinstance(base, BaseFieldCrown):
            return InpFieldCrown(base.name)
        if isinstance(base, BaseNoneCrown):
            return InpNoneCrown()
        if isinstance(base, BaseDictCrown):
            return InpDictCrown(
                map={
                    key: self._to_inp_crown(value, dict_extra, list_extra)
                    for key, value in base.map.items()
                },
                extra=dict_extra,
            )
        if isinstance(base, BaseListCrown):
            return InpListCrown(
                map=[
                    self._to_inp_crown(value, dict_extra, list_extra)
                    for value in base.map
                ],
                extra=list_extra,
            )
        raise RuntimeError

    def _to_out_crown(
        self,
        base: BaseCrown,
        filler: Filler,
        sieves: Dict[str, Sieve]
    ) -> OutCrown:
        if isinstance(base, BaseFieldCrown):
            return OutFieldCrown(base.name)
        if isinstance(base, BaseNoneCrown):
            return OutNoneCrown(filler)
        if isinstance(base, BaseDictCrown):
            return OutDictCrown(
                map={
                    key: self._to_out_crown(value, filler, sieves)
                    for key, value in base.map.items()
                },
                sieves={k: sieves[k] for k in base.map if k in sieves},
            )
        if isinstance(base, BaseListCrown):
            return OutListCrown(
                map=[
                    self._to_out_crown(value, filler, sieves)
                    for value in base.map
                ],
            )
        raise RuntimeError

    def _provide_input_name_mapping(self, mediator: Mediator, request: InputNameMappingRequest) -> InputNameMapping:
        skipped_required_fields = [
            fld for fld in request.figure.fields
            if fld.is_required and self._should_skip(fld.name)
        ]

        if skipped_required_fields:
            sr_field_names = [field.name for field in skipped_required_fields]
            raise ValueError(
                f"Can not create name mapping for type {request.type}"
                f" that skips required fields {sr_field_names}",
            )

        base_name_mapping = self._provide_name_mapping(mediator, request)
        extra_policy: ExtraPolicy = mediator.provide(CfgExtraPolicy())

        if isinstance(extra_policy, ExtraCollect) and isinstance(base_name_mapping.crown, BaseListCrown):
            raise ValueError

        return InputNameMapping(
            crown=cast(
                RootInpCrown,
                self._to_inp_crown(
                    base_name_mapping.crown, extra_policy, cast(InpExtraPolicyList, extra_policy)
                )
            ),
            skipped_extra_targets=base_name_mapping.skipped_extra_targets,
        )

    def _create_sieve(self, field: OutputField) -> Sieve:
        if isinstance(field.default, DefaultValue):
            default_value = field.default.value

            return lambda x: x != default_value

        if isinstance(field.default, DefaultFactory):
            default_factory = field.default.factory

            return lambda x: x != default_factory()

        raise ValueError

    def _provide_output_name_mapping(self, mediator: Mediator, request: OutputNameMappingRequest) -> OutputNameMapping:
        base_name_mapping = self._provide_name_mapping(mediator, request)

        if self.omit_default:
            sieves = {
                field.name: self._create_sieve(field)
                for field in request.figure.fields if field.default != NoDefault()
            }
        else:
            sieves = {}

        return OutputNameMapping(
            crown=cast(
                RootOutCrown,
                self._to_out_crown(
                    base_name_mapping.crown, filler=DefaultValue(None), sieves=sieves
                ),
            ),
            skipped_extra_targets=base_name_mapping.skipped_extra_targets,
        )
