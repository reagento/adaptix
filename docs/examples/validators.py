from dataclasses import dataclass

from dataclass_factory import validate, Factory, Schema, NameStyle


class MySchema(Schema):
    SOMETHING = "Some string"

    @validate("int_field")  # use original field name in class
    def validate_field(self, data):
        if data > 100:
            raise ValueError
        return data * 100  # validator can change value

    # this validator will be called before parsing field
    @validate("complex_field", pre=True)
    def validate_field_pre(self, data):
        return data["value"]

    @validate("info")
    def validate_stub(self, data):
        return self.SOMETHING  # validator can access schema fields


@dataclass
class My:
    int_field: int
    complex_field: int
    info: str


factory = Factory(schemas={
    My: MySchema(name_style=NameStyle.upper_snake)  # name style does not affect how validators are bound to fields
})

result = factory.load({"INT_FIELD": 1, "COMPLEX_FIELD": {"value": 42}, "INFO": "ignored"}, My)
assert result == My(100, 42, "Some string")
