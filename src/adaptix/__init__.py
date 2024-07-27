from ._internal.common import Dumper, Loader, TypeHint
from ._internal.definitions import DebugTrail
from ._internal.model_tools.introspection.typed_dict import TypedDictAt38Warning
from ._internal.morphing.facade.func import dump, load
from ._internal.morphing.facade.provider import (
    as_is_dumper,
    as_is_loader,
    constructor,
    date_by_timestamp,
    datetime_by_format,
    datetime_by_timestamp,
    default_dict,
    dumper,
    enum_by_exact_value,
    enum_by_name,
    enum_by_value,
    flag_by_exact_value,
    flag_by_member_names,
    loader,
    name_mapping,
    validator,
    with_property,
)
from ._internal.morphing.facade.retort import AdornedRetort, FilledRetort, Retort
from ._internal.morphing.model.crown_definitions import (
    ExtraCollect,
    Extractor,
    ExtraForbid,
    ExtraKwargs,
    ExtraSkip,
    Saturator,
)
from ._internal.morphing.name_layout.base import ExtraIn, ExtraOut
from ._internal.name_style import NameStyle
from ._internal.provider.facade.provider import bound
from ._internal.retort.searching_retort import ProviderNotFoundError
from ._internal.utils import Omittable, Omitted, create_deprecated_alias_getter
from .provider import (
    AggregateCannotProvide,
    CannotProvide,
    Chain,
    LocStackPattern,
    Mediator,
    P,
    Provider,
    Request,
    create_loc_stack_checker,
)

__all__ = (
    "Dumper",
    "Loader",
    "TypeHint",
    "DebugTrail",
    "loader",
    "dumper",
    "as_is_dumper",
    "as_is_loader",
    "constructor",
    "with_property",
    "validator",
    "bound",
    "enum_by_exact_value",
    "enum_by_name",
    "enum_by_value",
    "flag_by_exact_value",
    "flag_by_member_names",
    "name_mapping",
    "default_dict",
    "datetime_by_format",
    "date_by_timestamp",
    "datetime_by_timestamp",
    "AdornedRetort",
    "FilledRetort",
    "Retort",
    "TypedDictAt38Warning",
    "Omittable",
    "Omitted",
    "provider",
    "CannotProvide",
    "AggregateCannotProvide",
    "Chain",
    "ExtraCollect",
    "Extractor",
    "ExtraForbid",
    "ExtraIn",
    "ExtraKwargs",
    "ExtraOut",
    "ExtraSkip",
    "Mediator",
    "NameStyle",
    "LocStackPattern",
    "P",
    "Saturator",
    "create_loc_stack_checker",
    "retort",
    "Provider",
    "Request",
    "load",
    "dump",
)

__getattr__ = create_deprecated_alias_getter(
    __name__,
    {
        "NoSuitableProvider": "ProviderNotFoundError",
    },
)
