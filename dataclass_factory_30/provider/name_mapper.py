from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple, TypeVar, Union, cast

# TODO: Add support for path in map
from ..model_tools import DefaultFactory, DefaultValue, NoDefault, OutputField
from .essential import Mediator
from .model import (
    BaseCrown,
    BaseDictCrown,
    BaseFieldCrown,
    BaseListCrown,
    BaseNameMappingRequest,
    BaseNoneCrown,
    DictExtraPolicy,
    ExtraCollect,
    ExtraSkip,
    Filler,
    InpCrown,
    InpDictCrown,
    InpFieldCrown,
    InpListCrown,
    InpNoneCrown,
    InputNameMapping,
    InputNameMappingRequest,
    ListExtraPolicy,
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
from .model.crown_definitions import (
    BaseExtraMove,
    Extractor,
    ExtraExtract,
    ExtraForbid,
    ExtraKwargs,
    ExtraSaturate,
    ExtraTargets,
    InpExtraMove,
    OutExtraMove,
    RootBaseCrown,
    Saturator,
)
from .name_style import NameStyle, convert_snake_style

T = TypeVar('T')

ExtraIn = Union[ExtraSkip, str, Sequence[str], ExtraForbid, ExtraKwargs, Saturator]
ExtraOut = Union[ExtraSkip, str, Sequence[str], Extractor]


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

    omit_default: bool = True

    extra_in: ExtraIn = ExtraSkip()
    extra_out: ExtraOut = ExtraSkip()

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

    def _provide_crown(
        self,
        mediator: Mediator,
        request: BaseNameMappingRequest,
        extra_move: BaseExtraMove,
    ) -> RootBaseCrown:
        extra_targets = extra_move.fields if isinstance(extra_move, ExtraTargets) else ()

        return BaseDictCrown(
            map={
                self._convert_name(fld.name): BaseFieldCrown(fld.name)
                for fld in request.figure.fields
                if not (
                    self._should_skip(fld.name)
                    or
                    fld.name in extra_targets
                )
            },
        )

    def _to_inp_crown(
        self,
        base: BaseCrown,
        dict_extra_policy: DictExtraPolicy,
        list_extra_policy: ListExtraPolicy,
    ) -> InpCrown:
        if isinstance(base, BaseFieldCrown):
            return InpFieldCrown(base.name)
        if isinstance(base, BaseNoneCrown):
            return InpNoneCrown()
        if isinstance(base, BaseDictCrown):
            return InpDictCrown(
                map={
                    key: self._to_inp_crown(value, dict_extra_policy, list_extra_policy)
                    for key, value in base.map.items()
                },
                extra_policy=dict_extra_policy,
            )
        if isinstance(base, BaseListCrown):
            return InpListCrown(
                map=[
                    self._to_inp_crown(value, dict_extra_policy, list_extra_policy)
                    for value in base.map
                ],
                extra_policy=list_extra_policy,
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

    def _create_extra_targets(self, extra: Union[str, Sequence[str]]) -> ExtraTargets:
        if isinstance(extra, str):
            return ExtraTargets((extra, ))
        return ExtraTargets(tuple(extra))

    def _get_inp_extra_move_and_policy(self, extra: ExtraIn) -> Tuple[InpExtraMove, DictExtraPolicy]:
        if extra == ExtraForbid():
            return None, ExtraForbid()
        if extra == ExtraSkip():
            return None, ExtraSkip()
        if extra == ExtraKwargs():
            return ExtraKwargs(), ExtraCollect()
        if callable(extra):
            return ExtraSaturate(extra), ExtraCollect()
        return self._create_extra_targets(extra), ExtraCollect()  # type: ignore[arg-type]

    def _get_out_extra_move(self, extra: ExtraOut) -> OutExtraMove:
        if extra == ExtraSkip():
            return None
        if callable(extra):
            return ExtraExtract(extra)
        return self._create_extra_targets(extra)  # type: ignore[arg-type]

    def _provide_input_name_mapping(self, mediator: Mediator, request: InputNameMappingRequest) -> InputNameMapping:
        skipped_required_fields = [
            fld for fld in request.figure.fields
            if fld.is_required and self._should_skip(fld.name)
        ]

        if skipped_required_fields:
            sr_field_names = [fld.name for fld in skipped_required_fields]
            raise ValueError(
                f"Can not create name mapping for type {request.type}"
                f" that skips required fields {sr_field_names}",
            )

        extra_move, extra_policy = self._get_inp_extra_move_and_policy(self.extra_in)
        crown = self._provide_crown(mediator, request, extra_move)

        if extra_policy == ExtraCollect() and isinstance(crown, BaseListCrown):
            raise ValueError

        return InputNameMapping(
            crown=cast(
                RootInpCrown,
                self._to_inp_crown(
                    base=crown,
                    dict_extra_policy=extra_policy,
                    list_extra_policy=extra_policy,  # type: ignore[arg-type]
                )
            ),
            extra_move=extra_move,
        )

    def _create_sieve(self, field_: OutputField) -> Sieve:
        if isinstance(field_.default, DefaultValue):
            default_value = field_.default.value

            return lambda x: x != default_value

        if isinstance(field_.default, DefaultFactory):
            default_factory = field_.default.factory

            return lambda x: x != default_factory()

        raise ValueError

    def _provide_output_name_mapping(self, mediator: Mediator, request: OutputNameMappingRequest) -> OutputNameMapping:
        extra_move = self._get_out_extra_move(self.extra_out)
        crown = self._provide_crown(mediator, request, extra_move)

        if self.omit_default:
            sieves = {
                fld.name: self._create_sieve(fld)
                for fld in request.figure.fields if fld.default != NoDefault()
            }
        else:
            sieves = {}

        return OutputNameMapping(
            crown=cast(
                RootOutCrown,
                self._to_out_crown(
                    base=crown,
                    filler=DefaultValue(None),
                    sieves=sieves
                ),
            ),
            extra_move=extra_move,
        )
