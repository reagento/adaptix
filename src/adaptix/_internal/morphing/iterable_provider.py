# ruff: noqa: SIM113
import collections.abc
from collections.abc import Iterable, Mapping
from inspect import isabstract
from typing import Callable

from ..common import Dumper, Loader
from ..compat import CompatExceptionGroup
from ..definitions import DebugTrail
from ..morphing.provider_template import MorphingProvider
from ..provider.essential import CannotProvide, Mediator
from ..provider.located_request import LocatedRequest, for_predicate
from ..provider.location import GenericParamLoc
from ..struct_trail import append_trail, render_trail_as_note
from ..type_tools import is_subclass_soft
from .json_schema.definitions import JSONSchema
from .json_schema.request_cls import JSONSchemaRequest
from .json_schema.schema_model import JSONSchemaType
from .load_error import AggregateLoadError, ExcludedTypeLoadError, LoadError, TypeLoadError
from .request_cls import DebugTrailRequest, DumperRequest, LoaderRequest, StrictCoercionRequest
from .utils import try_normalize_type

CollectionsMapping = collections.abc.Mapping


@for_predicate(Iterable)
class IterableProvider(MorphingProvider):
    ABC_TO_IMPL = {
        collections.abc.Iterable: tuple,
        collections.abc.Reversible: tuple,
        collections.abc.Collection: tuple,
        collections.abc.Sequence: tuple,
        collections.abc.MutableSequence: list,
        # exclude ByteString, because it does not process as Iterable
        collections.abc.Set: frozenset,
        collections.abc.MutableSet: set,
    }

    def _get_abstract_impl(self, abstract) -> Callable[[Iterable], Iterable]:
        try:
            return self.ABC_TO_IMPL[abstract]
        except KeyError:
            raise CannotProvide

    def _get_iter_factory(self, origin) -> Callable[[Iterable], Iterable]:
        if isabstract(origin):
            return self._get_abstract_impl(origin)
        if callable(origin):
            return origin
        raise CannotProvide

    def _fetch_norm_and_arg(self, request: LocatedRequest):
        norm = try_normalize_type(request.last_loc.type)

        if len(norm.args) != 1 and not (norm.origin is tuple and norm.args[-1] == Ellipsis):
            raise CannotProvide

        try:
            arg = norm.args[0].source
        except AttributeError:
            raise CannotProvide

        if issubclass(norm.origin, collections.abc.Mapping):
            raise CannotProvide

        return norm, arg

    def provide_loader(self, mediator: Mediator, request: LoaderRequest) -> Loader:
        norm, arg = self._fetch_norm_and_arg(request)

        iter_factory = self._get_iter_factory(norm.origin)
        arg_loader = mediator.mandatory_provide(
            request.append_loc(GenericParamLoc(type=arg, generic_pos=0)),
            lambda x: "Cannot create loader for iterable. Loader for element cannot be created",
        )
        strict_coercion = mediator.mandatory_provide(StrictCoercionRequest(loc_stack=request.loc_stack))
        debug_trail = mediator.mandatory_provide(DebugTrailRequest(loc_stack=request.loc_stack))
        return mediator.cached_call(
            self._make_loader,
            origin=norm.origin,
            iter_factory=iter_factory,
            arg_loader=arg_loader,
            strict_coercion=strict_coercion,
            debug_trail=debug_trail,
        )

    def _create_dt_first_iter_loader(self, origin, loader):
        def iter_loader_dt_first(iterable):
            idx = 0

            for el in iterable:
                try:
                    yield loader(el)
                except Exception as e:
                    append_trail(e, idx)
                    raise

                idx += 1

        return iter_loader_dt_first

    def _create_dt_all_iter_loader(self, origin, loader):
        def iter_loader_dt_all(iterable):
            idx = 0
            errors = []
            has_unexpected_error = False

            for el in iterable:
                try:
                    yield loader(el)
                except LoadError as e:
                    errors.append(append_trail(e, idx))
                except Exception as e:
                    errors.append(append_trail(e, idx))
                    has_unexpected_error = True

                idx += 1

            if errors:
                if has_unexpected_error:
                    raise CompatExceptionGroup(
                        f"while loading iterable {origin}",
                        [render_trail_as_note(e) for e in errors],
                    )
                raise AggregateLoadError(
                    f"while loading iterable {origin}",
                    [render_trail_as_note(e) for e in errors],
                )

        return iter_loader_dt_all

    def _make_loader(self, *, origin, iter_factory, arg_loader, strict_coercion: bool, debug_trail: DebugTrail):
        if debug_trail == DebugTrail.DISABLE:
            if strict_coercion:
                return self._get_dt_disable_sc_loader(iter_factory, arg_loader)
            return self._get_dt_disable_non_sc_loader(iter_factory, arg_loader)

        if debug_trail == DebugTrail.FIRST:
            iter_mapper = self._create_dt_first_iter_loader(origin, arg_loader)
        elif debug_trail == DebugTrail.ALL:
            iter_mapper = self._create_dt_all_iter_loader(origin, arg_loader)
        else:
            raise ValueError

        if strict_coercion:
            return self._get_dt_sc_loader(iter_factory, iter_mapper)
        return self._get_dt_non_sc_loader(iter_factory, iter_mapper)

    def _get_dt_non_sc_loader(self, iter_factory, iter_mapper):
        def iter_loader_dt(data):
            try:
                value_iter = iter(data)
            except TypeError:
                raise TypeLoadError(Iterable, data)

            return iter_factory(iter_mapper(value_iter))

        return iter_loader_dt

    def _get_dt_sc_loader(self, iter_factory, iter_mapper):
        def iter_loader_dt_sc(data):
            if isinstance(data, CollectionsMapping):
                raise ExcludedTypeLoadError(Iterable, Mapping, data)
            if type(data) is str:
                raise ExcludedTypeLoadError(Iterable, str, data)

            try:
                value_iter = iter(data)
            except TypeError:
                raise TypeLoadError(Iterable, data)

            return iter_factory(iter_mapper(value_iter))

        return iter_loader_dt_sc

    def _get_dt_disable_sc_loader(self, iter_factory, arg_loader):
        def iter_loader_sc(data):
            if isinstance(data, CollectionsMapping):
                raise ExcludedTypeLoadError(Iterable, Mapping, data)
            if type(data) is str:
                raise ExcludedTypeLoadError(Iterable, str, data)

            try:
                map_iter = map(arg_loader, data)
            except TypeError:
                raise TypeLoadError(Iterable, data)

            return iter_factory(map_iter)

        return iter_loader_sc

    def _get_dt_disable_non_sc_loader(self, iter_factory, arg_loader):
        def iter_loader(data):
            try:
                map_iter = map(arg_loader, data)
            except TypeError:
                raise TypeLoadError(Iterable, data)

            return iter_factory(map_iter)

        return iter_loader

    def provide_dumper(self, mediator: Mediator, request: DumperRequest) -> Dumper:
        norm, arg = self._fetch_norm_and_arg(request)

        iter_factory = self._get_dumper_iter_factory(norm)
        arg_dumper = mediator.mandatory_provide(
            request.append_loc(GenericParamLoc(type=arg, generic_pos=0)),
            lambda x: "Cannot create dumper for iterable. Dumper for element cannot be created",
        )
        debug_trail = mediator.mandatory_provide(DebugTrailRequest(loc_stack=request.loc_stack))
        return mediator.cached_call(
            self._make_dumper,
            origin=norm.origin,
            iter_factory=iter_factory,
            arg_dumper=arg_dumper,
            debug_trail=debug_trail,
        )

    def _get_dumper_iter_factory(self, norm):
        if is_subclass_soft(norm.origin, list):
            return norm.origin
        return tuple

    def _make_dumper(self, *, origin, iter_factory, arg_dumper, debug_trail: DebugTrail):
        if debug_trail == DebugTrail.DISABLE:
            return self._get_dt_disable_dumper(iter_factory, arg_dumper)
        if debug_trail == DebugTrail.FIRST:
            return self._get_dt_dumper(iter_factory, self._create_dt_first_iter_dumper(origin, arg_dumper))
        if debug_trail == DebugTrail.ALL:
            return self._get_dt_dumper(iter_factory, self._create_dt_all_iter_dumper(origin, arg_dumper))
        raise ValueError

    def _create_dt_first_iter_dumper(self, origin, dumper):
        def iter_dumper_dt_first(iterable):
            idx = 0

            for el in iterable:
                try:
                    yield dumper(el)
                except Exception as e:
                    append_trail(e, idx)
                    raise

                idx += 1

        return iter_dumper_dt_first

    def _create_dt_all_iter_dumper(self, origin, dumper):
        def iter_dumper_dt_all(iterable):
            idx = 0
            errors = []

            for el in iterable:
                try:
                    yield dumper(el)
                except Exception as e:
                    errors.append(append_trail(e, idx))

                idx += 1

            if errors:
                raise CompatExceptionGroup(
                    f"while dumping iterable {origin}",
                    [render_trail_as_note(e) for e in errors],
                )

        return iter_dumper_dt_all

    def _get_dt_dumper(self, iter_factory, iter_dumper):
        def iter_dt_dumper(data):
            return iter_factory(iter_dumper(data))

        return iter_dt_dumper

    def _get_dt_disable_dumper(self, iter_factory, arg_dumper: Dumper):
        def iter_dumper(data):
            return iter_factory(map(arg_dumper, data))

        return iter_dumper

    def _generate_json_schema(self, mediator: Mediator, request: JSONSchemaRequest) -> JSONSchema:
        norm, arg = self._fetch_norm_and_arg(request)
        item_schema = mediator.mandatory_provide(
            request.append_loc(
                GenericParamLoc(
                    type=arg,
                    generic_pos=0,
                ),
            ),
            lambda x: "Cannot create JSONSchema for iterable. JSONSchema for element cannot be created",
        )
        if norm.origin is set:
            return JSONSchema(type=JSONSchemaType.ARRAY, items=item_schema, unique_items=True)
        return JSONSchema(type=JSONSchemaType.ARRAY, items=item_schema)
