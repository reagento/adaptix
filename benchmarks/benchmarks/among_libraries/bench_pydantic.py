from functools import partial
from typing import List

from pydantic import BaseModel, Field

from benchmarks.among_libraries.input_data import create_book, create_dumped_book
from benchmarks.pybench.bench_api import benchmark_plan


class Review(BaseModel):
    id: int
    title: str
    rating: float
    content: str = Field(alias='text')

    class Config:
        allow_population_by_field_name = True


class Book(BaseModel):
    id: int
    name: str
    reviews: List[Review]


def test_loading():
    assert (
        Book.parse_obj(create_dumped_book(reviews_count=1))
        ==
        create_book(Book, Review, reviews_count=1)
    )


def test_dumping():
    assert (
        create_book(Book, Review, reviews_count=1).dict(by_alias=True)
        ==
        create_dumped_book(reviews_count=1)
    )


def bench_loading(reviews_count: int):
    data = create_dumped_book(reviews_count=reviews_count)
    return benchmark_plan(Book.parse_obj, data)


def bench_dumping(reviews_count: int):
    data = create_book(Book, Review, reviews_count=reviews_count)
    return benchmark_plan(partial(Book.dict, by_alias=True), data)
