from adaptix import Retort
from tests_helpers import PlaceholderProvider


def test_retort_replace():
    retort1 = Retort(debug_path=False)
    replaced_retort1 = retort1.replace(debug_path=True)

    assert replaced_retort1._debug_path is True
    assert not replaced_retort1._loader_cache and not replaced_retort1._dumper_cache

    retort2 = Retort(strict_coercion=False)
    replaced_retort2 = retort2.replace(strict_coercion=True)

    assert replaced_retort2._strict_coercion is True
    assert not replaced_retort2._loader_cache and not replaced_retort2._dumper_cache


def test_retort_extend():
    retort = Retort(recipe=[PlaceholderProvider(1)])
    recipe_before_extend = tuple(retort._get_full_recipe())
    to_extend = (PlaceholderProvider(2), PlaceholderProvider(3))
    extended_retort = retort.extend(recipe=to_extend)

    assert retort._get_full_recipe() == recipe_before_extend
    assert extended_retort._get_full_recipe()[:len(to_extend)] == to_extend
    assert not extended_retort._loader_cache and not extended_retort._dumper_cache


def test_hashability():
    hash(Retort())
