import pytest

from adaptix import NameStyle
from adaptix._internal.name_style import convert_snake_style, is_snake_case


def test_is_snake_case():
    assert is_snake_case('a')
    assert is_snake_case('a_b')
    assert is_snake_case('a_')
    assert is_snake_case('_a')
    assert is_snake_case('a_b_')
    assert is_snake_case('_a_')
    assert is_snake_case('_a_b')
    assert is_snake_case('_a_b_')

    assert is_snake_case('1')
    assert is_snake_case('1_2')
    assert is_snake_case('1_')
    assert is_snake_case('_1')
    assert is_snake_case('1_2_')
    assert is_snake_case('_1_')
    assert is_snake_case('_1_2')
    assert is_snake_case('_1_2_')

    assert is_snake_case('a_1')
    assert is_snake_case('a_1_')

    assert is_snake_case('a__b')
    assert is_snake_case('a__b_')

    assert is_snake_case('_')
    assert is_snake_case('___')

    assert not is_snake_case('A_1_')
    assert not is_snake_case('Aa_1_')

    assert not is_snake_case('123%')
    assert not is_snake_case('_123%')


def check_conversion(style, maps):
    for src, trg in maps.items():
        assert convert_snake_style(src, style) == trg


def test_snake_case_conversion():
    check_conversion(
        NameStyle.LOWER,
        {
            'abc_xyz': 'abcxyz',
            'abc__xyz': 'abcxyz',
            'abc_xyz_': 'abcxyz_',
            '_abc_xyz': '_abcxyz',
            '_abc_xyz_': '_abcxyz_',
            '_abc__xyz_': '_abcxyz_',
        }
    )
    check_conversion(
        NameStyle.CAMEL,
        {
            'abc_xyz': 'abcXyz',
            'abc__xyz': 'abcXyz',
            'abc_xyz_': 'abcXyz_',
            '_abc_xyz': '_abcXyz',
            '_abc_xyz_': '_abcXyz_',
            '_abc__xyz_': '_abcXyz_',
        }
    )
    check_conversion(
        NameStyle.PASCAL,
        {
            'abc_xyz': 'AbcXyz',
            'abc__xyz': 'AbcXyz',
            'abc_xyz_': 'AbcXyz_',
            '_abc_xyz': '_AbcXyz',
            '_abc_xyz_': '_AbcXyz_',
            '_abc__xyz_': '_AbcXyz_',
        }
    )
    check_conversion(
        NameStyle.UPPER,
        {
            'abc_xyz': 'ABCXYZ',
            'abc__xyz': 'ABCXYZ',
            'abc_xyz_': 'ABCXYZ_',
            '_abc_xyz': '_ABCXYZ',
            '_abc_xyz_': '_ABCXYZ_',
            '_abc__xyz_': '_ABCXYZ_',
        }
    )

    check_conversion(
        NameStyle.LOWER_DOT,
        {
            'abc_xyz': 'abc.xyz',
            'abc__xyz': 'abc..xyz',
            'abc_xyz_': 'abc.xyz_',
            '_abc_xyz': '_abc.xyz',
            '_abc_xyz_': '_abc.xyz_',
            '_abc__xyz_': '_abc..xyz_',
        }
    )
    check_conversion(
        NameStyle.CAMEL_DOT,
        {
            'abc_xyz': 'abc.Xyz',
            'abc__xyz': 'abc..Xyz',
            'abc_xyz_': 'abc.Xyz_',
            '_abc_xyz': '_abc.Xyz',
            '_abc_xyz_': '_abc.Xyz_',
            '_abc__xyz_': '_abc..Xyz_',
        }
    )
    check_conversion(
        NameStyle.PASCAL_DOT,
        {
            'abc_xyz': 'Abc.Xyz',
            'abc__xyz': 'Abc..Xyz',
            'abc_xyz_': 'Abc.Xyz_',
            '_abc_xyz': '_Abc.Xyz',
            '_abc_xyz_': '_Abc.Xyz_',
            '_abc__xyz_': '_Abc..Xyz_',
        }
    )
    check_conversion(
        NameStyle.UPPER_DOT,
        {
            'abc_xyz': 'ABC.XYZ',
            'abc__xyz': 'ABC..XYZ',
            'abc_xyz_': 'ABC.XYZ_',
            '_abc_xyz': '_ABC.XYZ',
            '_abc_xyz_': '_ABC.XYZ_',
            '_abc__xyz_': '_ABC..XYZ_',
        }
    )


def test_snake_case_conversion_fail():
    for style in NameStyle:
        with pytest.raises(ValueError):
            convert_snake_style('', style)

    for style in NameStyle:
        with pytest.raises(ValueError):
            convert_snake_style('___', style)

    for style in NameStyle:
        for name in ['AbcXyz', 'abcXyz', 'abcxyz?']:
            with pytest.raises(ValueError):
                convert_snake_style(name, style)
