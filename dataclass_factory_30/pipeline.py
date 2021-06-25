from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TypeVar, Generic, Tuple, final, Type, List

from .core import Provider, ProvisionCtx, BaseFactory, CannotProvide

T = TypeVar('T')
V = TypeVar('V')


def _make_pipeline(left, right) -> 'Pipeline':
    if isinstance(left, Pipeline):
        left_elems = left.elements
    else:
        left_elems = (left,)

    if isinstance(right, Pipeline):
        right_elems = right.elements
    else:
        right_elems = (right,)

    return Pipeline(
        left_elems + right_elems
    )


class PipeliningMixin:
    """
    A mixin that makes your class able to create a pipeline
    """

    @final
    def __or__(self, other) -> 'Pipeline':
        return _make_pipeline(self, other)

    @final
    def __ror__(self, other) -> 'Pipeline':
        return _make_pipeline(other, self)


class PipelineEvalMixin(ABC):
    """
    A special mixin for Provider Template that allows to eval pipeline.
    Subclass should implement :method:`eval_pipeline`
    """

    @classmethod
    @abstractmethod
    def eval_pipeline(
        cls,
        providers: List[Provider],
        factory: 'BaseFactory',
        offset: int,
        ctx: ProvisionCtx
    ):
        pass


@dataclass(frozen=True)
class Pipeline(Provider, PipeliningMixin, Generic[V]):
    elements: Tuple[V, ...]

    def _provide_other(
        self,
        provider_tmpl: 'Type[Provider[T]]',
        factory: 'BaseFactory',
        offset: int,
        ctx: ProvisionCtx
    ) -> T:
        if not issubclass(provider_tmpl, PipelineEvalMixin):
            raise CannotProvide

        providers = [factory.ensure_provider(el) for el in self.elements]

        return provider_tmpl.eval_pipeline(
            providers, factory, offset, ctx
        )

