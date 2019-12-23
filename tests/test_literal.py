import sys
from unittest import TestCase

from dataclass_factory import Factory

if sys.version_info >= (3, 8):
    from typing import Literal

    ABC = Literal["a", "b", "c"]
    One = Literal[1]


    class TestLiteral(TestCase):
        def setUp(self) -> None:
            self.factory = Factory()

        def test_literal_fail(self):
            with self.assertRaises(ValueError):
                self.factory.load("d", ABC)
            with self.assertRaises(ValueError):
                self.factory.load(1.0, One)

        def test_literal(self):
            self.assertEqual(self.factory.load("a", ABC), "a")
            self.assertEqual(self.factory.load("b", ABC), "b")
            self.assertEqual(self.factory.load(1, One), 1)
