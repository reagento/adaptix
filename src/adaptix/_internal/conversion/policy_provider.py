from ..provider.essential import Mediator
from ..provider.static_provider import StaticProvider, static_provision_action
from .request_cls import UnlinkedOptionalPolicy, UnlinkedOptionalPolicyRequest


class UnlinkedOptionalPolicyProvider(StaticProvider):
    def __init__(self, is_allowed: bool):
        self._is_allowed = is_allowed

    @static_provision_action
    def _unlinked_optional_policy(
        self,
        mediator: Mediator,
        request: UnlinkedOptionalPolicyRequest,
    ) -> UnlinkedOptionalPolicy:
        return UnlinkedOptionalPolicy(is_allowed=self._is_allowed)
