from dataclasses import dataclass, field

from dataclass_factory_30.core import BaseFactory, Provider, ProvisionCtx


@dataclass(frozen=True)
class BuiltinFactory(BaseFactory):
    recipe: list = field(default_factory=list)

    def _ensure_provision_ctx(self, value) -> ProvisionCtx:
        if isinstance(value, type):
            return ProvisionCtx(value)
        if isinstance(value, ProvisionCtx):
            return value
        raise ValueError(f'Can not create ProvisionCtx from {value}')

    def ensure_provider(self, value) -> Provider:
        pass
