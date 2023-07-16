from functools import partial
from typing import List

import msgspec
import pytest

from benchmarks.pybench.bench_api import benchmark_plan
from benchmarks.simple_structures.common import create_book, create_dumped_book

review_rename = {'content': 'text'}


class Review(msgspec.Struct, rename=review_rename):
    id: int
    title: str
    rating: float
    content: str


class Book(msgspec.Struct):
    id: int
    name: str
    reviews: List[Review]


class ReviewNoGC(msgspec.Struct, rename=review_rename, gc=False):
    id: int
    title: str
    rating: float
    content: str


class BookNoGC(msgspec.Struct, gc=False):
    id: int
    name: str
    reviews: List[ReviewNoGC]


@pytest.mark.parametrize('strict', [False, True])
def test_loading(strict):
    assert (
        msgspec.convert(create_dumped_book(reviews_count=1), Book, strict=strict)
        ==
        create_book(Book, Review, reviews_count=1)
    )
    assert (
        msgspec.convert(create_dumped_book(reviews_count=1), BookNoGC, strict=strict)
        ==
        create_book(BookNoGC, ReviewNoGC, reviews_count=1)
    )


def test_dumping():
    assert (
        msgspec.to_builtins(create_book(Book, Review, reviews_count=1))
        ==
        create_dumped_book(reviews_count=1)
    )
    assert (
        msgspec.to_builtins(create_book(BookNoGC, ReviewNoGC, reviews_count=1))
        ==
        create_dumped_book(reviews_count=1)
    )


def bench_loading(no_gc: bool, strict: bool, reviews_count: int):
    data = create_dumped_book(reviews_count=reviews_count)
    return benchmark_plan(
        partial(msgspec.convert, strict=strict),
        data,
        BookNoGC if no_gc else Book,
    )


def bench_dumping(no_gc: bool, reviews_count: int):
    if no_gc:
        data = create_book(BookNoGC, ReviewNoGC, reviews_count=reviews_count)
    else:
        data = create_book(Book, Review, reviews_count=reviews_count)
    return benchmark_plan(msgspec.to_builtins, data)
