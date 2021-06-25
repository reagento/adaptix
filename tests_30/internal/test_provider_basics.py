import pytest

from dataclass_factory_30.core import Provider, provision_action, ProvisionCtx, BaseFactory, _get_provider_tmpl_pam


def test_several_provision_action_def():
    with pytest.raises(ValueError):
        class TestProvider(Provider):
            @provision_action
            def _provide_test1(self, factory: 'BaseFactory', offset: int, ctx: ProvisionCtx) -> int:
                pass

            @provision_action
            def _provide_test2(self, factory: 'BaseFactory', offset: int, ctx: ProvisionCtx) -> int:
                pass


def test_inheritance_with_several_provision_action():
    with pytest.raises(ValueError):
        class TestProvider(Provider):
            @provision_action
            def _provide_test1(self, factory: 'BaseFactory', offset: int, ctx: ProvisionCtx) -> int:
                pass

        class TestProviderChild(TestProvider):
            @provision_action
            def _provide_test2(self, factory: 'BaseFactory', offset: int, ctx: ProvisionCtx) -> int:
                pass


def test_pam_resolution():
    with pytest.raises(ValueError):
        class TestProvider1(Provider):
            @provision_action
            def _provide_test1(self, factory: 'BaseFactory', offset: int, ctx: ProvisionCtx) -> int:
                pass

        assert _get_provider_tmpl_pam(TestProvider1) == '_provide_test1'

        class TestProvider2(Provider):
            @provision_action
            def _provide_test2(self, factory: 'BaseFactory', offset: int, ctx: ProvisionCtx) -> int:
                pass

        assert _get_provider_tmpl_pam(TestProvider2) == '_provide_test2'

        class TestProviderChild1(TestProvider1):
            pass

        assert _get_provider_tmpl_pam(TestProviderChild1) == '_provide_test1'

        class TestProviderChild12(TestProvider1, TestProvider2):
            pass

        assert _get_provider_tmpl_pam(TestProviderChild12) is None

        class TestProviderChild12Child(TestProviderChild12):
            pass

        assert _get_provider_tmpl_pam(TestProviderChild12Child) is None

