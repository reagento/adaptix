import inspect
from functools import partial
from inspect import Parameter, Signature
from typing import Any, Callable, Iterable, Optional, Type, TypeVar, overload

from ...common import TypeHint
from ...provider.essential import Provider
from .checker import ensure_function_is_stub
from .retort import AdornedConverterRetort, ConverterRetort

_global_retort = ConverterRetort()

SrcT = TypeVar('SrcT')
DstT = TypeVar('DstT')
CallableT = TypeVar('CallableT', bound=Callable)


@overload
def get_converter(
    src: Type[SrcT],
    dst: Type[DstT],
    *,
    retort: AdornedConverterRetort = _global_retort,
    recipe: Iterable[Provider] = (),
    name: Optional[str] = None,
) -> Callable[[SrcT], DstT]:
    ...


@overload
def get_converter(
    src: Type[TypeHint],
    dst: Type[TypeHint],
    *,
    retort: AdornedConverterRetort = _global_retort,
    recipe: Iterable[Provider] = (),
    name: Optional[str] = None,
) -> Callable[[Any], Any]:
    ...


def get_converter(
    src: TypeHint,
    dst,
    *,
    retort: AdornedConverterRetort = _global_retort,
    recipe: Iterable[Provider] = (),
    name: Optional[str] = None,
):
    if recipe:
        retort = retort.extend(recipe=recipe)
    return retort.produce_converter(
        signature=Signature(
            parameters=[Parameter('src', kind=Parameter.POSITIONAL_ONLY, annotation=src)],
            return_annotation=dst,
        ),
        stub_function=None,
        function_name=name,
    )


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
    stub_function: Optional[Callable] = None,
    *,
    retort: AdornedConverterRetort = _global_retort,
    recipe: Iterable[Provider] = (),
):
    if stub_function is None:
        return partial(impl_converter, retort=retort, recipe=recipe)

    if recipe:
        retort = retort.extend(recipe=recipe)
    ensure_function_is_stub(stub_function)
    return retort.produce_converter(
        signature=inspect.signature(stub_function),
        stub_function=stub_function,
        function_name=None,
    )
