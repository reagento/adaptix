from dataclasses import dataclass, field
from typing import TypeVar

from ..core import (
    Mediator,
    Request,
    CannotProvide,
)

T = TypeVar('T')


class NoSuitableProvider(Exception):
    pass


@dataclass
class BuiltinSearchState:
    offset: int

    def start_from_next(self):
        return BuiltinSearchState(self.offset + 1)


@dataclass(frozen=True)
class BuiltinFactory:
    def provide_from_next(self, request: Request[T]) -> T:
        pass

    recipe: list = field(default_factory=list)

    def provide(self, request: Request[T]) -> T:
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
                return getattr(provider, attr_name)(self, request)
            except CannotProvide:
                pass

        raise NoSuitableProvider
