from dataclasses import dataclass
from typing import List

from dataclass_factory import Factory, Schema

from benchmarks.among_libraries.input_data import create_book, create_dumped_book
from benchmarks.pybench.bench_api import benchmark_plan


@dataclass
class Review:
    id: int
    title: str
    rating: float
    content: str


@dataclass
class Book:
    id: int
    name: str
    reviews: List[Review]


schemas = {
    Review: Schema(name_mapping={'content': 'text'}),
}


def test_loading():
    assert (
        Factory(schemas=schemas).load(create_dumped_book(reviews_count=1), Book)
        ==
        create_book(Book, Review, reviews_count=1)
    )


def test_dumping():
    assert (
        Factory(schemas=schemas).dump(create_book(Book, Review, reviews_count=1))
        ==
        create_dumped_book(reviews_count=1)
    )


def bench_loading(debug_path: bool, reviews_count: int):
    parser = Factory(schemas=schemas, debug_path=debug_path).parser(Book)

    data = create_dumped_book(reviews_count=reviews_count)
    return benchmark_plan(parser, data)


def bench_dumping(reviews_count: int):
    serializer = Factory(schemas=schemas).serializer(Book)

    data = create_book(Book, Review, reviews_count=reviews_count)
    return benchmark_plan(serializer, data)
