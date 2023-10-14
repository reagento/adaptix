from dataclasses import dataclass
from typing import List

from adaptix import DebugTrail, Retort, name_mapping
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


retort = Retort(
    recipe=[
        name_mapping(Review, map={'content': 'text'}),
    ],
)


def test_loading():
    assert (
        retort.load(create_dumped_book(reviews_count=1), Book)
        ==
        create_book(Book, Review, reviews_count=1)
    )


def test_dumping():
    assert (
        retort.dump(create_book(Book, Review, reviews_count=1))
        ==
        create_dumped_book(reviews_count=1)
    )


def bench_loading(strict_coercion: bool, debug_trail: str, reviews_count: int):
    loader = retort.replace(
        strict_coercion=strict_coercion,
        debug_trail=DebugTrail(debug_trail),
    ).get_loader(Book)

    data = create_dumped_book(reviews_count=reviews_count)
    return benchmark_plan(loader, data)


def bench_dumping(debug_trail: str, reviews_count: int):
    dumper = retort.replace(
        debug_trail=DebugTrail(debug_trail),
    ).get_dumper(Book)

    data = create_book(Book, Review, reviews_count=reviews_count)
    return benchmark_plan(dumper, data)
