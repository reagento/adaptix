import collections.abc
from collections import defaultdict
from dataclasses import replace
from typing import Callable, DefaultDict, Dict, Mapping, Optional, Tuple

from ..common import Dumper, Loader
from ..compat import CompatExceptionGroup
from ..definitions import DebugTrail
from ..morphing.provider_template import DumperProvider, LoaderProvider
from ..provider.essential import Mediator
from ..provider.provider_template import for_predicate
from ..provider.request_cls import (
    DebugTrailRequest,
    GenericParamLoc,
    LocatedRequest,
    LocMap,
    TypeHintLoc,
    get_type_from_request,
    try_normalize_type,
)
from ..struct_trail import ItemKey, append_trail, render_trail_as_note
from ..type_tools import BaseNormType
from .load_error import AggregateLoadError, LoadError, TypeLoadError
from .request_cls import DumperRequest, LoaderRequest

CollectionsMapping = collections.abc.Mapping


@for_predicate(Dict)
class DictProvider(LoaderProvider, DumperProvider):
    def _extract_key_value(self, request: LocatedRequest) -> Tuple[BaseNormType, BaseNormType]:
        norm = try_normalize_type(get_type_from_request(request))
        return norm.args

    def _provide_loader(self, mediator: Mediator, request: LoaderRequest) -> Loader:
        key, value = self._extract_key_value(request)

        key_loader = mediator.mandatory_provide(
            LoaderRequest(
                loc_stack=request.loc_stack.append_with(
                    LocMap(
                        TypeHintLoc(type=key.source),
                        GenericParamLoc(generic_pos=0),
                    )
                )
            ),
            lambda x: 'Cannot create loader for dict. Loader for key cannot be created',
        )
        value_loader = mediator.mandatory_provide(
            LoaderRequest(
                loc_stack=request.loc_stack.append_with(
                    LocMap(
                        TypeHintLoc(type=value.source),
                        GenericParamLoc(generic_pos=1),
                    )
                )
            ),
            lambda x: 'Cannot create loader for dict. Loader for value cannot be created',
        )
        debug_trail = mediator.mandatory_provide(
            DebugTrailRequest(loc_stack=request.loc_stack)
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

        key_dumper = mediator.mandatory_provide(
            DumperRequest(
                loc_stack=request.loc_stack.append_with(
                    LocMap(
                        TypeHintLoc(type=key.source),
                        GenericParamLoc(generic_pos=0),
                    )
                )
            ),
            lambda x: 'Cannot create dumper for dict. Dumper for key cannot be created',
        )
        value_dumper = mediator.mandatory_provide(
            DumperRequest(
                loc_stack=request.loc_stack.append_with(
                    LocMap(
                        TypeHintLoc(type=value.source),
                        GenericParamLoc(generic_pos=1),
                    )
                )
            ),
            lambda x: 'Cannot create dumper for dict. Dumper for value cannot be created',
        )
        debug_trail = mediator.mandatory_provide(
            DebugTrailRequest(loc_stack=request.loc_stack)
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


@for_predicate(DefaultDict)
class DefaultDictProvider(LoaderProvider, DumperProvider):
    _DICT_PROVIDER = DictProvider()

    def __init__(self, default_factory: Optional[Callable] = None):
        self.default_factory = default_factory

    def _extract_key_value(self, request: LocatedRequest) -> Tuple[BaseNormType, BaseNormType]:
        norm = try_normalize_type(get_type_from_request(request))
        return norm.args

    def _provide_loader(self, mediator: Mediator, request: LoaderRequest) -> Loader:
        key, value = self._extract_key_value(request)
        dict_type_hint = Dict[key.source, value.source]  # type: ignore
        dict_loader = self._DICT_PROVIDER.apply_provider(
            mediator,
            replace(request, loc_stack=request.loc_stack.add_to_last_map(TypeHintLoc(dict_type_hint)))
        )
        default_factory = self.default_factory

        def defaultdict_loader(data):
            return defaultdict(default_factory, dict_loader(data))

        return defaultdict_loader

    def _provide_dumper(self, mediator: Mediator, request: DumperRequest) -> Dumper:
        key, value = self._extract_key_value(request)
        dict_type_hint = Dict[key.source, value.source]  # type: ignore

        return self._DICT_PROVIDER.apply_provider(
            mediator,
            replace(request, loc_stack=request.loc_stack.add_to_last_map(TypeHintLoc(dict_type_hint)))
        )
