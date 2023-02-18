from adaptix._internal.provider.essential import CannotProvide, Mediator, Provider, Request
from adaptix._internal.provider.model.crown_definitions import (
    ExtraCollect,
    Extractor,
    ExtraForbid,
    ExtraKwargs,
    ExtraSkip,
    Saturator,
)
from adaptix._internal.provider.name_layout.base import ExtraIn, ExtraOut
from adaptix._internal.provider.name_layout.component import NameMapStack, RawKey, RawPath
from adaptix._internal.provider.name_style import NameStyle
from adaptix._internal.provider.provider_basics import Chain
from adaptix._internal.provider.request_filtering import P, create_request_checker, match_origin
