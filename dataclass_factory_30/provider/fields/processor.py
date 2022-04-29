import itertools
from dataclasses import replace
from typing import Iterable, TypeVar, List, Set, Collection

from .definitions import(
    BaseFieldsFigure, BaseCrown, BaseDictCrown,
    BaseListCrown, BaseFieldCrown, BaseNameMapping,
    ExtraTargets,
)
from ..request_cls import FieldRM

T = TypeVar('T')


def _merge_iters(args: Iterable[Iterable[T]]) -> List[T]:
    return list(itertools.chain.from_iterable(args))


FF_TV = TypeVar("FF_TV", bound=BaseFieldsFigure)


class FigureProcessor:
    """FigureProcessor takes InputFieldsFigure and NameMapping,
    produces new InputFieldsFigure discarding unused fields
    and validates NameMapping
    """

    def _inner_collect_used_fields(self, crown: BaseCrown):
        if isinstance(crown, (BaseDictCrown, BaseListCrown)):
            return _merge_iters(
                self._inner_collect_used_fields(sub_crown)
                for sub_crown in crown.map.values()
            )
        if isinstance(crown, BaseFieldCrown):
            return [crown.name]
        if crown is None:
            return []

    def _collect_used_fields(self, crown: BaseCrown) -> Set[str]:
        lst = self._inner_collect_used_fields(crown)

        used_set = set()
        for f_name in lst:
            if f_name in used_set:
                raise ValueError(f"Field {f_name!r} is duplicated at crown")
            used_set.add(f_name)

        return used_set

    def _field_is_skipped(
        self,
        field: FieldRM,
        skipped_extra_targets: Collection[str],
        used_fields: Set[str],
        extra_targets: Set[str]
    ):
        f_name = field.name
        if f_name in extra_targets:
            return f_name in skipped_extra_targets
        else:
            return f_name not in used_fields

    def _validate_required_fields(
        self,
        figure: BaseFieldsFigure,
        used_fields: Set[str],
        extra_targets: Set[str],
        name_mapping: BaseNameMapping,
    ):
        skipped_required_fields = [
            field.name
            for field in figure.fields
            if field.is_required and self._field_is_skipped(
                field,
                skipped_extra_targets=name_mapping.skipped_extra_targets,
                used_fields=used_fields,
                extra_targets=extra_targets
            )
        ]
        if skipped_required_fields:
            raise ValueError(
                f"Required fields {skipped_required_fields} not presented at name_mapping crown"
            )

    def _get_extra_targets(self, figure: BaseFieldsFigure, used_fields: Set[str]):
        if isinstance(figure.extra, ExtraTargets):
            extra_targets = set(figure.extra.fields)

            extra_targets_at_crown = used_fields & extra_targets
            if extra_targets_at_crown:
                raise ValueError(
                    f"Fields {extra_targets_at_crown} can not be extra target"
                    f" and be presented at name_mapping"
                )

            return extra_targets

        return set()

    def process_figure(self, figure: FF_TV, name_mapping: BaseNameMapping) -> FF_TV:
        used_fields = self._collect_used_fields(name_mapping.crown)
        extra_targets = self._get_extra_targets(figure, used_fields)

        self._validate_required_fields(
            figure=figure,
            used_fields=used_fields,
            extra_targets=extra_targets,
            name_mapping=name_mapping,
        )

        filtered_extra_targets = extra_targets - set(name_mapping.skipped_extra_targets)
        extra = figure.extra

        if isinstance(extra, ExtraTargets):
            extra = ExtraTargets(tuple(filtered_extra_targets))

        # leave only fields that will be passed to constructor
        new_figure = replace(
            figure,
            fields=tuple(
                fld for fld in figure.fields
                if fld.name in used_fields or fld.name in filtered_extra_targets
            ),
            extra=extra,
        )

        return new_figure
