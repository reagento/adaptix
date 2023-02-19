from schematics.models import Model
from schematics.types import FloatType, IntType, ListType, ModelType, StringType

from benchmarks.among_libraries.input_data import create_dumped_book
from benchmarks.pybench.bench_api import benchmark_plan


class Review(Model):
    id = IntType()
    title = StringType()
    rating = FloatType()
    content = StringType(serialized_name='text')


class Book(Model):
    id = IntType()
    name = StringType()
    reviews = ListType(ModelType(Review))


def create_book_schematics(*, reviews_count: int) -> Book:
    return Book(create_dumped_book(reviews_count=reviews_count))


def test_loading():
    create_book_schematics(reviews_count=1)


def test_dumping():
    assert (
        create_book_schematics(reviews_count=1).to_primitive()
        ==
        create_dumped_book(reviews_count=1)
    )


def bench_loading(reviews_count: int):
    data = create_dumped_book(reviews_count=reviews_count)
    return benchmark_plan(Book, data)


def bench_dumping(reviews_count: int):
    data = create_book_schematics(reviews_count=reviews_count)
    return benchmark_plan(Book.to_primitive, data)
