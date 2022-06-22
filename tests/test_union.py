from __future__ import annotations

import sys
import unittest
from dataclasses import dataclass
from typing import Union
from unittest import TestCase

from dataclass_factory import Factory


@dataclass
class Data310:
    x: int | str


@dataclass
class DataOld:
    x: Union[int, str]


class TestUnion(TestCase):
    def setUp(self) -> None:
        self.factory = Factory()

    @unittest.skipUnless(sys.version_info[:2] >= (3, 10),
                         "requires Python 3.10+")
    def test_uniontype(self):
        raw = {"x": "hello"}
        data = self.factory.load(raw, Data310)
        self.assertEqual(data, Data310("hello"))
        self.assertEqual(self.factory.dump(data), raw)

    def test_union(self):
        raw = {"x": "hello"}
        data = self.factory.load(raw, DataOld)
        self.assertEqual(data, DataOld("hello"))
        self.assertEqual(self.factory.dump(data), raw)
