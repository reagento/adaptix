#!/usr/bin/env python
# -*- coding: utf-8 -*-
from dataclasses import dataclass
from unittest import TestCase

from dataclass_factory import Factory, Schema


@dataclass
class Data:
    last_: str
    _first: str = ""
    normal: str = ""


class TestUnderscore(TestCase):
    def test_keep_all(self):
        factory = Factory(
            default_schema=Schema(
                trim_trailing_underscore=False,
                skip_internal=False,
            )
        )
        data = Data("1", "2", "3")
        serial = {
            "last_": "1",
            "_first": "2",
            "normal": "3",
        }
        self.assertEqual(factory.dump(data), serial)
        self.assertEqual(factory.load(serial, Data), data)

    def test_trim(self):
        factory = Factory(
            default_schema=Schema(
                trim_trailing_underscore=True,
                skip_internal=False,
            )
        )
        data = Data("1", "2", "3")
        serial = {
            "last": "1",
            "_first": "2",
            "normal": "3",
        }
        self.assertEqual(factory.dump(data), serial)
        self.assertEqual(factory.load(serial, Data), data)

    def test_skip(self):
        factory = Factory(
            default_schema=Schema(
                trim_trailing_underscore=True,
                skip_internal=True,
            )
        )
        data = Data("1", "2", "3")
        serial = {
            "last": "1",
            "normal": "3",
        }
        self.assertEqual(factory.dump(data), serial)
        data = Data("1", normal="3")
        self.assertEqual(factory.load(serial, Data), data)
