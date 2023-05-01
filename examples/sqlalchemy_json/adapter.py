from sqlalchemy import JSON, TypeDecorator

from adaptix import AdornedRetort, TypeHint


# pylint: disable=abstract-method
# SQLAlchemy does not require to implement process_literal_param and python_type
class ModelJSON(TypeDecorator):
    impl = JSON
    cache_ok = True

    def __init__(
        self,
        tp: TypeHint,
        retort: AdornedRetort,
        none_as_null: bool = False,
    ):
        super().__init__(none_as_null=none_as_null)
        self.tp = tp
        self.retort = retort
        self.loader = retort.get_loader(tp)
        self.dumper = retort.get_dumper(tp)

    def process_bind_param(self, value, dialect):
        return self.dumper(value)

    def process_result_value(self, value, dialect):
        return self.loader(value)

    def coerce_compared_value(self, op, value):
        return self.impl.coerce_compared_value(op, value)
