import itertools
from typing import Set, List, TypeVar, Iterable

from dataclass_factory_30.provider.essential import Mediator, CannotProvide
from dataclass_factory_30.provider.static_provider import StaticProvider, static_provision_action
from .definitions import ExtractionImageRequest, ExtractionImage, ExtractionGen
from .crown_definitions import (
    InputNameMappingRequest,
    BaseDictCrown, BaseCrown, BaseListCrown, BaseFieldCrown,
    InpCrown, InpDictCrown, ExtraCollect, BaseNoneCrown, InpListCrown, InputNameMapping
)
from .extraction_gen import BuiltinExtractionGen

T = TypeVar('T')


def _merge_iters(args: Iterable[Iterable[T]]) -> List[T]:
    return list(itertools.chain.from_iterable(args))


class BuiltinExtractionImageProvider(StaticProvider):
    @static_provision_action(ExtractionImageRequest)
    def _provide_extraction_image(self, mediator: Mediator, request: ExtractionImageRequest) -> ExtractionImage:
        name_mapping = mediator.provide(
            InputNameMappingRequest(
                type=request.initial_request.type,
                figure=request.figure,
            )
        )

        extraction_gen = self._create_extraction_gen(request, name_mapping)

        if self._has_collect_policy(name_mapping.crown) and request.figure.extra is None:
            raise CannotProvide(
                "Cannot create parser that collect extra data"
                " if InputFigure does not take extra data"
            )

        used_direct_fields = self._collect_used_direct_fields(name_mapping.crown)
        skipped_direct_fields = [
            field.name for field in request.figure.fields
            if field.name not in used_direct_fields
        ]

        return ExtractionImage(
            extraction_gen=extraction_gen,
            skipped_fields=skipped_direct_fields + list(name_mapping.skipped_extra_targets),
        )

    def _create_extraction_gen(
        self,
        request: ExtractionImageRequest,
        name_mapping: InputNameMapping,
    ) -> ExtractionGen:
        return BuiltinExtractionGen(
            figure=request.figure,
            crown=name_mapping.crown,
            debug_path=request.initial_request.debug_path,
            strict_coercion=request.initial_request.strict_coercion,
        )

    def _inner_collect_used_direct_fields(self, crown: BaseCrown) -> List[str]:
        if isinstance(crown, BaseDictCrown):
            return _merge_iters(
                self._inner_collect_used_direct_fields(sub_crown)
                for sub_crown in crown.map.values()
            )
        if isinstance(crown, BaseListCrown):
            return _merge_iters(
                self._inner_collect_used_direct_fields(sub_crown)
                for sub_crown in crown.map
            )
        if isinstance(crown, BaseFieldCrown):
            return [crown.name]
        if isinstance(crown, BaseNoneCrown):
            return []
        raise TypeError

    def _collect_used_direct_fields(self, crown: BaseCrown) -> Set[str]:
        lst = self._inner_collect_used_direct_fields(crown)

        used_set = set()
        for f_name in lst:
            if f_name in used_set:
                raise ValueError(f"Field {f_name!r} is duplicated at crown")
            used_set.add(f_name)

        return used_set

    def _has_collect_policy(self, crown: InpCrown) -> bool:
        if isinstance(crown, InpDictCrown):
            return crown.extra == ExtraCollect() or any(
                self._has_collect_policy(sub_crown)
                for sub_crown in crown.map.values()
            )
        if isinstance(crown, InpListCrown):
            return any(
                self._has_collect_policy(sub_crown)
                for sub_crown in crown.map
            )
        if isinstance(crown, (BaseFieldCrown, BaseNoneCrown)):
            return False
        raise TypeError
