from dataclasses import dataclass, field
from typing import Optional, List, Dict, Collection

from .essential import Mediator
from .fields_basics import (
    NameMapping, NameMappingProvider,
    DictCrown, ExtraPolicy,
    CfgExtraPolicy, FieldCrown,
    BaseNameMappingRequest, BaseFieldsFigure, InputFieldsFigure,
    ExtraTargets, InputNameMappingRequest, OutputNameMappingRequest,
)
from .name_style import NameStyle, convert_snake_style


# TODO: Add support for path in map


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

    skip: List[str] = field(default_factory=list)
    only_mapped: bool = False
    only: Optional[List[str]] = None
    skip_internal: bool = True

    map: Dict[str, str] = field(default_factory=dict)
    trim_trailing_underscore: bool = True
    name_style: Optional[NameStyle] = None

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

    def _get_extra_targets(self, figure: BaseFieldsFigure) -> Collection[str]:
        if isinstance(figure, InputFieldsFigure) and isinstance(figure.extra, ExtraTargets):
            return set(figure.extra.fields)
        return []

    def _provide_name_mapping(self, mediator: Mediator, request: BaseNameMappingRequest) -> NameMapping:
        extra_policy: ExtraPolicy = mediator.provide(CfgExtraPolicy())

        extra_targets = self._get_extra_targets(request.figure)

        return NameMapping(
            crown=DictCrown(
                map={
                    self._convert_name(fld.field_name): FieldCrown(fld.field_name)
                    for fld in request.figure.fields
                    if not (
                        self._should_skip(fld.field_name)
                        or
                        fld.field_name in extra_targets
                    )
                },
                extra=extra_policy,
            ),
            skipped_extra_targets=list(filter(self._should_skip, extra_targets)),
        )

    def _provide_input_name_mapping(self, mediator: Mediator, request: InputNameMappingRequest) -> NameMapping:
        skipped_required_fields = [
            fld for fld in request.figure.fields
            if fld.is_required and self._should_skip(fld.field_name)
        ]

        if skipped_required_fields:
            raise ValueError  # TODO: replace this error with CannotProvide pushing to user

        return self._provide_name_mapping(mediator, request)

    def _provide_output_name_mapping(self, mediator: Mediator, request: OutputNameMappingRequest) -> NameMapping:
        return self._provide_name_mapping(mediator, request)
