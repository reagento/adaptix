# ruff: noqa: S101
from dataclasses import dataclass

import pytest

from adaptix import CodeGenBackend, DebugTrail, name_mapping
from adaptix._internal.code_tools.x86_64_compiler import check_native_platform
from benchmarks.pybench.bench_api import benchmark_plan
from benchmarks.simple_structures.bench_adaptix import Book, Review, retort
from benchmarks.simple_structures.common import create_book, create_dumped_book


@dataclass(slots=True)
class SlotReview:
    id: int
    title: str
    rating: float
    content: str


@dataclass(slots=True)
class SlotBook:
    id: int
    name: str
    reviews: list[SlotReview]


class FirstReview(Review):
    pass


class SecondReview(Review):
    pass


@dataclass
class SharedBranch:
    left: Review
    right: Review
    items: list[Review]
    mapping: dict[str, Review]


@dataclass
class SharedGraph:
    left: SharedBranch
    right: SharedBranch
    items: list[SharedBranch]
    mapping: dict[str, SharedBranch]


def create_case(workload: str):
    reviews_count = 1 if workload == "flat" else 100
    dumped_book = create_dumped_book(reviews_count=reviews_count)
    book_model, review_model = (SlotBook, SlotReview) if workload == "nested_slots" else (Book, Review)
    book = create_book(book_model, review_model, reviews_count=reviews_count)
    if workload == "flat":
        return Review, dumped_book["reviews"][0], book.reviews[0]
    if workload == "nested_fresh_keys":
        dumped_book["reviews"] = [
            {key.encode().decode(): value for key, value in review.items()} for review in dumped_book["reviews"]
        ]
    if workload == "nested_diverse":
        for index, (review, dumped) in enumerate(zip(book.reviews, dumped_book["reviews"], strict=True)):
            review.title = f"Review {index}"
            review.rating = index / 10
            dumped["title"] = review.title
            dumped["rating"] = review.rating
    if workload == "nested_polymorphic":
        for index, review in enumerate(book.reviews):
            cls = FirstReview if index % 2 else SecondReview
            replacement = cls.__new__(cls)
            if cls is SecondReview:
                replacement.other = None
            cls.__init__(replacement, review.id, review.title, review.rating, review.content)
            book.reviews[index] = replacement
    return book_model, dumped_book, book


def bench_loading(codegen_backend: str, debug_trail: str, workload: str):
    model, data, _ = create_case(workload)
    case_retort = retort.extend(recipe=[name_mapping(SlotReview, map={"content": "text"})])
    loader = case_retort.replace(
        codegen_backend=CodeGenBackend(codegen_backend),
        debug_trail=DebugTrail(debug_trail),
        strict_coercion=True,
    ).get_loader(model)
    return benchmark_plan(loader, data)


def bench_dumping(codegen_backend: str, debug_trail: str, workload: str):
    model, _, data = create_case(workload)
    case_retort = retort.extend(recipe=[name_mapping(SlotReview, map={"content": "text"})])
    dumper = case_retort.replace(
        codegen_backend=CodeGenBackend(codegen_backend),
        debug_trail=DebugTrail(debug_trail),
    ).get_dumper(model)
    return benchmark_plan(dumper, data)


def create_converter(case_retort, model, operation):
    fresh = case_retort.replace()
    return fresh.get_loader(model) if operation == "loading" else fresh.get_dumper(model)


def bench_creation(codegen_backend: str, debug_trail: str, workload: str, operation: str):
    model = SharedGraph if workload == "shared_graph" else create_case(workload)[0]
    case_retort = retort.replace(codegen_backend=CodeGenBackend(codegen_backend), debug_trail=DebugTrail(debug_trail))
    return benchmark_plan(create_converter, case_retort, model, operation)


@pytest.fixture(params=list(CodeGenBackend))
def codegen_backend(request):
    if request.param == CodeGenBackend.X86_64:
        try:
            check_native_platform()
        except RuntimeError as error:
            pytest.skip(str(error))
    return request.param.value


@pytest.mark.parametrize("debug_trail", [trail.value for trail in DebugTrail])
@pytest.mark.parametrize("workload", ["flat", "nested", "nested_fresh_keys", "nested_slots", "nested_diverse"])
def test_loading(codegen_backend, debug_trail, workload):
    plan = bench_loading(codegen_backend, debug_trail, workload)
    _, _, expected = create_case(workload)
    assert plan.func(*plan.args) == expected


@pytest.mark.parametrize("debug_trail", [trail.value for trail in DebugTrail])
@pytest.mark.parametrize("workload", ["flat", "nested", "nested_slots", "nested_polymorphic", "nested_diverse"])
def test_dumping(codegen_backend, debug_trail, workload):
    plan = bench_dumping(codegen_backend, debug_trail, workload)
    _, expected, _ = create_case(workload)
    assert plan.func(*plan.args) == expected


@pytest.mark.parametrize("operation", ["loading", "dumping"])
@pytest.mark.parametrize("workload", ["flat", "nested", "shared_graph"])
def test_creation(codegen_backend, operation, workload):
    if workload == "shared_graph":
        _, dumped, review = create_case("flat")
        branch = SharedBranch(review, review, [review], {"review": review})
        value = SharedGraph(branch, branch, [branch], {"branch": branch})
        branch_data = {"left": dumped, "right": dumped, "items": [dumped], "mapping": {"review": dumped}}
        data = {"left": branch_data, "right": branch_data, "items": [branch_data], "mapping": {"branch": branch_data}}
    else:
        _, data, value = create_case(workload)
    plan = bench_creation(codegen_backend, DebugTrail.ALL.value, workload, operation)
    function = plan.func(*plan.args)
    assert function(data if operation == "loading" else value) == (value if operation == "loading" else data)
