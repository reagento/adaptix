import contextlib
from collections.abc import Iterable
from typing import Any, Callable, Optional, TypedDict, TypeVar

from ...common import Dumper, Loader
from ...morphing.load_error import LoadError
from ...morphing.provider_template import DumperProvider, LoaderProvider
from ...morphing.request_cls import DumperRequest, LoaderRequest
from ...provider.essential import Mediator, Provider
from ...provider.facade.provider import bound_by_any
from ...provider.loc_stack_filtering import Pred

with contextlib.suppress(ImportError):
    from msgspec import ValidationError, convert, to_builtins


T = TypeVar("T")


class Convert(TypedDict, total=False):
    builtin_types: Iterable[type]
    str_keys: bool
    strict: bool
    from_attributes: bool
    dec_hook: Callable[[Any], Any]


class ToBuiltins(TypedDict, total=False):
    builtin_types: Iterable[type]
    str_keys: bool
    enc_hook: Callable[[Any], Any]


class NativeMsgspecProvider(LoaderProvider, DumperProvider):
    def __init__(
        self,
        conversion_params: Optional[Convert],
        to_builtins_params: Optional[ToBuiltins],
    ):
        self.conversion_params = conversion_params
        self.to_builtins_params = to_builtins_params

    def provide_loader(self, mediator: Mediator[Loader], request: LoaderRequest) -> Loader:
        tp = request.last_loc.type
        if conversion_params := self.conversion_params:
            def native_msgspec_loader(data):
                try:
                    return convert(data, type=tp, **conversion_params)
                except ValidationError as e:
                    raise LoadError() from e

            return native_msgspec_loader

        def native_msgspec_loader_no_params(data):
            try:
                return convert(data, type=tp)
            except ValidationError as e:
                raise LoadError() from e

        return native_msgspec_loader_no_params

    def provide_dumper(self, mediator: Mediator[Dumper], request: DumperRequest) -> Dumper:
        if to_builtins_params := self.to_builtins_params:
            def native_msgspec_dumper_with_params(data):
                return to_builtins(data, **to_builtins_params)

            return native_msgspec_dumper_with_params

        return to_builtins


def native_msgspec(
    *preds: Pred,
    convert: Optional[Convert] = None,
    to_builtins: Optional[ToBuiltins] = None,
) -> Provider:
    return bound_by_any(
        preds,
        NativeMsgspecProvider(
            conversion_params=convert,
            to_builtins_params=to_builtins,
        ),
    )
