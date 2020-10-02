from dataclasses import dataclass
from unittest import TestCase

from dataclass_factory import Factory, NameStyle, Schema, validate


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

    @validate(pre=True)
    def validate_any(self, data):
        if data == 666:
            raise ValueError
        return data


class My2decSchema(Schema):
    @validate("field_name")
    @validate("other_field")
    def v1(self, data):
        return data + 1


class My2valSchema(Schema):
    @validate("field_name")
    def v1(self, data):
        if data > 100:
            raise ValueError
        return data

    @validate("field_name")
    def v2(self, data):
        if data < 0:
            raise ValueError
        return data + 1


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
            factory.load({"field_name": 1, "other_field": 666}, My)

    def test_2dec(self):
        factory = Factory(schemas={My: My2decSchema()})
        res = factory.load({"field_name": 100, "other_field": 10}, My)
        self.assertEqual(res, My(101, 11))

    def test_2val(self):
        factory = Factory(schemas={My: My2valSchema()})
        with self.assertRaises(ValueError):
            factory.load({"field_name": 100000, "other_field": 666}, My)
        with self.assertRaises(ValueError):
            factory.load({"field_name": -10000, "other_field": 666}, My)
