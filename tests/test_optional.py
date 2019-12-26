from typing import Dict, Optional
from unittest import TestCase

from dataclasses import dataclass

from dataclass_factory import Factory


@dataclass
class Data:
    x: Optional[Dict[str, None]]
    y: Optional[bool]


class TestOptional(TestCase):
    def test_optional(self):
        factory = Factory()
        y = factory.load({"x": None, "y": None}, Data)
        self.assertEqual(y, Data(None, None))
