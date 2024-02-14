import collections.abc
from dataclasses import dataclass, replace
from enum import Enum
from os import PathLike
from pathlib import Path
from typing import Any, Collection, Dict, Iterable, Literal, Sequence, Set, Type, Union

from ..common import Dumper, Loader
from ..compat import CompatExceptionGroup
from ..datastructures import ClassDispatcher
from ..definitions import DebugTrail
from ..feature_requirement import HAS_PY_39
from ..provider.essential import CannotProvide, Mediator
from ..provider.provider_template import for_predicate
from ..provider.request_cls import (
    DebugTrailRequest,
    GenericParamLoc,
    LocatedRequest,
    LocMap,
    LocStack,
    StrictCoercionRequest,
    TypeHintLoc,
    get_type_from_request,
    try_normalize_type,
)
from ..provider.static_provider import StaticProvider, static_provision_action
from ..special_cases_optimization import as_is_stub
from ..type_tools import BaseNormType, NormTypeAlias, is_new_type, is_subclass_soft, strip_tags
from ..type_tools.norm_utils import strip_annotated
from .load_error import BadVariantLoadError, LoadError, TypeLoadError, UnionLoadError
from .provider_template import DumperProvider, LoaderProvider
from .request_cls import DumperRequest, LoaderRequest


class NewTypeUnwrappingProvider(StaticProvider):
    @static_provision_action
    def _provide_unwrapping(self, mediator: Mediator, request: LocatedRequest) -> Loader:
        loc = request.last_map.get_or_raise(TypeHintLoc, CannotProvide)

        if not is_new_type(loc.type):
            raise CannotProvide

        return mediator.delegating_provide(
            replace(
                request,
                loc_stack=request.loc_stack.add_to_last_map(TypeHintLoc(type=loc.type.__supertype__))
            ),
        )


class TypeHintTagsUnwrappingProvider(StaticProvider):
    @static_provision_action
    def _provide_unwrapping(self, mediator: Mediator, request: LocatedRequest) -> Loader:
        loc = request.last_map.get_or_raise(TypeHintLoc, CannotProvide)
        norm = try_normalize_type(loc.type)
        unwrapped = strip_tags(norm)
        if unwrapped.source == loc.type:  # type has not changed, continue search
            raise CannotProvide

        return mediator.delegating_provide(
            replace(
                request,
                loc_stack=request.loc_stack.add_to_last_map(TypeHintLoc(type=unwrapped.source))
            ),
        )


class TypeAliasUnwrappingProvider(StaticProvider):
    @static_provision_action
    def _provide_unwrapping(self, mediator: Mediator, request: LocatedRequest) -> Loader:
        loc = request.last_map.get_or_raise(TypeHintLoc, CannotProvide)
        norm = try_normalize_type(loc.type)
        if not isinstance(norm, NormTypeAlias):
            raise CannotProvide

        if norm.args:
            unwrapped = norm.value[tuple(arg.source for arg in norm.args)]
        else:
            unwrapped = norm.value

        return mediator.delegating_provide(
            replace(
                request,
                loc_stack=request.loc_stack.add_to_last_map(TypeHintLoc(type=unwrapped))
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

    def _get_allowed_values_repr(self, args: Collection, mediator: Mediator, loc_stack: LocStack) -> Collection:
        enum_cases = [arg for arg in args if isinstance(arg, Enum)]
        if not enum_cases:
            return set(args)

        literal_dumper = self._provide_dumper(mediator, DumperRequest(loc_stack))
        return {literal_dumper(arg) if isinstance(arg, Enum) else arg for arg in args}

    def _get_enum_types(self, cases: Collection) -> Collection:
        seen: Set[Type[Enum]] = set()
        enum_types = []
        for case in cases:
            case_type = type(case)
            if case_type not in seen:
                enum_types.append(case_type)
                seen.add(case_type)
        return enum_types

    def _fetch_enum_loaders(
        self, mediator: Mediator, request: LoaderRequest, enum_classes: Iterable[Type[Enum]]
    ) -> Iterable[Loader[Enum]]:
        requests = [
            LoaderRequest(
                loc_stack=request.loc_stack.append_with(
                    LocMap(
                        TypeHintLoc(type=enum_cls),
                    )
                )
            ) for enum_cls in enum_classes
        ]
        return mediator.mandatory_provide_by_iterable(
            requests,
            lambda: 'Cannot create loaders for enum. Loader for literal cannot be created',
        )

    def _fetch_enum_dumpers(
        self, mediator: Mediator, request: DumperRequest, enum_classes: Iterable[Type[Enum]]
    ) -> Dict[Type[Enum], Dumper[Enum]]:
        requests = [
            DumperRequest(
                loc_stack=request.loc_stack.append_with(
                    LocMap(
                        TypeHintLoc(type=enum_cls),
                    )
                )
            ) for enum_cls in enum_classes
        ]
        dumpers = mediator.mandatory_provide_by_iterable(
            requests,
            lambda: 'Cannot create loaders for enum. Loader for literal cannot be created',
        )
        return dict(zip(enum_classes, dumpers))

    def _get_literal_loader_with_enum(  # noqa: CCR001
        self, basic_loader: Loader, enum_loaders: Sequence[Loader[Enum]], allowed_values: Collection
    ) -> Loader:
        if not enum_loaders:
            return basic_loader

        if len(enum_loaders) == 1:
            enum_loader = enum_loaders[0]

            def wrapped_loader_with_single_enum(data):
                try:
                    enum_value = enum_loader(data)
                except LoadError:
                    pass
                else:
                    if enum_value in allowed_values:
                        return enum_value
                return basic_loader(data)

            return wrapped_loader_with_single_enum

        def wrapped_loader_with_enums(data):
            for loader in enum_loaders:
                try:
                    enum_value = loader(data)
                except LoadError:
                    pass
                else:
                    if enum_value in allowed_values:
                        return enum_value
            return basic_loader(data)

        return wrapped_loader_with_enums

    def _provide_loader(self, mediator: Mediator, request: LoaderRequest) -> Loader:
        norm = try_normalize_type(get_type_from_request(request))
        strict_coercion = mediator.mandatory_provide(StrictCoercionRequest(loc_stack=request.loc_stack))

        cleaned_args = [strip_annotated(arg) for arg in norm.args]

        enum_cases = [arg for arg in cleaned_args if isinstance(arg, Enum)]
        enum_loaders = list(self._fetch_enum_loaders(mediator, request, self._get_enum_types(enum_cases)))
        allowed_values_repr = self._get_allowed_values_repr(cleaned_args, mediator, request.loc_stack)

        if strict_coercion and any(
            isinstance(arg, bool) or _is_exact_zero_or_one(arg)
            for arg in cleaned_args
        ):
            allowed_values_with_types = self._get_allowed_values_collection(
                [(type(el), el) for el in cleaned_args]
            )

            # since True == 1 and False == 0
            def literal_loader_sc(data):
                if (type(data), data) in allowed_values_with_types:
                    return data
                raise BadVariantLoadError(allowed_values_repr, data)

            return self._get_literal_loader_with_enum(
                literal_loader_sc, enum_loaders, allowed_values_with_types
            )

        allowed_values = self._get_allowed_values_collection(cleaned_args)

        def literal_loader(data):
            if data in allowed_values:
                return data
            raise BadVariantLoadError(allowed_values_repr, data)

        return self._get_literal_loader_with_enum(literal_loader, enum_loaders, allowed_values)

    def _provide_dumper(self, mediator: Mediator, request: DumperRequest) -> Dumper:
        norm = try_normalize_type(get_type_from_request(request))
        cleaned_args = [strip_annotated(arg) for arg in norm.args]
        enum_cases = [arg for arg in cleaned_args if isinstance(arg, Enum)]

        if not enum_cases:
            return as_is_stub

        enum_dumpers = self._fetch_enum_dumpers(mediator, request, self._get_enum_types(enum_cases))

        if len(enum_dumpers) == 1:
            enum_dumper = list(enum_dumpers.values())[0]

            def literal_dumper_with_single_enum(data):
                if isinstance(data, Enum):
                    return enum_dumper(data)
                return data

            return literal_dumper_with_single_enum

        def literal_dumper_with_enums(data):
            if isinstance(data, Enum):
                return enum_dumpers[type(data)](data)
            return data

        return literal_dumper_with_enums


@for_predicate(Union)
class UnionProvider(LoaderProvider, DumperProvider):
    def _provide_loader(self, mediator: Mediator, request: LoaderRequest) -> Loader:
        norm = try_normalize_type(get_type_from_request(request))
        debug_trail = mediator.mandatory_provide(DebugTrailRequest(loc_stack=request.loc_stack))

        if self._is_single_optional(norm):
            not_none = next(case for case in norm.args if case.origin is not None)
            not_none_loader = mediator.mandatory_provide(
                LoaderRequest(
                    loc_stack=request.loc_stack.append_with(
                        LocMap(
                            TypeHintLoc(type=not_none.source),
                            GenericParamLoc(generic_pos=0),
                        )
                    )
                ),
                lambda x: 'Cannot create loader for union. Loaders for some union cases cannot be created',
            )
            if debug_trail in (DebugTrail.ALL, DebugTrail.FIRST):
                return self._single_optional_dt_loader(norm.source, not_none_loader)
            if debug_trail == DebugTrail.DISABLE:
                return self._single_optional_dt_disable_loader(not_none_loader)
            raise ValueError

        loaders = mediator.mandatory_provide_by_iterable(
            [
                LoaderRequest(
                    loc_stack=request.loc_stack.append_with(
                        LocMap(
                            TypeHintLoc(type=tp.source),
                            GenericParamLoc(generic_pos=i),
                        )
                    )
                )
                for i, tp in enumerate(norm.args)
            ],
            lambda: 'Cannot create loader for union. Loaders for some union cases cannot be created',
        )
        if debug_trail == DebugTrail.DISABLE:
            return self._get_loader_dt_disable(tuple(loaders))
        if debug_trail == DebugTrail.FIRST:
            return self._get_loader_dt_first(norm.source, tuple(loaders))
        if debug_trail == DebugTrail.ALL:
            return self._get_loader_dt_all(norm.source, tuple(loaders))
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
        norm = try_normalize_type(request_type)

        # TODO: allow use Literal[..., None] with non single optional

        if self._is_single_optional(norm):
            not_none = next(case for case in norm.args if case.origin is not None)
            not_none_dumper = mediator.mandatory_provide(
                DumperRequest(
                    loc_stack=request.loc_stack.append_with(
                        LocMap(
                            TypeHintLoc(type=not_none.source),
                            GenericParamLoc(generic_pos=0),
                        )
                    )
                ),
                lambda x: 'Cannot create dumper for union. Dumpers for some union cases cannot be created',
            )
            if not_none_dumper == as_is_stub:
                return as_is_stub
            return self._get_single_optional_dumper(not_none_dumper)

        non_class_origins = [case.source for case in norm.args if not self._is_class_origin(case.origin)]
        if non_class_origins:
            raise CannotProvide(
                f"All cases of union must be class, but found {non_class_origins}",
                is_terminal=True,
                is_demonstrative=True,
            )

        dumpers = mediator.mandatory_provide_by_iterable(
            [
                DumperRequest(
                    loc_stack=request.loc_stack.append_with(
                        LocMap(
                            TypeHintLoc(type=tp.source),
                            GenericParamLoc(generic_pos=i),
                        )
                    )
                )
                for i, tp in enumerate(norm.args)
            ],
            lambda: 'Cannot create dumper for union. Dumpers for some union cases cannot be created',
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


def path_like_dumper(data):
    return data.__fspath__()  # pylint: disable=unnecessary-dunder-call


@for_predicate(PathLike[str] if HAS_PY_39 else PathLike)
class PathLikeProvider(LoaderProvider, DumperProvider):
    _impl = Path

    def _provide_loader(self, mediator: Mediator, request: LoaderRequest) -> Loader:
        return mediator.mandatory_provide(
            LoaderRequest(
                loc_stack=request.loc_stack.add_to_last_map(TypeHintLoc(type=self._impl))
            ),
            lambda x: f'Cannot create loader for {PathLike}. Loader for {Path} cannot be created',
        )

    def _provide_dumper(self, mediator: Mediator, request: DumperRequest) -> Dumper:
        return path_like_dumper
