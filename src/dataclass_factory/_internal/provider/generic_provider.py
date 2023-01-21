import collections.abc
from abc import ABC
from dataclasses import dataclass, replace
from enum import EnumMeta, Flag
from inspect import isabstract
from typing import Callable, Collection, Container, Dict, Iterable, Literal, Mapping, Tuple, Union

from ..common import Dumper, Loader, TypeHint
from ..load_error import BadVariantError, ExcludedTypeLoadError, LoadError, MsgError, TypeLoadError, UnionLoadError
from ..struct_path import append_path
from ..type_tools import BaseNormType, is_new_type, is_subclass_soft, normalize_type, strip_tags
from .essential import CannotProvide, Mediator, Request
from .provider_template import DumperProvider, LoaderProvider, for_origin
from .request_cls import (
    DumperRequest,
    LoaderRequest,
    LocatedRequest,
    TypeHintLocation,
    get_type_from_request,
    replace_type,
)
from .static_provider import StaticProvider, static_provision_action


def stub(arg):
    return arg


class NewTypeUnwrappingProvider(StaticProvider):
    @static_provision_action
    def _provide_unwrapping(self, mediator: Mediator, request: LocatedRequest) -> Loader:
        if not isinstance(request.loc, TypeHintLocation):
            raise CannotProvide
        if not is_new_type(request.loc.type):
            raise CannotProvide

        return mediator.provide(
            replace(request, loc=replace(request.loc, type=request.loc.type.__supertype__))
        )


class TypeHintTagsUnwrappingProvider(StaticProvider):
    @static_provision_action
    def _provide_unwrapping(self, mediator: Mediator, request: LocatedRequest) -> Loader:
        if not isinstance(request.loc, TypeHintLocation):
            raise CannotProvide
        unwrapped = strip_tags(normalize_type(request.loc.type))
        if unwrapped.source == request.loc.type:  # type has not changed, continue search
            raise CannotProvide

        return mediator.provide(
            replace(request, loc=replace(request.loc, type=unwrapped))
        )


def _is_exact_zero_or_one(arg):
    return type(arg) == int and arg in (0, 1)  # pylint: disable=unidiomatic-typecheck


@dataclass
@for_origin(Literal)
class LiteralProvider(LoaderProvider, DumperProvider):
    tuple_size_limit: int = 4

    def _get_container(self, args: Collection) -> Container:
        if len(args) > self.tuple_size_limit:
            return set(args)
        return tuple(args)

    def _provide_loader(self, mediator: Mediator, request: LoaderRequest) -> Loader:
        norm = normalize_type(get_type_from_request(request))

        # TODO: add support for enum
        if request.strict_coercion and any(
            isinstance(arg, bool) or _is_exact_zero_or_one(arg)
            for arg in norm.args
        ):
            allowed_values = self._get_container(
                [(type(el), el) for el in norm.args]
            )

            # since True == 1 and False == 0
            def literal_loader_sc(data):
                if (type(data), data) in allowed_values:
                    return data
                raise LoadError

            return literal_loader_sc

        allowed_values = self._get_container(norm.args)

        def literal_loader(data):
            if data in allowed_values:
                return data
            raise LoadError

        return literal_loader

    def _provide_dumper(self, mediator: Mediator, request: DumperRequest) -> Dumper:
        return stub


@for_origin(Union)
class UnionProvider(LoaderProvider, DumperProvider):
    def _provide_loader(self, mediator: Mediator, request: LoaderRequest) -> Loader:
        norm = normalize_type(get_type_from_request(request))

        loaders = tuple(
            mediator.provide(replace_type(request, tp.source))
            for tp in norm.args
        )

        if request.debug_path:
            return self._get_loader_dp(loaders)

        return self._get_loader_non_dp(loaders)

    def _get_loader_dp(self, loader_iter: Iterable[Loader]) -> Loader:
        def union_loader_dp(data):
            errors = []
            for loader in loader_iter:
                try:
                    return loader(data)
                except LoadError as e:
                    errors.append(e)

            raise UnionLoadError(errors)

        return union_loader_dp

    def _get_loader_non_dp(self, loader_iter: Iterable[Loader]) -> Loader:
        def union_loader(data):
            for loader in loader_iter:
                try:
                    return loader(data)
                except LoadError:
                    pass
            raise LoadError

        return union_loader

    def _is_single_optional(self, norm: BaseNormType) -> bool:
        return len(norm.args) == 2 and None in [case.origin for case in norm.args]

    def _is_class_origin(self, origin) -> bool:
        return (origin is None or isinstance(origin, type)) and not is_subclass_soft(origin, collections.abc.Callable)

    def _provide_dumper(self, mediator: Mediator, request: DumperRequest) -> Dumper:
        request_type = get_type_from_request(request)
        norm = normalize_type(request_type)

        # TODO: allow use Literal[..., None] with non single optional

        if self._is_single_optional(norm):
            non_optional = next(case for case in norm.args if case.origin is not None)
            non_optional_dumper = mediator.provide(replace_type(request, non_optional.source))
            return self._get_single_optional_dumper(non_optional_dumper)

        non_class_origins = [case.source for case in norm.args if not self._is_class_origin(case.origin)]
        if non_class_origins:
            raise ValueError(
                f"Can not create dumper for {request_type}."
                f" All cases of union must be class, but found {non_class_origins}"
            )

        dumpers = tuple(
            mediator.provide(replace_type(request, tp.source))
            for tp in norm.args
        )

        dumper_type_map = {case.origin: dumper for case, dumper in zip(norm.args, dumpers)}
        return self._get_dumper(dumper_type_map)

    def _get_dumper(self, dumper_type_map: Mapping[type, Dumper]) -> Dumper:
        def union_dumper(data):
            return dumper_type_map[type(data)](data)

        return union_dumper

    def _get_single_optional_dumper(self, dumper: Dumper) -> Dumper:
        def union_so_dumper(data):
            if data is None:
                return None
            return dumper(data)

        return union_so_dumper


CollectionsMapping = collections.abc.Mapping


@for_origin(Iterable)
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
        arg_loader = mediator.provide(replace_type(request, arg))
        return self._make_loader(request, iter_factory, arg_loader)

    def _create_debug_path_iter_mapper(self, converter):
        def iter_mapper(iterable):
            idx = 0

            for el in iterable:
                try:
                    yield converter(el)
                except Exception as e:
                    append_path(e, idx)
                    raise e

                idx += 1

        return iter_mapper

    def _make_loader(self, request: LoaderRequest, iter_factory, arg_loader):
        if request.debug_path:
            iter_mapper = self._create_debug_path_iter_mapper(arg_loader)

            if request.strict_coercion:
                return self._get_dp_sc_loader(iter_factory, iter_mapper)

            return self._get_dp_non_sc_loader(iter_factory, iter_mapper)

        if request.strict_coercion:
            return self._get_non_dp_sc_loader(iter_factory, arg_loader)

        return self._get_non_dp_non_sc_loader(iter_factory, arg_loader)

    def _get_dp_non_sc_loader(self, iter_factory, iter_mapper):
        def iter_loader_dp(value):
            try:
                value_iter = iter(value)
            except TypeError:
                raise TypeLoadError(Iterable)

            return iter_factory(iter_mapper(value_iter))

        return iter_loader_dp

    def _get_dp_sc_loader(self, iter_factory, iter_mapper):
        def iter_loader_dp_sc(value):
            if isinstance(value, CollectionsMapping):
                raise ExcludedTypeLoadError(Mapping)

            try:
                value_iter = iter(value)
            except TypeError:
                raise TypeLoadError(Iterable)

            return iter_factory(iter_mapper(value_iter))

        return iter_loader_dp_sc

    def _get_non_dp_sc_loader(self, iter_factory, arg_loader):
        def iter_loader_sc(value):
            if isinstance(value, CollectionsMapping):
                raise ExcludedTypeLoadError(Mapping)

            try:
                map_iter = map(arg_loader, value)
            except TypeError:
                raise TypeLoadError(Iterable)

            return iter_factory(map_iter)

        return iter_loader_sc

    def _get_non_dp_non_sc_loader(self, iter_factory, arg_loader):
        def iter_loader(value):
            try:
                map_iter = map(arg_loader, value)
            except TypeError:
                raise TypeLoadError(Iterable)

            return iter_factory(map_iter)

        return iter_loader

    def _provide_dumper(self, mediator: Mediator, request: DumperRequest) -> Dumper:
        norm, arg = self._fetch_norm_and_arg(request)

        iter_factory = self._get_iter_factory(norm.origin)
        arg_dumper = mediator.provide(replace_type(request, arg))
        return self._make_dumper(request, iter_factory, arg_dumper)

    def _make_dumper(self, request: DumperRequest, iter_factory, arg_dumper):
        if request.debug_path:
            iter_mapper = self._create_debug_path_iter_mapper(arg_dumper)
            return self._get_dp_dumper(iter_factory, iter_mapper)

        return self._get_non_dp_dumper(iter_factory, arg_dumper)

    def _get_dp_dumper(self, iter_factory, iter_mapper):
        def iter_dp_dumper(data):
            return iter_factory(iter_mapper(data))

        return iter_dp_dumper

    def _get_non_dp_dumper(self, iter_factory, arg_dumper: Dumper):
        def iter_dumper(data):
            return iter_factory(map(arg_dumper, data))

        return iter_dumper


@for_origin(Dict)
class DictProvider(LoaderProvider, DumperProvider):
    def _extract_key_value(self, request: LocatedRequest) -> Tuple[BaseNormType, BaseNormType]:
        norm = normalize_type(get_type_from_request(request))
        return norm.args  # type: ignore

    def _provide_loader(self, mediator: Mediator, request: LoaderRequest) -> Loader:
        key, value = self._extract_key_value(request)

        key_loader = mediator.provide(
            replace_type(request, key.source),
        )

        value_loader = mediator.provide(
            replace_type(request, value.source),
        )

        return self._make_loader(request, key_loader=key_loader, value_loader=value_loader)

    def _make_loader(self, request: LoaderRequest, key_loader: Loader, value_loader: Loader):
        if request.debug_path:
            return self._get_loader_dp(
                key_loader=key_loader,
                value_loader=value_loader,
            )

        return self._get_loader_non_dp(
            key_loader=key_loader,
            value_loader=value_loader,
        )

    def _get_loader_dp(self, key_loader: Loader, value_loader: Loader):
        def dict_loader_dp(data):
            try:
                items_method = data.items
            except AttributeError:
                raise TypeLoadError(CollectionsMapping)

            result = {}
            for k, v in items_method():
                try:
                    loaded_key = key_loader(k)
                    loaded_value = value_loader(v)
                except Exception as e:
                    append_path(e, k)
                    raise e

                result[loaded_key] = loaded_value

            return result

        return dict_loader_dp

    def _get_loader_non_dp(self, key_loader: Loader, value_loader: Loader):
        def dict_loader(data):
            try:
                items_method = data.items
            except AttributeError:
                raise TypeLoadError(CollectionsMapping)

            result = {}
            for k, v in items_method():
                result[key_loader(k)] = value_loader(v)

            return result

        return dict_loader

    def _provide_dumper(self, mediator: Mediator, request: DumperRequest) -> Dumper:
        key, value = self._extract_key_value(request)

        key_dumper = mediator.provide(
            replace_type(request, key.source),
        )

        value_dumper = mediator.provide(
            replace_type(request, value.source),
        )

        return self._make_dumper(request, key_dumper=key_dumper, value_dumper=value_dumper)

    def _make_dumper(self, request: DumperRequest, key_dumper: Dumper, value_dumper: Dumper):
        if request.debug_path:
            return self._get_dumper_dp(
                key_dumper=key_dumper,
                value_dumper=value_dumper,
            )

        return self._get_dumper_non_dp(
            key_dumper=key_dumper,
            value_dumper=value_dumper,
        )

    def _get_dumper_dp(self, key_dumper, value_dumper):
        def dict_dumper_dp(data: Mapping):
            result = {}
            for k, v in data.items():
                try:
                    result[key_dumper(k)] = value_dumper(v)
                except Exception as e:
                    append_path(e, k)
                    raise e

            return result

        return dict_dumper_dp

    def _get_dumper_non_dp(self, key_dumper, value_dumper):
        def dict_dumper(data: Mapping):
            result = {}
            for k, v in data.items():
                result[key_dumper(k)] = value_dumper(v)

            return result

        return dict_dumper


class BaseEnumProvider(LoaderProvider, DumperProvider, ABC):
    def _check_request(self, mediator: Mediator, request: Request) -> None:
        if not isinstance(request, LocatedRequest):
            raise CannotProvide

        norm = normalize_type(get_type_from_request(request))

        if not isinstance(norm.origin, EnumMeta):
            raise CannotProvide


def _enum_name_dumper(data):
    return data.name


class EnumNameProvider(BaseEnumProvider):
    """This provider represents enum members to the outside world by their name"""

    def _provide_loader(self, mediator: Mediator, request: LoaderRequest) -> Loader:
        enum = get_type_from_request(request)

        if issubclass(enum, Flag):
            raise ValueError(f"Can not use {type(self).__name__} with Flag subclass {enum}")

        variants = [case.name for case in enum]

        def enum_loader(data):
            try:
                return enum[data]
            except KeyError:
                raise BadVariantError(variants)
            except TypeError:
                raise BadVariantError(variants)

        return enum_loader

    def _provide_dumper(self, mediator: Mediator, request: DumperRequest) -> Dumper:
        return _enum_name_dumper


class EnumValueProvider(BaseEnumProvider):
    """This provider represents enum members to the outside world by their value.
    Input data will be loaded and then interpreted as one of enum member value.
    At serializing value of enum member will be dumped.
    """

    def __init__(self, value_type: TypeHint):
        """Create value provider for Enum.

        :param value_type: Type of enum member value
            that will be used to create loader and dumper of member value
        """
        self._value_type = value_type

    def _provide_loader(self, mediator: Mediator, request: LoaderRequest) -> Loader:
        enum = get_type_from_request(request)
        value_loader = mediator.provide(replace_type(request, self._value_type))

        def enum_loader(data):
            loaded_value = value_loader(data)
            try:
                return enum(loaded_value)
            except ValueError:
                raise MsgError("Bad enum value")

        return enum_loader

    def _provide_dumper(self, mediator: Mediator, request: DumperRequest) -> Dumper:
        value_dumper = mediator.provide(replace_type(request, self._value_type))

        def enum_dumper(data):
            return value_dumper(data.value)

        return enum_dumper


def _enum_exact_value_dumper(data):
    return data.value


class EnumExactValueProvider(BaseEnumProvider):
    """This provider represents enum members to the outside world
    by their value without any processing
    """

    def _provide_loader(self, mediator: Mediator, request: LoaderRequest) -> Loader:
        enum = get_type_from_request(request)
        variants = [case.value for case in enum]

        def enum_exact_loader(data):
            # since MyEnum(MyEnum.MY_CASE) == MyEnum.MY_CASE
            if isinstance(data, enum):
                raise BadVariantError(variants)

            try:
                return enum(data)
            except ValueError:
                raise BadVariantError(variants)

        return enum_exact_loader

    def _provide_dumper(self, mediator: Mediator, request: DumperRequest) -> Dumper:
        return _enum_exact_value_dumper
