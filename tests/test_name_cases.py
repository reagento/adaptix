#!/usr/bin/env python
# -*- coding: utf-8 -*-
from dataclasses import dataclass
from unittest import TestCase

from dataclass_factory import ParserFactory, NameStyle, SerializerFactory, Factory, Schema
from dataclass_factory.naming import convert_name, is_snake_case


@dataclass
class Data:
    styled_name: int
    trailed_name_: int
    NameToMap: int


TRAILING_VARIANTS = (None, False, True)


class TestConvertLogic(TestCase):
    def assert_raise_value_error(self, name_style: NameStyle):
        for trailing in TRAILING_VARIANTS:
            with self.assertRaises(ValueError):
                convert_name('BadSnakeName', name_style, None, trailing)

    def test_value_error(self):
        for ns in NameStyle:
            if ns is not NameStyle.ignore:
                self.assert_raise_value_error(ns)

        for trailing in TRAILING_VARIANTS:
            self.assertEqual(
                convert_name('BadSnakeName', NameStyle.ignore, None, trailing),
                'BadSnakeName'
            )

    def test_mapping(self):
        for ns in NameStyle:
            for trailing in TRAILING_VARIANTS:
                self.assertEqual(
                    convert_name('BadSnakeName', ns, {'BadSnakeName': 'MappedName'}, trailing),
                    'MappedName'
                )


class TestParser(TestCase):
    def test_snake_check(self):
        self.assertTrue(is_snake_case('a_x'))
        self.assertTrue(is_snake_case('a_'))
        self.assertTrue(is_snake_case('a_x_'))
        self.assertTrue(is_snake_case('a_1'))
        self.assertTrue(is_snake_case('a_1_'))

        self.assertTrue(is_snake_case('3_1'))
        self.assertTrue(is_snake_case('3_1_'))

        self.assertFalse(is_snake_case('A_1_'))
        self.assertFalse(is_snake_case('Aa_1_'))

        self.assertTrue(is_snake_case('_1_'))
        self.assertTrue(is_snake_case('_1_2'))

    def assert_convert(self, name_style: NameStyle, snake_name: str, result_name: str):
        self.assertEqual(result_name, convert_name(snake_name, name_style, None, True))

    def do_case_test(self, name_style: NameStyle, *, styled: str, trailed: str):
        data = {
            styled: 1,
            trailed: 2,
            'MappedName': 3,
        }

        self.assert_convert(name_style, 'styled_name', styled)
        self.assert_convert(name_style, 'trailed_name_', trailed)

        parser = Factory(
            default_schema=Schema(
                name_style=name_style,
                name_mapping={'NameToMap': 'MappedName'}
            )
        ).parser(Data)
        self.assertEqual(parser(data), Data(1, 2, 3))

    def test_none(self):
        data = {
            "styled_name": 1,
            "trailed_name": 2,
            "NameToMap": 3,
        }
        parser = Factory().parser(Data)
        self.assertEqual(parser(data), Data(1, 2, 3))

    def test_ignore(self):
        self.do_case_test(
            NameStyle.ignore,
            styled="styled_name",
            trailed="trailed_name",
        )

    def test_snake(self):
        self.do_case_test(
            NameStyle.snake,
            styled="styled_name",
            trailed="trailed_name",
        )

    def test_kebab(self):
        self.do_case_test(
            NameStyle.kebab,
            styled="styled-name",
            trailed="trailed-name",
        )

    def test_camel_lower(self):
        self.do_case_test(
            NameStyle.camel_lower,
            styled="styledName",
            trailed="trailedName",
        )

    def test_camel(self):
        self.do_case_test(
            NameStyle.camel,
            styled="StyledName",
            trailed="TrailedName",
        )

    def test_lower(self):
        self.do_case_test(
            NameStyle.lower,
            styled="styledname",
            trailed="trailedname",
        )

    def test_upper(self):
        self.do_case_test(
            NameStyle.upper,
            styled="STYLEDNAME",
            trailed="TRAILEDNAME",
        )

    def test_upper_snake(self):
        self.do_case_test(
            NameStyle.upper_snake,
            styled="STYLED_NAME",
            trailed="TRAILED_NAME",
        )

    def test_camel_snake(self):
        self.do_case_test(
            NameStyle.camel_snake,
            styled="Styled_Name",
            trailed="Trailed_Name",
        )

    def test_dot(self):
        self.do_case_test(
            NameStyle.dot,
            styled="styled.name",
            trailed="trailed.name",
        )

    def test_camel_dot(self):
        self.do_case_test(
            NameStyle.camel_dot,
            styled="Styled.Name",
            trailed="Trailed.Name",
        )

    def test_upper_dot(self):
        self.do_case_test(
            NameStyle.upper_dot,
            styled="STYLED.NAME",
            trailed="TRAILED.NAME",
        )


class TestSerializer(TestCase):
    def test_none(self):
        data = {
            "styled_name": 1,
            "trailed_name": 2,
            "NameToMap": 3
        }
        d = Data(1, 2, 3)

        serializer = Factory().serializer(Data)
        self.assertEqual(serializer(d), data)
