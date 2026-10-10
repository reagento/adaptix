from adaptix._internal.common import Dumper, Loader
from adaptix._internal.morphing.model.basic_gen import fetch_code_gen_hook
from adaptix._internal.morphing.native.codegen import cached_compile_native, fetch_native_codegen
from adaptix._internal.morphing.native.plan import ScalarPlan
from adaptix._internal.morphing.provider_template import DumperProvider, LoaderProvider
from adaptix._internal.morphing.request_cls import DumperRequest, LoaderRequest
from adaptix._internal.provider.essential import CannotProvide, Mediator


class NativeScalarProvider(LoaderProvider, DumperProvider):
    def provide_loader(self, mediator: Mediator, request: LoaderRequest) -> Loader:
        return self.compile(mediator, request)

    def provide_dumper(self, mediator: Mediator, request: DumperRequest) -> Dumper:
        return self.compile(mediator, request)

    def compile(self, mediator, request):
        generator = fetch_native_codegen(mediator, request.loc_stack)
        if generator is None:
            raise CannotProvide
        mapper = mediator.provide_from_next()
        return cached_compile_native(
            mediator, generator,
            ScalarPlan(
                mapper=mapper,
            ),
            hook=fetch_code_gen_hook(mediator, request.loc_stack),
        )
