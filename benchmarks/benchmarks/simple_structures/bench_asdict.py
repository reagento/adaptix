from dataclasses import asdict, dataclass
from typing import List

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


def test_dumping():
    dumped_book = create_dumped_book(reviews_count=1)
    dumped_book["reviews"][0]["content"] = dumped_book["reviews"][0].pop("text")
    # asdict does not support renaming
    assert (
        asdict(create_book(Book, Review, reviews_count=1))
        ==
        dumped_book
    )


def bench_dumping(reviews_count: int):
    data = create_book(Book, Review, reviews_count=reviews_count)
    return benchmark_plan(asdict, data)
