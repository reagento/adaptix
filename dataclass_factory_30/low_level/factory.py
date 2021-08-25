from dataclasses import dataclass, field
from typing import TypeVar

from .provider import TypeRequestChecker, ConstrainingProxyProvider
from ..core import (
    BaseFactory,
    Provider,
    PipeliningMixin,
    SearchState,
    Request,
    collect_class_full_recipe,
    find_provision_action_attr_name,
    CannotProvide,
    NoSuitableProvider
)

T = TypeVar('T')


@dataclass
class BuiltinSearchState(SearchState):
    offset: int

    def start_from_next(self):
        return BuiltinSearchState(self.offset + 1)


@dataclass(frozen=True)
class BuiltinFactory(BaseFactory[BuiltinSearchState], PipeliningMixin):
    recipe: list = field(default_factory=list)

    def create_init_search_state(self) -> BuiltinSearchState:
        return BuiltinSearchState(0)

    def provide(self, s_state: BuiltinSearchState, request: Request[T]) -> T:
        # TODO: add caching
        full_recipe = self.recipe + collect_class_full_recipe(type(self))
        start_idx = s_state.offset
        request_cls = type(request)

        for offset, item in enumerate(full_recipe[start_idx:], start_idx):
            provider = self.ensure_provider(item)
            attr_name = find_provision_action_attr_name(request_cls, type(provider))
            if attr_name is None:
                continue

            item_s_state = BuiltinSearchState(offset)
            try:
                return getattr(provider, attr_name)(self, item_s_state, request)
            except CannotProvide:
                pass

        raise NoSuitableProvider

    def ensure_provider(self, value) -> Provider:
        if isinstance(value, Provider):
            return value

        if isinstance(value, tuple):
            try:
                pred, sub_value = value

                tr_checker = TypeRequestChecker(pred)
                provider = self.ensure_provider(sub_value)

                return ConstrainingProxyProvider(tr_checker, provider)
            except (TypeError, ValueError):
                pass

        if isinstance(value, type):
            raise ValueError(
                f'Can not create provider from {value}.'
                'You should pass instance instead of class'
            )

        raise ValueError(f'Can not create provider from {value}')
