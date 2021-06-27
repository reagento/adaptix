from typing import Set

import pytest

from dataclass_factory_30.high_level import NameMapper
from dataclass_factory_30.high_level.name_style import NameStyle


def check_name_mapper(mapper: NameMapper, source: Set[str], target: Set[str]):
    result = set()
    for s_name in source:
        result.add(mapper._map_name(s_name))

    result -= {None}

    assert result == target


def test_default():
    check_name_mapper(
        NameMapper(),
        {'a', 'b', '_c', 'd_', '_e_'},
        {'a', 'b', 'd'},
    )


def test_name_mutating():
    check_name_mapper(
        NameMapper(
            map={},
            trim_trailing_underscore=True,
            name_style=NameStyle.UPPER,
        ),
        {'a', 'b', '_c', 'd_', '_e_'},
        {'A', 'B', 'D'},
    )
    check_name_mapper(
        NameMapper(
            map={'a': 'z'},
            trim_trailing_underscore=True,
            name_style=NameStyle.UPPER,
        ),
        {'a', 'b', '_c', 'd_', '_e_'},
        {'z', 'B', 'D'},
    )
    check_name_mapper(
        NameMapper(
            map={'a': 'z'},
            trim_trailing_underscore=True,
            name_style=NameStyle.UPPER,
        ),
        {'a', 'b', '_c', 'd_', '_e_'},
        {'z', 'B', 'D'},
    )
    check_name_mapper(
        NameMapper(
            map={'a': 'z', '_c': 'x'},
            trim_trailing_underscore=True,
            name_style=NameStyle.UPPER,
        ),
        {'a', 'b', '_c', 'd_', '_e_'},
        {'z', 'B', 'D'},
    )
    check_name_mapper(
        NameMapper(
            map={'a': 'z', 'd_': 'w'},
            name_style=NameStyle.UPPER,
            trim_trailing_underscore=True,
        ),
        {'a', 'b', '_c', 'd_', '_e_'},
        {'z', 'B', 'w'},
    )
    check_name_mapper(
        NameMapper(
            map={'a': '_z'},
            name_style=NameStyle.UPPER,
            trim_trailing_underscore=True,
        ),
        {'a', 'b', '_c', 'd_', '_e_'},
        {'_z', 'B', 'D'},
    )
    check_name_mapper(
        NameMapper(
            map={},
            trim_trailing_underscore=False,
            name_style=NameStyle.UPPER,
        ),
        {'a', 'b', '_c', 'd_', '_e_'},
        {'A', 'B', 'D_'},
    )


def test_name_filtering():
    check_name_mapper(
        NameMapper(
            skip=['a', 'xxx'],
            only_mapped=False,
            only=None,
            skip_internal=True,
        ),
        {'a', 'b', '_c', 'd_', '_e_'},
        {'b', 'd'},
    )
    check_name_mapper(
        NameMapper(
            skip=[],
            only_mapped=True,
            only=None,
            skip_internal=True,
            map={},
        ),
        {'a', 'b', '_c', 'd_', '_e_'},
        set(),
    )
    check_name_mapper(
        NameMapper(
            skip=[],
            only_mapped=True,
            only=None,
            skip_internal=True,
            map={'a': 'z'},
        ),
        {'a', 'b', '_c', 'd_', '_e_'},
        {'z'},
    )
    check_name_mapper(
        NameMapper(
            skip=[],
            only_mapped=False,
            only=['a', '_c'],
            skip_internal=True,
        ),
        {'a', 'b', '_c', 'd_', '_e_'},
        {'a', '_c'},
    )
    check_name_mapper(
        NameMapper(
            skip=[],
            only_mapped=True,
            only=['a'],
            skip_internal=False,
            map={'b': 'y'}
        ),
        {'a', 'b', '_c', 'd_', '_e_'},
        {'a', 'y'},
    )
    check_name_mapper(
        NameMapper(
            skip=['b'],
            only_mapped=False,
            only=['a', 'b'],
            skip_internal=False,
        ),
        {'a', 'b', '_c', 'd_', '_e_'},
        {'a'},
    )
    check_name_mapper(
        NameMapper(
            skip=['b'],
            only_mapped=True,
            only=None,
            skip_internal=True,
            map={'a': 'z', 'b': 'y'}
        ),
        {'a', 'b', '_c', 'd_', '_e_'},
        {'z'},
    )
    check_name_mapper(
        NameMapper(
            skip=[],
            only_mapped=False,
            only=['a', '_c'],
            skip_internal=True,
        ),
        {'a', 'b', '_c', 'd_', '_e_'},
        {'a', '_c'},
    )
