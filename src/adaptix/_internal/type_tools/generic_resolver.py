from dataclasses import dataclass, replace
from typing import Callable, Collection, Dict, Generic, Hashable, Mapping, TypeVar, get_args

from ..common import TypeHint
from .basic_utils import get_type_vars, get_type_vars_of_parametrized, is_generic, is_parametrized, strip_alias
from .implicit_params import fill_implicit_params

M = TypeVar('M')
K = TypeVar('K', bound=Hashable)


@dataclass
class MembersStorage(Generic[K, M]):
    members: Mapping[K, TypeHint]
    overriden: Collection[K]
    meta: M


class GenericResolver(Generic[K, M]):
    def __init__(self, members_getter: Callable[[TypeHint], MembersStorage[K, M]]):
        self._raw_members_getter = members_getter

    def get_resolved_members(self, tp: TypeHint) -> MembersStorage[K, M]:
        if is_parametrized(tp):
            return self._get_members_of_parametrized_generic(tp)
        if is_generic(tp):
            return self._get_members_of_parametrized_generic(fill_implicit_params(tp))
        return self._get_members_by_parents(tp)

    def _get_members_of_parametrized_generic(self, parametrized_generic) -> MembersStorage[K, M]:
        origin = strip_alias(parametrized_generic)
        members_storage = self._get_members_by_parents(origin)
        type_var_to_actual = dict(
            zip(
                get_type_vars(origin),
                get_args(parametrized_generic),
            )
        )
        return replace(
            members_storage,
            members={
                key: self._parametrize_by_dict(type_var_to_actual, tp)
                for key, tp in members_storage.members.items()
            }
        )

    def _parametrize_by_dict(self, type_var_to_actual: Mapping[TypeVar, TypeHint], tp: TypeHint) -> TypeHint:
        if tp in type_var_to_actual:
            return type_var_to_actual[tp]

        params = get_type_vars_of_parametrized(tp)
        if not params:
            return tp
        return tp[tuple(type_var_to_actual[type_var] for type_var in params)]

    def _get_members_by_parents(self, tp) -> MembersStorage[K, M]:
        members_storage = self._raw_members_getter(tp)
        if not any(
            get_type_vars_of_parametrized(tp) or isinstance(tp, TypeVar)
            for tp in members_storage.members.values()
        ):
            return members_storage
        if not hasattr(tp, '__orig_bases__'):
            return members_storage

        bases_members: Dict[K, TypeHint] = {}
        for base in reversed(tp.__orig_bases__):
            bases_members.update(self.get_resolved_members(base).members)

        return replace(
            members_storage,
            members={
                key: (
                    bases_members[key]
                    if key in bases_members and key not in members_storage.overriden else
                    value
                )
                for key, value in members_storage.members.items()
            },
        )
