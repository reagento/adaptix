#!/usr/bin/env python
# -*- coding: utf-8 -*-
from dataclasses import dataclass
from unittest import TestCase

from dataclass_factory import ParserFactory, NameStyle, SerializerFactory
from dataclass_factory.naming import convert_name


@dataclass
class Data:
    styled_name: int
    trailed_: int
    BadSnakeName: int


class TestParser(TestCase):
    def do_test_convert(self, name_style: NameStyle, snake_name: str, none_snake_name: str):
        self.assertEqual(none_snake_name, convert_name(snake_name, name_style, None, True))

    def do_case_test(self, name_style: NameStyle, *, styled_name: str, trailed: str, bad_snake_name: str):
        data = {
            styled_name: 1,
            trailed: 2,
            bad_snake_name: 3
        }

        self.do_test_convert(name_style, 'styled_name', styled_name)
        self.do_test_convert(name_style, 'trailed_', trailed)
        self.do_test_convert(name_style, 'BadSnakeName', bad_snake_name)

        parser = ParserFactory(name_styles={Data: name_style}).get_parser(Data)
        self.assertEqual(parser(data), Data(1, 2, 3))

    def test_none(self):
        data = {
            "styled_name": 1,
            "trailed": 2,
            "BadSnakeName": 3
        }
        parser = ParserFactory().get_parser(Data)
        self.assertEqual(parser(data), Data(1, 2, 3))

    def test_snake(self):
        self.do_case_test(
            NameStyle.snake,
            styled_name="styled_name",
            trailed="trailed",
            bad_snake_name="BadSnakeName",
        )

    def test_kebab(self):
        self.do_case_test(
            NameStyle.kebab,
            styled_name="styled-name",
            trailed="trailed",
            bad_snake_name="BadSnakeName",
        )

    def test_camel_lower(self):
        self.do_case_test(
            NameStyle.camel_lower,
            styled_name="styledName",
            trailed="trailed",
            bad_snake_name="badsnakename",
        )

    def test_camel(self):
        self.do_case_test(
            NameStyle.camel,
            styled_name="StyledName",
            trailed="Trailed",
            bad_snake_name="Badsnakename",
        )

    def test_lower(self):
        self.do_case_test(
            NameStyle.lower,
            styled_name="styledname",
            trailed="trailed",
            bad_snake_name="badsnakename",
        )

    def test_upper(self):
        self.do_case_test(
            NameStyle.upper,
            styled_name="STYLEDNAME",
            trailed="TRAILED",
            bad_snake_name="BADSNAKENAME",
        )

    def test_upper_snake(self):
        self.do_case_test(
            NameStyle.upper_snake,
            styled_name="STYLED_NAME",
            trailed="TRAILED",
            bad_snake_name="BADSNAKENAME",
        )

    def test_camel_snake(self):
        self.do_case_test(
            NameStyle.camel_snake,
            styled_name="Styled_Name",
            trailed="Trailed",
            bad_snake_name="Badsnakename",
        )

    def test_dot(self):
        self.do_case_test(
            NameStyle.dot,
            styled_name="styled.name",
            trailed="trailed",
            bad_snake_name="BadSnakeName",
        )

    def test_camel_dot(self):
        self.do_case_test(
            NameStyle.camel_dot,
            styled_name="Styled.Name",
            trailed="Trailed",
            bad_snake_name="Badsnakename",
        )

    def test_upper_dot(self):
        self.do_case_test(
            NameStyle.upper_dot,
            styled_name="STYLED.NAME",
            trailed="TRAILED",
            bad_snake_name="BADSNAKENAME",
        )


class TestSerializer(TestCase):
    def test_none(self):
        data = {
            "some-var": 1,
            "other": 2,
            "BadSnakeName": 3
        }
        d = Data(1, 2, 3)
        serializer = SerializerFactory(name_styles={Data: NameStyle.kebab}).get_serializer(Data)
        self.assertEqual(serializer(d), data)
