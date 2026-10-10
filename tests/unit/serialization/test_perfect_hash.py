import random

from adaptix._internal.serialization.perfect_hash import PerfectHash


def test_all_names_have_distinct_verified_slots():
    names = [f"field_{index}" for index in range(500)] + ["", "é", "ключ", "😀", 'quote"', "nul\0"]
    table = PerfectHash.build(names + names)
    assert table is not None
    assert sum(value is not None for value in table.entries) == len(names)
    for name in names:
        assert table.lookup(name.encode()) == name


def test_unknown_names_never_alias_known_names():
    table = PerfectHash.build([f"field_{index}" for index in range(128)])
    assert table is not None
    randomizer = random.Random(42)  # noqa: S311
    for _ in range(10000):
        unknown = randomizer.randbytes(randomizer.randrange(30))
        assert table.lookup(unknown) is None


def test_empty_schema_does_not_allocate_a_table():
    assert PerfectHash.build([]) is None


def test_unrepresentable_or_adversarial_names_use_general_decoder(monkeypatch):
    assert PerfectHash.build(["\ud800"]) is None
    monkeypatch.setattr("adaptix._internal.serialization.perfect_hash.hash_bytes", lambda data, seed: 0)
    assert PerfectHash.build(["first", "second"]) is None
