import sys
from typing import Any
from unittest import TestCase

from nose2.tools import params  # type: ignore
from typing_extensions import Literal as CompatLiteral

from dataclass_factory import Factory

LITERALS: Any = [CompatLiteral]
if sys.version_info >= (3, 8):
    from typing import Literal as PyLiteral

    LITERALS.append(PyLiteral)


class TestLiteral(TestCase):
    def setUp(self) -> None:
        self.factory = Factory()

    @params(*LITERALS)
    def test_literal_fail(self, literal):
        abc = literal["a", "b", "c"]
        one = literal[1]
        with self.assertRaises(ValueError):
            self.factory.load("d", abc)
        with self.assertRaises(ValueError):
            self.factory.load(1.0, one)

    @params(*LITERALS)
    def test_literal(self, literal):
        abc = literal["a", "b", "c"]
        one = literal[1]
        self.assertEqual(self.factory.load("a", abc), "a")
        self.assertEqual(self.factory.load("b", abc), "b")
        self.assertEqual(self.factory.load("c", abc), "c")
        self.assertEqual(self.factory.load(1, one), 1)

        self.assertEqual(self.factory.dump("a", abc), "a")
        self.assertEqual(self.factory.dump("b", abc), "b")
        self.assertEqual(self.factory.dump("c", abc), "c")

        self.assertEqual(self.factory.dump("Z", abc), "Z")

        self.assertEqual(self.factory.dump(1, one), 1)
