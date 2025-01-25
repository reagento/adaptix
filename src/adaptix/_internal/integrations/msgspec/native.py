from typing import Any, Callable, Iterable, Mapping, Optional, TypedDict, TypeVar

from adaptix import Dumper, Loader, Mediator, Omittable, Omitted, Provider
from adaptix._internal.morphing.load_error import LoadError
from adaptix._internal.morphing.provider_template import DumperProvider, LoaderProvider
from adaptix._internal.morphing.request_cls import DumperRequest, LoaderRequest
from adaptix._internal.provider.facade.provider import bound_by_any
from adaptix._internal.provider.loc_stack_filtering import Pred

try:
    from msgspec import ValidationError, convert, to_builtins
except ImportError:
    pass

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

    def _skip_omitted(self, mapping: Mapping[str, T]) -> Mapping[str, T]:
        return {k: v for k, v in mapping.items() if v != Omitted()}

    def provide_loader(self, mediator: Mediator[Loader], request: LoaderRequest) -> Loader:
        type_ = request.last_loc.type
        if conversion_params := self.conversion_params:
            def native_msgspec_loader(data):
                try:
                    return convert(data, type=type_, **conversion_params)
                except ValidationError as e:
                    raise LoadError() from e

            return native_msgspec_loader

        def native_msgspec_loader_no_params(data):
            try:
                return convert(data, type=type_)
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
    to_builtins: Optional[Convert] = None,
) -> Provider:
    return bound_by_any(
        preds,
        NativeMsgspecProvider(
            conversion_params=convert,
            to_builtins_params=to_builtins,
        ),
    )
