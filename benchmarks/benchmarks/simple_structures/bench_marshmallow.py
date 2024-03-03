from dataclasses import dataclass
from typing import List

from marshmallow import Schema, fields, post_load

from benchmarks.pybench.bench_api import benchmark_plan
from benchmarks.simple_structures.common import create_book, create_dumped_book


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


class ReviewSchema(Schema):
    id = fields.Int()
    title = fields.Str()
    rating = fields.Float()
    content = fields.Str(data_key="text")

    @post_load
    def _to_model(self, data, **kwargs):
        return Review(**data)


class BookSchema(Schema):
    id = fields.Int()
    name = fields.Str()
    reviews = fields.List(fields.Nested(ReviewSchema()))

    @post_load
    def _to_model(self, data, **kwargs):
        return Book(**data)


def test_loading():
    assert (
        BookSchema().load(create_dumped_book(reviews_count=1))
        ==
        create_book(Book, Review, reviews_count=1)
    )


def test_dumping():
    assert (
        BookSchema().dump(create_book(Book, Review, reviews_count=1))
        ==
        create_dumped_book(reviews_count=1)
    )


def bench_loading(reviews_count: int):
    data = create_dumped_book(reviews_count=reviews_count)
    return benchmark_plan(BookSchema().load, data)


def bench_dumping(reviews_count: int):
    data = create_book(Book, Review, reviews_count=reviews_count)
    return benchmark_plan(BookSchema().dump, data)
