#!/usr/bin/env python
# -*- coding: utf-8 -*-
from dataclasses import dataclass
from unittest import TestCase

from dataclass_factory import ParserFactory, NameStyle, SerializerFactory


@dataclass
class Data:
    some_var: int
    other_: int
    UnsupportedVar: int


class Test1(TestCase):
    def test_none(self):
        data = {
            "some_var": 1,
            "other": 2,
            "UnsupportedVar": 3
        }
        parser = ParserFactory().get_parser(Data)
        self.assertEqual(parser(data), Data(1, 2, 3))

    def test_snake(self):
        data = {
            "some_var": 1,
            "other": 2,
            "UnsupportedVar": 3
        }
        parser = ParserFactory(name_styles={Data: NameStyle.snake}).get_parser(Data)
        self.assertEqual(parser(data), Data(1, 2, 3))

    def test_kebab(self):
        data = {
            "some-var": 1,
            "other": 2,
            "UnsupportedVar": 3
        }
        parser = ParserFactory(name_styles={Data: NameStyle.kebab}).get_parser(Data)
        self.assertEqual(parser(data), Data(1, 2, 3))

    def test_camel(self):
        data = {
            "SomeVar": 1,
            "Other": 2,
            "UnsupportedVar": 3
        }
        parser = ParserFactory(name_styles={Data: NameStyle.camel}).get_parser(Data)
        self.assertEqual(parser(data), Data(1, 2, 3))

    def test_camel_lower(self):
        data = {
            "someVar": 1,
            "other": 2,
            "UnsupportedVar": 3
        }
        parser = ParserFactory(name_styles={Data: NameStyle.camel_lower}).get_parser(Data)
        self.assertEqual(parser(data), Data(1, 2, 3))


class TestSerializer(TestCase):
    def test_none(self):
        data = {
            "some-var": 1,
            "other": 2,
            "UnsupportedVar": 3
        }
        d = Data(1, 2, 3)
        serializer = SerializerFactory(name_styles={Data: NameStyle.kebab}).get_serializer(Data)
        self.assertEqual(serializer(d), data)
