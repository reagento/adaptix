from ..provider.essential import Mediator
from ..provider.static_provider import StaticProvider, static_provision_action
from .request_cls import UnboundOptionalPolicy, UnboundOptionalPolicyRequest


class UnboundOptionalPolicyProvider(StaticProvider):
    def __init__(self, is_allowed: bool):
        self._is_allowed = is_allowed

    @static_provision_action
    def _outer_unbound_optional_policy(
        self,
        mediator: Mediator,
        request: UnboundOptionalPolicyRequest,
    ) -> UnboundOptionalPolicy:
        return UnboundOptionalPolicy(is_allowed=self._is_allowed)
