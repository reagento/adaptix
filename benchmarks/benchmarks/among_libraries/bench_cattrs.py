from typing import List

from attr import define
from cattr import Converter
from cattrs.gen import make_dict_structure_fn, make_dict_unstructure_fn, override

from benchmarks.among_libraries.input_data import create_book, create_dumped_book
from benchmarks.pybench.bench_api import benchmark_plan


@define
class Review:
    id: int
    title: str
    rating: float
    content: str


@define
class Book:
    id: int
    name: str
    reviews: List[Review]


converter = Converter()
converter.register_unstructure_hook(
    Review,
    make_dict_unstructure_fn(Review, converter, content=override(rename="text")),
)
converter.register_structure_hook(
    Review,
    make_dict_structure_fn(Review, converter, content=override(rename="text")),
)


def test_loading():
    assert (
        converter.structure(create_dumped_book(reviews_count=1), Book)
        ==
        create_book(Book, Review, reviews_count=1)
    )


def test_dumping():
    assert (
        converter.unstructure(create_book(Book, Review, reviews_count=1))
        ==
        create_dumped_book(reviews_count=1)
    )


def bench_loading(detailed_validation: bool, reviews_count: int):
    bench_converter = converter.copy(detailed_validation=detailed_validation)

    data = create_dumped_book(reviews_count=reviews_count)
    return benchmark_plan(bench_converter.structure, data, Book)


def bench_dumping(detailed_validation: bool, reviews_count: int):
    bench_converter = converter.copy(detailed_validation=detailed_validation)

    data = create_book(Book, Review, reviews_count=reviews_count)
    return benchmark_plan(bench_converter.unstructure, data, Book)
