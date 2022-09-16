from dataclass_factory_30.facade import Factory
from dataclass_factory_30.provider.model import ExtraForbid, ExtraSkip
from tests_helpers import PlaceholderProvider


def test_factory_replace():
    factory1 = Factory(debug_path=False)
    replaced_factory1 = factory1.replace(debug_path=True)

    assert replaced_factory1._debug_path is True
    assert not replaced_factory1._parser_cache and not replaced_factory1._serializers_cache

    factory2 = Factory(strict_coercion=False)
    replaced_factory2 = factory2.replace(strict_coercion=True)

    assert replaced_factory2._strict_coercion is True
    assert not replaced_factory2._parser_cache and not replaced_factory2._serializers_cache

    factory3 = Factory(extra_policy=ExtraSkip())
    replaced_factory3 = factory3.replace(extra_policy=ExtraForbid())

    assert replaced_factory3._extra_policy is ExtraForbid()
    assert not replaced_factory3._parser_cache and not replaced_factory3._serializers_cache


def test_factory_extend():
    factory = Factory(recipe=[PlaceholderProvider(1)])
    recipt_before_extend = [*factory._inc_instance_recipe]
    to_extend = [PlaceholderProvider(2), PlaceholderProvider(3)]
    extended_factory = factory.extend(recipe=to_extend)

    assert factory._inc_instance_recipe == recipt_before_extend
    assert extended_factory._inc_instance_recipe[:len(to_extend)] == to_extend
    assert not extended_factory._parser_cache and not extended_factory._serializers_cache
