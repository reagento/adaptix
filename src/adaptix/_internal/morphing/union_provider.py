import collections.abc
from collections.abc import Iterable, Sequence
from typing import Any, Literal, Union

from adaptix._internal.morphing.native.codegen import cached_compile_native, compile_native_scalar, fetch_native_codegen
from adaptix._internal.morphing.native.plan import UnionPlan

from ..common import Dumper, Loader, TypeHint
from ..compat import CompatExceptionGroup
from ..datastructures import ClassDispatcher
from ..definitions import DebugTrail
from ..provider.essential import AggregateCannotProvide, CannotProvide, Mediator
from ..provider.loc_stack_filtering import LocStack
from ..provider.loc_stack_tools import format_type
from ..provider.located_request import LocatedRequest, for_predicate
from ..provider.location import GenericParamLoc
from ..special_cases_optimization import as_is_stub
from ..type_tools import BaseNormType, is_subclass_soft, strip_tags
from ..type_tools.normalize_type import NoneType
from .concrete_provider import none_loader
from .json_schema.definitions import JSONSchema
from .json_schema.request_cls import JSONSchemaRequest
from .load_error import LoadError, TypeLoadError, UnionLoadError
from .model.basic_gen import fetch_code_gen_hook
from .provider_template import DumperProvider, JSONSchemaProvider, LoaderProvider
from .request_cls import DebugTrailRequest, DumperRequest, LoaderRequest
from .sentinel_provider import check_is_sentinel
from .utils import try_normalize_type


@for_predicate(Union)
class UnionProvider(LoaderProvider, DumperProvider, JSONSchemaProvider):
    def _get_loc_stacks_to_request(
        self,
        mediator: Mediator,
        request: LocatedRequest,
        norm: BaseNormType,
        target: str,
    ) -> Sequence[LocStack]:
        loc_stacks = [
            request.loc_stack.append_with(
                GenericParamLoc(
                    type=norm_tp.source,
                    generic_pos=i,
                ),
            )
            for i, norm_tp in enumerate(norm.args)
        ]
        filtered_loc_stacks = [loc_stack for loc_stack in loc_stacks if not check_is_sentinel(mediator, loc_stack)]
        if not filtered_loc_stacks:
            raise CannotProvide(
                f"Cannot create {target} for union consisting only of sentinels",
                is_terminal=True,
                is_demonstrative=True,
            )
        return tuple(filtered_loc_stacks)

    def provide_loader(self, mediator: Mediator, request: LoaderRequest) -> Loader:
        norm = try_normalize_type(request.last_loc.type)
        debug_trail = mediator.mandatory_provide(DebugTrailRequest(loc_stack=request.loc_stack))
        loc_stacks = self._get_loc_stacks_to_request(
            mediator=mediator,
            request=request,
            norm=norm,
            target="loader",
        )
        loaders = mediator.mandatory_provide_by_iterable(
            [request.with_loc_stack(loc_stack) for loc_stack in loc_stacks],
            lambda: "Cannot create loader for union. Loaders for some union cases cannot be created",
        )
        if len(loaders) == 1:
            return loaders[0]

        if (not_none_loader := self._parse_single_optional_loader(loaders)) is not None:
            if debug_trail in (DebugTrail.ALL, DebugTrail.FIRST):
                result = mediator.cached_call(self._produce_single_optional_dt_loader, norm.source, not_none_loader)
                return compile_native_scalar(mediator, request, result)
            if debug_trail == DebugTrail.DISABLE:
                result = mediator.cached_call(self._produce_single_optional_dt_disable_loader, not_none_loader)
                return compile_native_scalar(mediator, request, result)
            raise ValueError

        if debug_trail == DebugTrail.DISABLE:
            result = mediator.cached_call(self._produce_loader_dt_disable, tuple(loaders))
        elif debug_trail == DebugTrail.FIRST:
            result = mediator.cached_call(self._produce_loader_dt_first, norm.source, tuple(loaders))
        elif debug_trail == DebugTrail.ALL:
            result = mediator.cached_call(self._produce_loader_dt_all, norm.source, tuple(loaders))
        else:
            raise ValueError
        from adaptix._internal.morphing.native.registry import describe_scalar_union  # noqa: PLC0415

        result = describe_scalar_union(result, loaders)
        native_codegen = fetch_native_codegen(mediator, request.loc_stack)
        if native_codegen is not None:
            return cached_compile_native(
                mediator, native_codegen,
                UnionPlan(
                    loaders=tuple(loaders),
                    fallback=result,
                    tp=norm.source,
                    debug_trail=debug_trail,
                ),
                hook=fetch_code_gen_hook(mediator, request.loc_stack),
            )
        return result

    def _parse_single_optional_loader(self, loaders: Sequence[Loader]) -> Loader | None:
        try:
            [first, second] = loaders
        except ValueError:
            return None
        if first != none_loader and second == none_loader:
            return first
        if first == none_loader and second != none_loader:
            return second
        return None

    def _produce_single_optional_dt_disable_loader(self, loader: Loader) -> Loader:
        def optional_dt_disable_loader(data):
            if data is None:
                return None
            return loader(data)

        return self.describe_optional(optional_dt_disable_loader, loader)

    def _produce_single_optional_dt_loader(self, tp, loader: Loader) -> Loader:
        def optional_dt_loader(data):
            if data is None:
                return None
            try:
                return loader(data)
            except LoadError as e:
                raise UnionLoadError(f"while loading {tp}", [TypeLoadError(None, data), e])

        return self.describe_optional(optional_dt_loader, loader, tp)

    def describe_optional(self, function, loader, tp=None):
        from adaptix._internal.morphing.native.descriptions import OptionalProgram  # noqa: PLC0415
        from adaptix._internal.morphing.native.registry import (  # noqa: PLC0415
            ScalarProgram,
            get_program,
            identity_spec,
            register_program,
        )

        program = get_program(loader)
        spec = identity_spec(loader)
        if isinstance(program, ScalarProgram):
            register_program(
                function,
                ScalarProgram(
                    function,
                    program.types,
                    nullable=True,
                    coerce_int=program.coerce_int,
                ),
            )
        elif spec is not None and spec[0]:
            register_program(function, ScalarProgram(function, spec[0], nullable=True))
        else:
            register_program(function, OptionalProgram(function, loader, tp))
        return function

    def _produce_loader_dt_disable(self, loader_iter: Iterable[Loader]) -> Loader:
        def union_loader(data):
            for loader in loader_iter:
                try:
                    return loader(data)
                except LoadError:
                    pass
            raise LoadError

        return union_loader

    def _produce_loader_dt_first(self, tp, loader_iter: Iterable[Loader]) -> Loader:
        def union_loader_dt_first(data):
            errors = []
            for loader in loader_iter:
                try:
                    return loader(data)
                except LoadError as e:
                    errors.append(e)

            raise UnionLoadError(f"while loading {tp}", errors)

        return union_loader_dt_first

    def _produce_loader_dt_all(self, tp, loader_iter: Iterable[Loader]) -> Loader:
        def union_loader_dt_all(data):
            errors = []
            has_unexpected_error = False
            for loader in loader_iter:
                try:
                    result = loader(data)
                except LoadError as e:
                    errors.append(e)
                except Exception as e:
                    errors.append(e)
                    has_unexpected_error = True
                else:
                    if not has_unexpected_error:
                        return result

            if has_unexpected_error:
                raise CompatExceptionGroup(f"while loading {tp}", errors)
            raise UnionLoadError(f"while loading {tp}", errors)

        return union_loader_dt_all

    def _is_allowed_origin(self, origin) -> bool:
        return (
            origin is None
            or origin is Literal
            or (isinstance(origin, type) and not is_subclass_soft(origin, collections.abc.Callable))
        )

    def provide_dumper(self, mediator: Mediator, request: DumperRequest) -> Dumper:
        norm = try_normalize_type(request.last_loc.type)
        loc_stacks = self._get_loc_stacks_to_request(
            mediator=mediator,
            request=request,
            norm=norm,
            target="dumper",
        )
        dumpers = mediator.mandatory_provide_by_iterable(
            [request.with_loc_stack(loc_stack) for loc_stack in loc_stacks],
            lambda: "Cannot create dumper for union. Dumpers for some union cases cannot be created",
        )
        if len(dumpers) == 1:
            return dumpers[0]
        if all(dumper == as_is_stub for dumper in dumpers):
            return as_is_stub

        if (not_none_dumper := self._parse_single_optional_dumper(norm, dumpers)) is not None:
            try:
                hash(not_none_dumper)
            except TypeError:
                return self._produce_single_optional_dumper(not_none_dumper)
            return mediator.cached_call(self._produce_single_optional_dumper, not_none_dumper)

        types_with_forbidden_origins = [
            case.source for case in norm.args if not self._is_allowed_origin(strip_tags(case).origin)
        ]
        if types_with_forbidden_origins:
            raise AggregateCannotProvide(
                "All cases of union must be class or Literal",
                [
                    CannotProvide(
                        f"Found {format_type(tp)}",
                        is_demonstrative=True,
                    )
                    for tp in types_with_forbidden_origins
                ],
                is_terminal=True,
                is_demonstrative=True,
            )
        result = mediator.cached_call(
            self._make_dumper,
            tuple(loc_stack.last.type for loc_stack in loc_stacks),
            tuple(dumpers),
        )
        return compile_native_scalar(mediator, request, result)

    def _make_dumper(self, args: Iterable[TypeHint], dumpers: Iterable[Dumper]) -> Dumper:
        non_literals, literal = self._extract_literal(args, dumpers)
        dumper_class_dispatcher = ClassDispatcher[Any, Dumper](
            {self._get_class_for_dumping(case): dumper for case, dumper in non_literals},
        )
        if literal is not None:
            return self._produce_dumper_with_literal(dumper_class_dispatcher, literal[0].args, literal[1])

        result = self._produce_dumper(dumper_class_dispatcher)
        from adaptix._internal.morphing.native.descriptions import UnionDumperProgram  # noqa: PLC0415
        from adaptix._internal.morphing.native.registry import ScalarProgram, register_program  # noqa: PLC0415

        variants = tuple((self._get_class_for_dumping(case), dumper) for case, dumper in non_literals)
        if all(dumper is as_is_stub for _, dumper in variants):
            return register_program(
                result,
                ScalarProgram(
                    result,
                    tuple(cls for cls, _ in variants if cls is not NoneType),
                    nullable=any(cls is NoneType for cls, _ in variants),
                ),
            )
        return register_program(result, UnionDumperProgram(result, variants))

    def _get_class_for_dumping(self, norm: BaseNormType) -> type:
        if norm.origin is None:
            return NoneType
        return strip_tags(norm).origin

    def _parse_single_optional_dumper(self, norm: BaseNormType, dumpers: Iterable[Dumper]) -> Dumper | None:
        try:
            [(first_norm, first_dumper), (second_norm, second_dumper)] = zip(norm.args, dumpers, strict=True)
        except ValueError:
            return None
        if first_norm.origin is None and first_dumper == as_is_stub:
            return second_dumper
        if second_norm.origin is None and second_dumper == as_is_stub:
            return first_dumper
        return None

    def _extract_literal(self, args: Iterable[TypeHint], dumpers: Iterable[Dumper]):
        non_literals: list[tuple[BaseNormType, Dumper]] = []
        literal: tuple[BaseNormType, Dumper] | None = None
        for arg, dumper in zip(args, dumpers, strict=True):
            norm = try_normalize_type(arg)
            if norm.origin == Literal:
                literal = (norm, dumper)
            else:
                non_literals.append((norm, dumper))

        return non_literals, literal

    def _produce_single_optional_dumper(self, dumper: Dumper) -> Dumper:
        def optional_dumper(data):
            if data is None:
                return None
            return dumper(data)

        return self.describe_optional(optional_dumper, dumper)

    def _produce_dumper_with_literal(
        self,
        dumper_class_dispatcher: ClassDispatcher[Any, Dumper],
        literal_cases: Sequence[Any],
        literal_dumper: Dumper,
    ) -> Dumper:
        def union_dumper_with_literal(data):
            if data in literal_cases:
                return literal_dumper(data)
            return dumper_class_dispatcher.dispatch(type(data))(data)

        return union_dumper_with_literal

    def _produce_dumper(self, dumper_class_dispatcher: ClassDispatcher[Any, Dumper]) -> Dumper:
        def union_dumper(data):
            return dumper_class_dispatcher.dispatch(type(data))(data)

        return union_dumper

    def provide_json_schema(self, mediator: Mediator, request: JSONSchemaRequest) -> JSONSchema:
        # TODO: Sync behavior with latest changes and handle corner cases # noqa: TD003
        norm = try_normalize_type(request.last_loc.type)
        loc_stacks = self._get_loc_stacks_to_request(
            mediator=mediator,
            request=request,
            norm=norm,
            target="json schema",
        )
        json_schemas = mediator.mandatory_provide_by_iterable(
            [request.with_loc_stack(loc_stack) for loc_stack in loc_stacks],
            lambda: "Cannot create json schema for union. Dumpers for some union cases cannot be created",
        )
        return JSONSchema(any_of=json_schemas)
