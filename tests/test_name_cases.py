#!/usr/bin/env python
# -*- coding: utf-8 -*-
from dataclasses import dataclass
from unittest import TestCase

from dataclass_factory import ParserFactory, NameStyle, SerializerFactory
from dataclass_factory.naming import convert_name, is_snake_case


@dataclass
class Data:
    styled_name: int
    trailed_name_: int


class TestConvertLogic(TestCase):
    def assert_value_error(self, name_style: NameStyle):
        for trailing in (None, False, True):
            with self.assertRaises(ValueError):
                convert_name('NonSnakeCase', name_style, None, trailing)

    def test_value_error(self):
        self.assert_value_error(NameStyle.dot)
        self.assert_value_error(NameStyle.snake)


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
        self.assertTrue(is_snake_case('_1_'))
        self.assertTrue(is_snake_case('_1_2'))

    def assert_convert(self, name_style: NameStyle, snake_name: str, result_name: str):
        self.assertEqual(result_name, convert_name(snake_name, name_style, None, True))

    def do_case_test(self, name_style: NameStyle, *, styled_name: str, trailed: str):
        data = {
            styled_name: 1,
            trailed: 2,
        }

        self.assert_convert(name_style, 'styled_name', styled_name)
        self.assert_convert(name_style, 'trailed_name_', trailed)

        with self.assertRaises(ValueError):
            convert_name('BadSnakeName', name_style, None, True)

        parser = ParserFactory(name_styles={Data: name_style}).get_parser(Data)
        self.assertEqual(parser(data), Data(1, 2))

    def test_none(self):
        data = {
            "styled_name": 1,
            "trailed_name": 2,
        }
        parser = ParserFactory().get_parser(Data)
        self.assertEqual(parser(data), Data(1, 2))

    def test_snake(self):
        self.do_case_test(
            NameStyle.snake,
            styled_name="styled_name",
            trailed="trailed_name",
        )

    def test_kebab(self):
        self.do_case_test(
            NameStyle.kebab,
            styled_name="styled-name",
            trailed="trailed-name",
        )

    def test_camel_lower(self):
        self.do_case_test(
            NameStyle.camel_lower,
            styled_name="styledName",
            trailed="trailedName",
        )

    def test_camel(self):
        self.do_case_test(
            NameStyle.camel,
            styled_name="StyledName",
            trailed="TrailedName",
        )

    def test_lower(self):
        self.do_case_test(
            NameStyle.lower,
            styled_name="styledname",
            trailed="trailedname",
        )

    def test_upper(self):
        self.do_case_test(
            NameStyle.upper,
            styled_name="STYLEDNAME",
            trailed="TRAILEDNAME",
        )

    def test_upper_snake(self):
        self.do_case_test(
            NameStyle.upper_snake,
            styled_name="STYLED_NAME",
            trailed="TRAILED_NAME",
        )

    def test_camel_snake(self):
        self.do_case_test(
            NameStyle.camel_snake,
            styled_name="Styled_Name",
            trailed="Trailed_Name",
        )

    def test_dot(self):
        self.do_case_test(
            NameStyle.dot,
            styled_name="styled.name",
            trailed="trailed.name",
        )

    def test_camel_dot(self):
        self.do_case_test(
            NameStyle.camel_dot,
            styled_name="Styled.Name",
            trailed="Trailed.Name",
        )

    def test_upper_dot(self):
        self.do_case_test(
            NameStyle.upper_dot,
            styled_name="STYLED.NAME",
            trailed="TRAILED.NAME",
        )


class TestSerializer(TestCase):
    def test_none(self):
        data = {
            "styled-name": 1,
            "trailed-name": 2,
        }
        d = Data(1, 2)
        serializer = SerializerFactory(name_styles={Data: NameStyle.kebab}).get_serializer(Data)
        self.assertEqual(serializer(d), data)
