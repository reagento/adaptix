from dataclasses import dataclass
from unittest import TestCase

from dataclass_factory import validate, Factory, Schema, NameStyle


class MySchema(Schema):
    @validate("field_name")
    def validate_field(self, data):
        if data:
            return data
        raise ValueError

    @validate("field_name", pre=True)
    def validate_field_pre(self, data):
        return data * 100

    @validate("other_field")
    def validate_other(self, data):
        return data + 1

    @validate()
    def validate_any(self, data):
        if data == 666:
            raise ValueError
        return data


@dataclass
class My:
    field_name: int
    other_field: int


class ValidationTestCase(TestCase):
    def test_validate(self):
        factory = Factory(schemas={My: MySchema()})
        res = factory.load({"field_name": 1, "other_field": 10}, My)
        self.assertEqual(res, My(100, 11))

    def test_name_style(self):
        factory = Factory(schemas={My: MySchema(name_style=NameStyle.camel)})
        res = factory.load({"FieldName": 1, "OtherField": 10}, My)
        self.assertEqual(res, My(100, 11))

    def test_raises(self):
        factory = Factory(schemas={My: MySchema()})
        with self.assertRaises(ValueError):
            factory.load({"field_name": 0, "other_field": 10}, My)

    def test_any(self):
        factory = Factory(schemas={My: MySchema()})
        with self.assertRaises(ValueError):
            factory.load({"field_name": 0, "other_field": 666}, My)
