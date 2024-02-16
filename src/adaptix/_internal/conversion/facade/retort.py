# pylint: disable=protected-access, not-callable
import inspect
from functools import partial
from inspect import Parameter, Signature
from typing import Any, Callable, Dict, Iterable, Optional, Tuple, Type, TypeVar, overload

from adaptix import TypeHint

from ...common import Converter
from ...provider.essential import Provider
from ...provider.loc_stack_filtering import P
from ...provider.shape_provider import BUILTIN_SHAPE_PROVIDER
from ...retort.operating_retort import OperatingRetort
from ...type_tools import is_generic_class
from ..coercer_provider import DstAnyCoercerProvider, SameTypeCoercerProvider, SubclassCoercerProvider
from ..converter_provider import BuiltinConverterProvider
from ..linking_provider import SameNameLinkingProvider
from ..request_cls import ConverterRequest
from .checker import ensure_function_is_stub
from .provider import forbid_unlinked_optional


class FilledConversionRetort(OperatingRetort):
    recipe = [
        BUILTIN_SHAPE_PROVIDER,

        BuiltinConverterProvider(),

        SameNameLinkingProvider(is_default=True),

        SameTypeCoercerProvider(),
        DstAnyCoercerProvider(),
        SubclassCoercerProvider(),

        forbid_unlinked_optional(P.ANY),
    ]


AR = TypeVar('AR', bound='AdornedConversionRetort')
SrcT = TypeVar('SrcT')
DstT = TypeVar('DstT')
CallableT = TypeVar('CallableT', bound=Callable)


class AdornedConversionRetort(OperatingRetort):
    def _calculate_derived(self) -> None:
        super()._calculate_derived()
        self._simple_converter_cache: Dict[Tuple[TypeHint, TypeHint, Optional[str]], Converter] = {}

    def extend(self: AR, *, recipe: Iterable[Provider]) -> AR:
        # pylint: disable=protected-access
        with self._clone() as clone:
            clone._inc_instance_recipe = (
                tuple(recipe) + clone._inc_instance_recipe
            )

        return clone

    def _produce_converter(
        self,
        signature: Signature,
        stub_function: Optional[Callable],
        function_name: Optional[str],
    ) -> Callable[..., Any]:
        return self._facade_provide(
            ConverterRequest(
                signature=signature,
                function_name=function_name,
                stub_function=stub_function,
            ),
            error_message=f'Cannot produce converter for {signature!r}',
        )

    def _make_simple_converter(self, src: TypeHint, dst: TypeHint, name: Optional[str]) -> Converter:
        return self._produce_converter(
            signature=Signature(
                parameters=[Parameter('src', kind=Parameter.POSITIONAL_ONLY, annotation=src)],
                return_annotation=dst,
            ),
            stub_function=None,
            function_name=name,
        )

    @overload
    def get_converter(
        self,
        src: Type[SrcT],
        dst: Type[DstT],
        *,
        recipe: Iterable[Provider] = (),
    ) -> Callable[[SrcT], DstT]:
        ...

    @overload
    def get_converter(
        self,
        src: TypeHint,
        dst: TypeHint,
        *,
        name: Optional[str] = None,
        recipe: Iterable[Provider] = (),
    ) -> Callable[[Any], Any]:
        ...

    def get_converter(
        self,
        src: TypeHint,
        dst: TypeHint,
        *,
        name: Optional[str] = None,
        recipe: Iterable[Provider] = (),
    ):
        """Method producing basic converter.

        :param src: A type of converter input data.
        :param dst: A type of converter output data.
        :param recipe: An extra recipe adding to retort.
        :param name: Name of generated function, if value is None, name will be derived.
        :return: Desired converter function
        """
        retort = self.extend(recipe=recipe) if recipe else self

        try:
            return retort._simple_converter_cache[(src, dst, name)]
        except KeyError:
            pass
        converter = retort._make_simple_converter(src, dst, name)
        retort._simple_converter_cache[(src, dst, name)] = converter
        return converter

    @overload
    def impl_converter(self, func_stub: CallableT, /) -> CallableT:
        ...

    @overload
    def impl_converter(self, *, recipe: Iterable[Provider] = ()) -> Callable[[CallableT], CallableT]:
        ...

    def impl_converter(self, stub_function: Optional[Callable] = None, *, recipe: Iterable[Provider] = ()):
        """Decorator producing converter with signature of stub function.

        :param stub_function: A function that signature is used to generate converter.
        :param recipe: An extra recipe adding to retort.
        :return: Desired converter function
        """
        if stub_function is None:
            return partial(self.impl_converter, recipe=recipe)

        ensure_function_is_stub(stub_function)
        retort = self.extend(recipe=recipe) if recipe else self
        return retort._produce_converter(
            signature=inspect.signature(stub_function),
            stub_function=stub_function,
            function_name=None,
        )

    def convert(self, src_obj: Any, dst: Type[DstT], *, recipe: Iterable[Provider] = ()) -> DstT:
        """Method transforming a source object to destination.

        :param src_obj: A type of converter input data.
        :param dst: A type of converter output data.
        :param recipe: An extra recipe adding to retort.
        :return: Instance of destination
        """
        src = type(src_obj)
        if is_generic_class(src):
            raise ValueError(
                f'Can not infer the actual type of generic class instance ({src!r}),'
                ' you have to use `get_converter` explicitly passing the type of object'
            )

        return self.get_converter(src, dst, recipe=recipe)(src_obj)


class ConversionRetort(FilledConversionRetort, AdornedConversionRetort):
    pass
