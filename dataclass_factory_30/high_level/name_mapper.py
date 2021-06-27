from dataclasses import dataclass, field
from typing import Optional, List, Dict

from .name_style import NameStyle, convert_snake_style
from ..core import ProvisionCtx, BaseFactory, CannotProvide
from ..low_level.provider import NameMappingProvider
from ..low_level.fields import FieldsProvisionCtx


# TODO: Add support for path in map

@dataclass(frozen=True)
class NameMapper(NameMappingProvider):
    """A NameMapper decides which fields will be presented
    to the outside world and how they will look.

    The mapping process consists of two stages:
    1. Determining which fields are presented
    2. Mutating names of presented fields

    Parameters that are responsible for
    filtering of available have such priority
    1. skip
    2. only | only_mapped
    3. skip_internal

    Fields selected by only and only_mapped are unified.
    Rules with higher priority overlap other rules.

    Mutating parameters works in that way:
    Mapper tries to use the value from the map.
    If the field is not presented in the map,
    trim trailing underscore and convert name style.

    The field must follow snake_case to could be converted.
    """

    skip: List[str] = field(default_factory=list)
    only_mapped: bool = False
    only: Optional[List[str]] = None
    skip_internal: bool = True

    map: Dict[str, str] = field(default_factory=dict)
    trim_trailing_underscore: bool = True
    name_style: Optional[NameStyle] = None

    def _filter(self, name: str) -> Optional[str]:
        if name in self.skip:
            return None

        if self.only_mapped or self.only is not None:
            if self.only_mapped and name in self.map:
                return name

            if self.only is not None and name in self.only:
                return name

            return None

        if self.skip_internal and name.startswith('_'):
            return None

        return name

    def _map_name(self, src_name: str) -> Optional[str]:
        name = self._filter(src_name)
        if name is None:
            return None

        try:
            name = self.map[name]
        except KeyError:
            if self.trim_trailing_underscore:
                name = name.rstrip('_')

            if self.name_style is not None:
                name = convert_snake_style(name, self.name_style)

        return name

    def _provide_name_mapping(self, factory: 'BaseFactory', offset: int, ctx: ProvisionCtx) -> Optional[str]:
        if not isinstance(ctx, FieldsProvisionCtx):
            raise CannotProvide

        return self._map_name(ctx.field_name)

