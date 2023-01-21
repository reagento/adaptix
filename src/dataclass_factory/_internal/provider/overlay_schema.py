from dataclasses import dataclass, fields, replace
from typing import Any, Callable, ClassVar, Generic, Iterable, Mapping, Optional, Type, TypeVar

from ..utils import ClassDispatcher, Omitted
from .essential import CannotProvide, Mediator
from .provider_basics import Chain
from .request_cls import LocatedRequest, Location, TypeHintLocation
from .static_provider import StaticProvider, static_provision_action


@dataclass
class Schema:
    pass


Sc = TypeVar('Sc', bound=Schema)
Ov = TypeVar('Ov', bound='Overlay')

Merger = Callable[[Any, Any, Any], Any]


@dataclass
class Overlay(Generic[Sc]):
    _schema_cls: ClassVar[Type[Schema]]  # ClassVar can not contain TypeVar
    _mergers: ClassVar[Optional[Mapping[str, Merger]]]

    def __init_subclass__(cls, *args, **kwargs):
        cls._schema_cls = cls.__orig_bases__[0].__args__[0]  # type: ignore[attr-defined]  # pylint: disable=no-member
        cls._mergers = None

    def _default_merge(self, old: Any, new: Any) -> Any:
        return new

    def _is_omitted(self, value: Any) -> bool:
        return value is Omitted()

    @classmethod
    def _load_mergers(cls) -> Mapping[str, Merger]:
        if cls._mergers is None:
            cls._mergers = {
                field.name: getattr(cls, f'_merge_{field.name}', cls._default_merge)
                for field in fields(cls)
            }
        return cls._mergers

    def merge(self: Ov, new: Ov) -> Ov:
        merged = {}
        for field_name, merger in self._load_mergers().items():
            old_field_value = getattr(self, field_name)
            new_field_value = getattr(new, field_name)
            if self._is_omitted(old_field_value):
                merged[field_name] = new_field_value
            elif self._is_omitted(new_field_value):
                merged[field_name] = old_field_value
            else:
                merged[field_name] = merger(self, old_field_value, new_field_value)
        return self.__class__(**merged)

    def to_schema(self) -> Sc:
        omitted_fields = [
            field_name for field_name, field_value in vars(self).items()
            if self._is_omitted(field_value)
        ]
        if omitted_fields:
            raise ValueError(
                f"Can not create schema because overlay contains omitted values at {omitted_fields}"
            )
        # noinspection PyArgumentList
        return self._schema_cls(**vars(self))  # type: ignore[return-value]


@dataclass(frozen=True)
class OverlayRequest(LocatedRequest[Ov], Generic[Ov]):
    overlay_cls: Type[Ov]


def provide_schema(overlay: Type[Overlay[Sc]], mediator: Mediator, loc: Location) -> Sc:
    stacked_overlay = mediator.provide(
        OverlayRequest(
            loc=loc,
            overlay_cls=overlay,
        )
    )
    if isinstance(loc, TypeHintLocation) and isinstance(loc.type, type):
        for parent in loc.type.mro()[1:]:
            try:
                new_overlay = mediator.provide(
                    OverlayRequest(
                        loc=replace(loc, type=parent),
                        overlay_cls=overlay,
                    )
                )
            except CannotProvide:
                pass
            else:
                stacked_overlay = new_overlay.merge(stacked_overlay)
    return stacked_overlay.to_schema()


class OverlayProvider(StaticProvider):
    def __init__(self, overlays: Iterable[Overlay], chain: Optional[Chain]):
        self._chain = chain
        self._overlays = overlays
        self._dispatcher = ClassDispatcher({type(overlay): overlay for overlay in overlays})

    @static_provision_action
    def _provide_overlay(self, mediator: Mediator, request: OverlayRequest):
        try:
            overlay = self._dispatcher.dispatch(request.overlay_cls)
        except KeyError:
            raise CannotProvide

        if self._chain is None:
            return overlay

        try:
            next_overlay = mediator.provide_from_next()
        except CannotProvide:
            return overlay

        if self._chain == Chain.FIRST:
            return next_overlay.merge(overlay)
        return overlay.merge(next_overlay)
