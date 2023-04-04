from functools import partial
from typing import List

from pydantic import BaseModel, Field, StrictFloat, StrictInt, StrictStr

from benchmarks.among_libraries.input_data import create_book, create_dumped_book
from benchmarks.pybench.bench_api import benchmark_plan


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


class StrictTypesReview(BaseModel):
    id: StrictInt
    title: StrictStr
    rating: StrictFloat
    content: StrictStr = Field(alias='text')

    model_config = {
        'populate_by_name': True,
    }


class StrictTypesBook(BaseModel):
    id: StrictFloat
    name: StrictStr
    reviews: List[StrictTypesReview]


def test_loading():
    assert (
        Book.model_validate(create_dumped_book(reviews_count=1))
        ==
        create_book(Book, Review, reviews_count=1)
    )
    assert (
        StrictTypesBook.model_validate(create_dumped_book(reviews_count=1))
        ==
        create_book(StrictTypesBook, StrictTypesReview, reviews_count=1)
    )


def test_dumping():
    assert (
        create_book(Book, Review, reviews_count=1).model_dump(mode='json', by_alias=True)
        ==
        create_dumped_book(reviews_count=1)
    )
    assert (
        create_book(StrictTypesBook, StrictTypesReview, reviews_count=1).model_dump(mode='json', by_alias=True)
        ==
        create_dumped_book(reviews_count=1)
    )


def bench_loading(reviews_count: int, strict_types: bool):
    if strict_types:
        loader = StrictTypesBook.model_validate
    else:
        loader = Book.model_validate

    data = create_dumped_book(reviews_count=reviews_count)
    return benchmark_plan(loader, data)


def bench_dumping(reviews_count: int, strict_types: bool):
    if strict_types:
        data = create_book(StrictTypesBook, StrictTypesReview, reviews_count=reviews_count)
        dumper = StrictTypesBook.model_dump
    else:
        data = create_book(Book, Review, reviews_count=reviews_count)
        dumper = Book.model_dump

    return benchmark_plan(partial(dumper, mode='json', by_alias=True), data)
