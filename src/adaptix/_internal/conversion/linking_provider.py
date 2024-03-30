import itertools
from typing import Iterable, Optional, Union

from ..common import Coercer, OneArgCoercer
from ..model_tools.definitions import DefaultFactory, DefaultValue
from ..provider.essential import CannotProvide, Mediator
from ..provider.loc_stack_filtering import LocStackChecker
from ..provider.location import FieldLoc
from .provider_template import LinkingProvider
from .request_cls import ConstantLinking, FieldLinking, LinkingRequest, LinkingResult, LinkingSource


class DefaultLinkingProvider(LinkingProvider):
    def _provide_linking(self, mediator: Mediator, request: LinkingRequest) -> LinkingResult:
        target_field_id = request.destination.last.cast(FieldLoc).field_id

        for source in self._iterate_sources(request):
            if source.last.cast(FieldLoc).field_id == target_field_id:
                return LinkingResult(
                    linking=FieldLinking(source=source, coercer=None),
                )
        raise CannotProvide

    def _iterate_sources(self, request: LinkingRequest) -> Iterable[LinkingSource]:
        if len(request.destination) == 2:  # noqa: PLR2004
            yield from reversed(request.context.loc_stacks)
        yield from request.sources


class MatchingLinkingProvider(LinkingProvider):
    def __init__(self, src_lsc: LocStackChecker, dst_lsc: LocStackChecker, coercer: Optional[OneArgCoercer]):
        self._src_lsc = src_lsc
        self._dst_lsc = dst_lsc
        self._one_arg_coercer = coercer

    def _get_coercer(self) -> Optional[Coercer]:
        one_arg_coercer = self._one_arg_coercer
        if one_arg_coercer is None:
            return None
        return lambda x, ctx: one_arg_coercer(x)

    def _provide_linking(self, mediator: Mediator, request: LinkingRequest) -> LinkingResult:
        if not self._dst_lsc.check_loc_stack(mediator, request.destination):
            raise CannotProvide

        for source in itertools.chain(request.sources, reversed(request.context.loc_stacks)):
            if self._src_lsc.check_loc_stack(mediator, source):
                return LinkingResult(linking=FieldLinking(source=source, coercer=self._get_coercer()))
        raise CannotProvide


class ConstantLinkingProvider(LinkingProvider):
    def __init__(self, dst_lsc: LocStackChecker, default: Union[DefaultValue, DefaultFactory]):
        self._dst_lsc = dst_lsc
        self._default = default

    def _provide_linking(self, mediator: Mediator, request: LinkingRequest) -> LinkingResult:
        if self._dst_lsc.check_loc_stack(mediator, request.destination):
            return LinkingResult(linking=ConstantLinking(self._default))
        raise CannotProvide
