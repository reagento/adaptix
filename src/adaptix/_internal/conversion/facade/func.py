import inspect
from functools import partial
from typing import Callable, Iterable, Optional, TypeVar, overload

from ...provider.essential import Provider
from .retort import AdornedConverterRetort, ConverterRetort

_global_retort = ConverterRetort()

SrcT = TypeVar('SrcT')
DstT = TypeVar('DstT')
CallableT = TypeVar('CallableT', bound=Callable)


@overload
def impl_converter(func_stub: CallableT, /) -> CallableT:
    ...


@overload
def impl_converter(
    *,
    retort: AdornedConverterRetort = _global_retort,
    recipe: Iterable[Provider] = (),
) -> Callable[[CallableT], CallableT]:
    ...


def impl_converter(
    func_stub: Optional[Callable] = None,
    *,
    retort: AdornedConverterRetort = _global_retort,
    recipe: Iterable[Provider] = (),
):
    if func_stub is None:
        return partial(impl_converter, retort=retort, recipe=recipe)

    if recipe:
        retort = retort.extend(recipe=recipe)
    return retort.produce_converter(
        signature=inspect.signature(func_stub),
        function_name=getattr(func_stub, '__name__', None),
    )
