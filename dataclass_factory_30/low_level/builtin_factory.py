from dataclasses import dataclass, field
from typing import TypeVar

from .provider import RequestChecker, ConstrainingProxyProvider, create_builtin_req_checker
from ..core import (
    BaseFactory,
    Provider,
    PipeliningMixin,
    SearchState,
    Request,
    collect_class_full_recipe,
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

    def provide_with(self, s_state: BuiltinSearchState, request: Request[T]) -> T:
        # TODO: add caching
        full_recipe = self.recipe + collect_class_full_recipe(type(self))
        start_idx = s_state.offset
        request_cls = type(request)

        for offset, item in enumerate(full_recipe[start_idx:], start_idx):
            provider = self.ensure_provider(item)
            try:
                attr_name = provider.get_request_dispatcher().dispatch(request_cls)
            except KeyError:
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

                if isinstance(pred, RequestChecker):
                    req_checker = pred
                else:
                    req_checker = create_builtin_req_checker(pred)

                provider = self.ensure_provider(sub_value)

                return ConstrainingProxyProvider(req_checker, provider)
            except (TypeError, ValueError):
                pass

        if isinstance(value, type):
            raise ValueError(
                f'Can not create provider from {value}.'
                'You should pass instance instead of class'
            )

        raise ValueError(f'Can not create provider from {value}')
