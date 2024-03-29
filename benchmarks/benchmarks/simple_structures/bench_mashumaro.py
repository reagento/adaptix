from dataclasses import dataclass
from typing import List

from mashumaro import DataClassDictMixin
from mashumaro.config import BaseConfig

from benchmarks.pybench.bench_api import benchmark_plan
from benchmarks.simple_structures.common import create_book, create_dumped_book


@dataclass
class Review(DataClassDictMixin):
    id: int
    title: str
    rating: float
    content: str

    class Config(BaseConfig):
        aliases = {
            "content": "text",
        }
        serialize_by_alias = True


@dataclass
class Book(DataClassDictMixin):
    id: int
    name: str
    reviews: List[Review]


@dataclass
class ReviewLC(DataClassDictMixin):
    id: int
    title: str
    rating: float
    content: str

    class Config(BaseConfig):
        aliases = {
            "content": "text",
        }
        serialize_by_alias = True
        lazy_compilation = True



@dataclass
class BookLC(DataClassDictMixin):
    id: int
    name: str
    reviews: List[ReviewLC]

    class Config(BaseConfig):
        lazy_compilation = True


def test_loading():
    assert (
        Book.from_dict(create_dumped_book(reviews_count=1))
        ==
        create_book(Book, Review, reviews_count=1)
    )
    assert (
        BookLC.from_dict(create_dumped_book(reviews_count=1))
        ==
        create_book(BookLC, ReviewLC, reviews_count=1)
    )


def test_dumping():
    assert (
        create_book(Book, Review, reviews_count=1).to_dict()
        ==
        create_dumped_book(reviews_count=1)
    )
    assert (
        create_book(BookLC, ReviewLC, reviews_count=1).to_dict()
        ==
        create_dumped_book(reviews_count=1)
    )


def bench_loading(reviews_count: int, lazy_compilation: bool):
    data = create_dumped_book(reviews_count=reviews_count)
    if lazy_compilation:
        BookLC.from_dict(data)  # emit method compilation
    loader = BookLC.from_dict if lazy_compilation else Book.from_dict
    return benchmark_plan(loader, data)


def bench_dumping(reviews_count: int, lazy_compilation: bool):
    if lazy_compilation:
        data = create_book(BookLC, ReviewLC, reviews_count=reviews_count)
        data.to_dict()
    else:
        data = create_book(Book, Review, reviews_count=reviews_count)
    return benchmark_plan(data.to_dict)
