from dataclasses import dataclass
from typing import List

from mashumaro import DataClassDictMixin
from mashumaro.config import BaseConfig

from benchmarks.pybench.bench_api import benchmark_plan
from benchmarks.small_structures.common import create_book, create_dumped_book


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


def test_loading():
    assert (
        Book.from_dict(create_dumped_book(reviews_count=1))
        ==
        create_book(Book, Review, reviews_count=1)
    )


def test_dumping():
    assert (
        create_book(Book, Review, reviews_count=1).to_dict()
        ==
        create_dumped_book(reviews_count=1)
    )


def bench_loading(reviews_count: int):
    data = create_dumped_book(reviews_count=reviews_count)
    return benchmark_plan(Book.from_dict, data)


def bench_dumping(reviews_count: int):
    data = create_book(Book, Review, reviews_count=reviews_count)
    return benchmark_plan(Book.to_dict, data)
