#!/usr/bin/env python
# -*- coding: utf-8 -*-
from dataclasses import dataclass
from unittest import TestCase

from dataclass_factory import ParserFactory, NamingPolicy


@dataclass
class Data:
    some_var: int
    other: int
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
        parser = ParserFactory(naming_policies={Data: NamingPolicy.snake}).get_parser(Data)
        self.assertEqual(parser(data), Data(1, 2, 3))

    def test_kebab(self):
        data = {
            "some-var": 1,
            "other": 2,
            "UnsupportedVar": 3
        }
        parser = ParserFactory(naming_policies={Data: NamingPolicy.kebab}).get_parser(Data)
        self.assertEqual(parser(data), Data(1, 2, 3))

    def test_camel(self):
        data = {
            "SomeVar": 1,
            "Other": 2,
            "UnsupportedVar": 3
        }
        parser = ParserFactory(naming_policies={Data: NamingPolicy.camel}).get_parser(Data)
        self.assertEqual(parser(data), Data(1, 2, 3))

    def test_camel_lower(self):
        data = {
            "someVar": 1,
            "other": 2,
            "UnsupportedVar": 3
        }
        parser = ParserFactory(naming_policies={Data: NamingPolicy.camel_lower}).get_parser(Data)
        self.assertEqual(parser(data), Data(1, 2, 3))
