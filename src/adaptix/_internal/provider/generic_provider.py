import collections.abc
from dataclasses import dataclass, replace
from inspect import isabstract
from typing import Any, Callable, Collection, Dict, Iterable, Literal, Mapping, Tuple, Union

from ..common import Dumper, Loader
from ..compat import CompatExceptionGroup
from ..essential import CannotProvide, Mediator
from ..load_error import (
    AggregateLoadError,
    BadVariantError,
    ExcludedTypeLoadError,
    LoadError,
    TypeLoadError,
    UnionLoadError,
)
from ..struct_trail import ItemKey, append_trail, render_trail_as_note
from ..type_tools import BaseNormType, is_new_type, is_subclass_soft, normalize_type, strip_tags
from ..type_tools.normalize_type import NotSubscribedError
from ..utils import ClassDispatcher
from .definitions import DebugTrail
from .model.special_cases_optimization import as_is_stub
from .provider_template import DumperProvider, LoaderProvider, for_predicate
from .request_cls import (
    DebugTrailRequest,
    DumperRequest,
    GenericParamLoc,
    LoaderRequest,
    LocatedRequest,
    LocMap,
    StrictCoercionRequest,
    TypeHintLoc,
    get_type_from_request,
)
from .static_provider import StaticProvider, static_provision_action


def stub(arg):
    return arg


class NewTypeUnwrappingProvider(StaticProvider):
    @static_provision_action
    def _provide_unwrapping(self, mediator: Mediator, request: LocatedRequest) -> Loader:
        loc = request.loc_map.get_or_raise(TypeHintLoc, CannotProvide)

        if not is_new_type(loc.type):
            raise CannotProvide

        return mediator.provide(
            replace(
                request,
                loc_map=request.loc_map.add(TypeHintLoc(type=loc.type.__supertype__))
            ),
        )


class TypeHintTagsUnwrappingProvider(StaticProvider):
    @static_provision_action
    def _provide_unwrapping(self, mediator: Mediator, request: LocatedRequest) -> Loader:
        loc = request.loc_map.get_or_raise(TypeHintLoc, CannotProvide)

        try:
            norm = normalize_type(loc.type)
        except NotSubscribedError:
            raise CannotProvide
        unwrapped = strip_tags(norm)
        if unwrapped.source == loc.type:  # type has not changed, continue search
            raise CannotProvide

        return mediator.provide(
            replace(
                request,
                loc_map=request.loc_map.add(TypeHintLoc(type=unwrapped.source))
            ),
        )


def _is_exact_zero_or_one(arg):
    return type(arg) is int and arg in (0, 1)  # pylint: disable=unidiomatic-typecheck


@dataclass
@for_predicate(Literal)
class LiteralProvider(LoaderProvider, DumperProvider):
    tuple_size_limit: int = 4

    def _get_allowed_values_collection(self, args: Collection) -> Collection:
        if len(args) > self.tuple_size_limit:
            return set(args)
        return tuple(args)

    def _provide_loader(self, mediator: Mediator, request: LoaderRequest) -> Loader:
        norm = normalize_type(get_type_from_request(request))
        strict_coercion = mediator.provide(StrictCoercionRequest(loc_map=request.loc_map))

        # TODO: add support for enum
        if strict_coercion and any(
            isinstance(arg, bool) or _is_exact_zero_or_one(arg)
            for arg in norm.args
        ):
            allowed_values_with_types = self._get_allowed_values_collection(
                [(type(el), el) for el in norm.args]
            )
            allowed_values_repr = set(norm.args)

            # since True == 1 and False == 0
            def literal_loader_sc(data):
                if (type(data), data) in allowed_values_with_types:
                    return data
                raise BadVariantError(allowed_values_repr, data)

            return literal_loader_sc

        allowed_values = self._get_allowed_values_collection(norm.args)
        allowed_values_repr = set(norm.args)

        def literal_loader(data):
            if data in allowed_values:
                return data
            raise BadVariantError(allowed_values_repr, data)

        return literal_loader

    def _provide_dumper(self, mediator: Mediator, request: DumperRequest) -> Dumper:
        return stub


@for_predicate(Union)
class UnionProvider(LoaderProvider, DumperProvider):
    def _provide_loader(self, mediator: Mediator, request: LoaderRequest) -> Loader:
        norm = normalize_type(get_type_from_request(request))
        debug_trail = mediator.provide(DebugTrailRequest(loc_map=request.loc_map))

        if self._is_single_optional(norm):
            not_none = next(case for case in norm.args if case.origin is not None)
            not_none_loader = mediator.provide(
                LoaderRequest(
                    loc_map=LocMap(
                        TypeHintLoc(type=not_none.source),
                        GenericParamLoc(pos=0),
                    )
                )
            )
            if debug_trail in (DebugTrail.ALL, DebugTrail.FIRST):
                return self._single_optional_dt_loader(norm.source, not_none_loader)
            if debug_trail == DebugTrail.DISABLE:
                return self._single_optional_dt_disable_loader(not_none_loader)
            raise ValueError

        loaders = tuple(
            mediator.provide(
                LoaderRequest(
                    loc_map=LocMap(
                        TypeHintLoc(type=tp.source),
                        GenericParamLoc(pos=i),
                    )
                )
            )
            for i, tp in enumerate(norm.args)
        )
        if debug_trail == DebugTrail.DISABLE:
            return self._get_loader_dt_disable(loaders)
        if debug_trail == DebugTrail.FIRST:
            return self._get_loader_dt_first(norm.source, loaders)
        if debug_trail == DebugTrail.ALL:
            return self._get_loader_dt_all(norm.source, loaders)
        raise ValueError

    def _single_optional_dt_disable_loader(self, loader: Loader) -> Loader:
        def optional_dt_disable_loader(data):
            if data is None:
                return None
            return loader(data)

        return optional_dt_disable_loader

    def _single_optional_dt_loader(self, tp, loader: Loader) -> Loader:
        def optional_dt_loader(data):
            if data is None:
                return None
            try:
                return loader(data)
            except LoadError as e:
                raise UnionLoadError(f'while loading {tp}', [TypeLoadError(None, data), e])

        return optional_dt_loader

    def _get_loader_dt_disable(self, loader_iter: Iterable[Loader]) -> Loader:
        def union_loader(data):
            for loader in loader_iter:
                try:
                    return loader(data)
                except LoadError:
                    pass
            raise LoadError

        return union_loader

    def _get_loader_dt_first(self, tp, loader_iter: Iterable[Loader]) -> Loader:
        def union_loader_dt_first(data):
            errors = []
            for loader in loader_iter:
                try:
                    return loader(data)
                except LoadError as e:
                    errors.append(e)

            raise UnionLoadError(f'while loading {tp}', errors)

        return union_loader_dt_first

    def _get_loader_dt_all(self, tp, loader_iter: Iterable[Loader]) -> Loader:
        def union_loader_dt_all(data):
            errors = []
            has_unexpected_error = False
            for loader in loader_iter:
                try:
                    result = loader(data)
                except LoadError as e:
                    errors.append(e)
                except Exception as e:  # pylint: disable=broad-exception-caught
                    errors.append(e)
                    has_unexpected_error = True
                else:
                    if not has_unexpected_error:
                        return result

            if has_unexpected_error:
                raise CompatExceptionGroup(f'while loading {tp}', errors)
            raise UnionLoadError(f'while loading {tp}', errors)

        return union_loader_dt_all

    def _is_single_optional(self, norm: BaseNormType) -> bool:
        return len(norm.args) == 2 and None in [case.origin for case in norm.args]

    def _is_class_origin(self, origin) -> bool:
        return (origin is None or isinstance(origin, type)) and not is_subclass_soft(origin, collections.abc.Callable)

    def _provide_dumper(self, mediator: Mediator, request: DumperRequest) -> Dumper:
        request_type = get_type_from_request(request)
        norm = normalize_type(request_type)

        # TODO: allow use Literal[..., None] with non single optional

        if self._is_single_optional(norm):
            not_none = next(case for case in norm.args if case.origin is not None)
            not_none_dumper = mediator.provide(
                DumperRequest(
                    loc_map=LocMap(
                        TypeHintLoc(type=not_none.source),
                        GenericParamLoc(pos=0),
                    )
                )
            )
            if not_none_dumper == as_is_stub:
                return as_is_stub
            return self._get_single_optional_dumper(not_none_dumper)

        non_class_origins = [case.source for case in norm.args if not self._is_class_origin(case.origin)]
        if non_class_origins:
            raise ValueError(
                f"Can not create dumper for {request_type}."
                f" All cases of union must be class, but found {non_class_origins}"
            )

        dumpers = tuple(
            mediator.provide(
                DumperRequest(
                    loc_map=LocMap(
                        TypeHintLoc(type=tp.source),
                        GenericParamLoc(pos=i),
                    )
                )
            )
            for i, tp in enumerate(norm.args)
        )
        if all(dumper == as_is_stub for dumper in dumpers):
            return as_is_stub

        dumper_type_dispatcher = ClassDispatcher(
            {type(None) if case.origin is None else case.origin: dumper for case, dumper in zip(norm.args, dumpers)}
        )
        return self._get_dumper(dumper_type_dispatcher)

    def _get_dumper(self, dumper_type_dispatcher: ClassDispatcher[Any, Dumper]) -> Dumper:
        def union_dumper(data):
            return dumper_type_dispatcher.dispatch(type(data))(data)

        return union_dumper

    def _get_single_optional_dumper(self, dumper: Dumper) -> Dumper:
        def optional_dumper(data):
            if data is None:
                return None
            return dumper(data)

        return optional_dumper


CollectionsMapping = collections.abc.Mapping


@for_predicate(Iterable)
class IterableProvider(LoaderProvider, DumperProvider):
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
        try:
            norm = normalize_type(get_type_from_request(request))
        except ValueError:
            raise CannotProvide

        if len(norm.args) != 1:
            raise CannotProvide

        try:
            arg = norm.args[0].source
        except AttributeError:
            raise CannotProvide

        if issubclass(norm.origin, collections.abc.Mapping):
            raise CannotProvide

        return norm, arg

    def _provide_loader(self, mediator: Mediator, request: LoaderRequest) -> Loader:
        norm, arg = self._fetch_norm_and_arg(request)

        iter_factory = self._get_iter_factory(norm.origin)
        arg_loader = mediator.provide(
            LoaderRequest(
                loc_map=LocMap(
                    TypeHintLoc(type=arg),
                    GenericParamLoc(pos=0),
                )
            )
        )
        strict_coercion = mediator.provide(StrictCoercionRequest(loc_map=request.loc_map))
        debug_trail = mediator.provide(DebugTrailRequest(loc_map=request.loc_map))
        return self._make_loader(
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
                except Exception as e:  # pylint: disable=broad-exception-caught
                    errors.append(append_trail(e, idx))
                    has_unexpected_error = True

                idx += 1

            if errors:
                if has_unexpected_error:
                    raise CompatExceptionGroup(
                        f'while loading iterable {origin}',
                        [render_trail_as_note(e) for e in errors],
                    )
                raise AggregateLoadError(
                    f'while loading iterable {origin}',
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
            if type(data) is str:  # pylint: disable=unidiomatic-typecheck
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
            if type(data) is str:  # pylint: disable=unidiomatic-typecheck
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

    def _provide_dumper(self, mediator: Mediator, request: DumperRequest) -> Dumper:
        norm, arg = self._fetch_norm_and_arg(request)

        iter_factory = self._get_iter_factory(norm.origin)
        arg_dumper = mediator.provide(
            DumperRequest(
                loc_map=LocMap(
                    TypeHintLoc(type=arg),
                    GenericParamLoc(pos=0),
                )
            )
        )
        debug_trail = mediator.provide(DebugTrailRequest(loc_map=request.loc_map))
        return self._make_dumper(
            origin=norm.origin,
            iter_factory=iter_factory,
            arg_dumper=arg_dumper,
            debug_trail=debug_trail,
        )

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
                except Exception as e:  # pylint: disable=broad-exception-caught
                    errors.append(append_trail(e, idx))

                idx += 1

            if errors:
                raise CompatExceptionGroup(
                    f'while dumping iterable {origin}',
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


@for_predicate(Dict)
class DictProvider(LoaderProvider, DumperProvider):
    def _extract_key_value(self, request: LocatedRequest) -> Tuple[BaseNormType, BaseNormType]:
        norm = normalize_type(get_type_from_request(request))
        return norm.args  # type: ignore

    def _provide_loader(self, mediator: Mediator, request: LoaderRequest) -> Loader:
        key, value = self._extract_key_value(request)

        key_loader = mediator.provide(
            LoaderRequest(
                loc_map=LocMap(
                    TypeHintLoc(type=key.source),
                    GenericParamLoc(pos=0),
                )
            )
        )
        value_loader = mediator.provide(
            LoaderRequest(
                loc_map=LocMap(
                    TypeHintLoc(type=value.source),
                    GenericParamLoc(pos=1),
                )
            )
        )
        debug_trail = mediator.provide(
            DebugTrailRequest(loc_map=request.loc_map)
        )
        return self._make_loader(
            key_loader=key_loader,
            value_loader=value_loader,
            debug_trail=debug_trail,
        )

    def _make_loader(self, key_loader: Loader, value_loader: Loader, debug_trail: DebugTrail):
        if debug_trail == DebugTrail.DISABLE:
            return self._get_loader_dt_disable(key_loader, value_loader)
        if debug_trail == DebugTrail.FIRST:
            return self._get_loader_dt_first(key_loader, value_loader)
        if debug_trail == DebugTrail.ALL:
            return self._get_loader_dt_all(key_loader, value_loader)
        raise ValueError

    def _get_loader_dt_disable(self, key_loader: Loader, value_loader: Loader):
        def dict_loader(data):
            try:
                items_method = data.items
            except AttributeError:
                raise TypeLoadError(CollectionsMapping, data)

            result = {}
            for k, v in items_method():
                result[key_loader(k)] = value_loader(v)

            return result

        return dict_loader

    def _get_loader_dt_first(self, key_loader: Loader, value_loader: Loader):
        def dict_loader_dt_first(data):
            try:
                items_method = data.items
            except AttributeError:
                raise TypeLoadError(CollectionsMapping, data)

            result = {}
            for k, v in items_method():
                try:
                    loaded_key = key_loader(k)
                except Exception as e:
                    append_trail(e, ItemKey(k))
                    raise

                try:
                    loaded_value = value_loader(v)
                except Exception as e:
                    append_trail(e, k)
                    raise

                result[loaded_key] = loaded_value

            return result

        return dict_loader_dt_first

    def _get_loader_dt_all(self, key_loader: Loader, value_loader: Loader):  # noqa: C901,CCR001
        def dict_loader_dt_all(data):  # noqa: CCR001
            try:
                items_method = data.items
            except AttributeError:
                raise TypeLoadError(CollectionsMapping, data)

            result = {}
            errors = []
            has_unexpected_error = False
            for k, v in items_method():
                try:
                    loaded_key = key_loader(k)
                except LoadError as e:
                    errors.append(append_trail(e, ItemKey(k)))
                except Exception as e:  # pylint: disable=broad-exception-caught
                    errors.append(append_trail(e, ItemKey(k)))
                    has_unexpected_error = True

                try:
                    loaded_value = value_loader(v)
                except LoadError as e:
                    errors.append(append_trail(e, k))
                except Exception as e:  # pylint: disable=broad-exception-caught
                    errors.append(append_trail(e, k))
                    has_unexpected_error = True

                if not errors:
                    result[loaded_key] = loaded_value

            if errors:
                if has_unexpected_error:
                    raise CompatExceptionGroup(
                        f'while loading {dict}',
                        [render_trail_as_note(e) for e in errors],
                    )
                raise AggregateLoadError(
                    f'while loading {dict}',
                    [render_trail_as_note(e) for e in errors],
                )
            return result

        return dict_loader_dt_all

    def _provide_dumper(self, mediator: Mediator, request: DumperRequest) -> Dumper:
        key, value = self._extract_key_value(request)

        key_dumper = mediator.provide(
            DumperRequest(
                loc_map=LocMap(
                    TypeHintLoc(type=key.source),
                    GenericParamLoc(pos=0),
                )
            )
        )
        value_dumper = mediator.provide(
            DumperRequest(
                loc_map=LocMap(
                    TypeHintLoc(type=value.source),
                    GenericParamLoc(pos=1),
                )
            )
        )
        debug_trail = mediator.provide(
            DebugTrailRequest(loc_map=request.loc_map)
        )
        return self._make_dumper(
            key_dumper=key_dumper,
            value_dumper=value_dumper,
            debug_trail=debug_trail,
        )

    def _make_dumper(self, key_dumper: Dumper, value_dumper: Dumper, debug_trail: DebugTrail):
        if debug_trail == DebugTrail.DISABLE:
            return self._get_dumper_dt_disable(
                key_dumper=key_dumper,
                value_dumper=value_dumper,
            )
        if debug_trail == DebugTrail.FIRST:
            return self._get_dumper_dt_first(
                key_dumper=key_dumper,
                value_dumper=value_dumper,
            )
        if debug_trail == DebugTrail.ALL:
            return self._get_dumper_dt_all(
                key_dumper=key_dumper,
                value_dumper=value_dumper,
            )
        raise ValueError

    def _get_dumper_dt_disable(self, key_dumper, value_dumper):
        def dict_dumper_dt_disable(data: Mapping):
            result = {}
            for k, v in data.items():
                result[key_dumper(k)] = value_dumper(v)

            return result

        return dict_dumper_dt_disable

    def _get_dumper_dt_first(self, key_dumper, value_dumper):
        def dict_dumper_dt_first(data: Mapping):
            result = {}
            for k, v in data.items():
                try:
                    dumped_key = key_dumper(k)
                except Exception as e:
                    append_trail(e, ItemKey(k))
                    raise

                try:
                    dumped_value = value_dumper(v)
                except Exception as e:
                    append_trail(e, k)
                    raise

                result[dumped_key] = dumped_value

            return result

        return dict_dumper_dt_first

    def _get_dumper_dt_all(self, key_dumper, value_dumper):
        def dict_dumper_dt_all(data: Mapping):
            result = {}
            errors = []
            for k, v in data.items():
                try:
                    dumped_key = key_dumper(k)
                except Exception as e:  # pylint: disable=broad-exception-caught
                    errors.append(append_trail(e, ItemKey(k)))

                try:
                    dumped_value = value_dumper(v)
                except Exception as e:  # pylint: disable=broad-exception-caught
                    errors.append(append_trail(e, k))

                if not errors:
                    result[dumped_key] = dumped_value

            if errors:
                raise CompatExceptionGroup(
                    f'while dumping {dict}',
                    [render_trail_as_note(e) for e in errors],
                )
            return result

        return dict_dumper_dt_all
