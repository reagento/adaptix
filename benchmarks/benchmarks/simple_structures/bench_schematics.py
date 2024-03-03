from schematics.models import Model
from schematics.types import FloatType, IntType, ListType, ModelType, StringType

from benchmarks.pybench.bench_api import benchmark_plan
from benchmarks.simple_structures.common import create_book, create_dumped_book


class Review(Model):
    id = IntType(required=True)
    title = StringType(required=True)
    rating = FloatType(required=True)
    content = StringType(serialized_name="text", required=True)


class Book(Model):
    id = IntType(required=True)
    name = StringType(required=True)
    reviews = ListType(ModelType(Review), required=True)


def maker(model):
    def wrapper(**kwargs):
        return model(kwargs)

    return wrapper


def test_loading():
    assert (
        Book(create_dumped_book(reviews_count=1))
        ==
        create_book(maker(Book), maker(Review), reviews_count=1)
    )


def test_dumping():
    assert (
        create_book(maker(Book), maker(Review), reviews_count=1).to_primitive()
        ==
        create_dumped_book(reviews_count=1)
    )


def bench_loading(reviews_count: int):
    data = create_dumped_book(reviews_count=reviews_count)
    return benchmark_plan(Book, data)


def bench_dumping(reviews_count: int):
    data = create_book(maker(Book), maker(Review), reviews_count=reviews_count)
    return benchmark_plan(data.to_primitive)
