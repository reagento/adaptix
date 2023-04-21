from functools import partial
from typing import List

from pydantic import BaseModel, Field

from benchmarks.pybench.bench_api import benchmark_plan
from benchmarks.small_structures.common import create_book, create_dumped_book


class Review(BaseModel):
    id: int
    title: str
    rating: float
    content: str = Field(alias='text')

    model_config = {
        'populate_by_name': True,
    }


class Book(BaseModel):
    id: int
    name: str
    reviews: List[Review]


class StrictReview(BaseModel):
    id: int
    title: str
    rating: float
    content: str = Field(alias='text')

    model_config = {
        'populate_by_name': True,
        'strict': True,
    }


class StrictBook(BaseModel):
    id: int
    name: str
    reviews: List[StrictReview]

    model_config = {
        'strict': True,
    }


def test_loading():
    assert (
        Book.model_validate(create_dumped_book(reviews_count=1))
        ==
        create_book(Book, Review, reviews_count=1)
    )
    assert (
        StrictBook.model_validate(create_dumped_book(reviews_count=1))
        ==
        create_book(StrictBook, StrictReview, reviews_count=1)
    )


def test_dumping():
    assert (
        create_book(Book, Review, reviews_count=1).model_dump(mode='json', by_alias=True)
        ==
        create_dumped_book(reviews_count=1)
    )
    assert (
        create_book(StrictBook, StrictReview, reviews_count=1).model_dump(mode='json', by_alias=True)
        ==
        create_dumped_book(reviews_count=1)
    )


def bench_loading(strict: bool, reviews_count: int):
    if strict:
        loader = StrictBook.model_validate
    else:
        loader = Book.model_validate

    data = create_dumped_book(reviews_count=reviews_count)
    return benchmark_plan(loader, data)


def bench_dumping(strict: bool, reviews_count: int):
    if strict:
        data = create_book(StrictBook, StrictReview, reviews_count=reviews_count)
        dumper = StrictBook.model_dump
    else:
        data = create_book(Book, Review, reviews_count=reviews_count)
        dumper = Book.model_dump

    return benchmark_plan(partial(dumper, mode='json', by_alias=True), data)
