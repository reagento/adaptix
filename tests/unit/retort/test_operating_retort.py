from dataclasses import dataclass
from typing import List

from tests_helpers import raises_exc, requires, with_cause, with_notes

from adaptix import AggregateCannotProvide, CannotProvide, NoSuitableProvider, Retort
from adaptix._internal.feature_requirement import HAS_STD_CLASSES_GENERICS
from adaptix.conversion import get_converter


def test_cannot_produce_loader():
    retort = Retort()

    @dataclass
    class Stub:
        f1: int
        f2: memoryview
        f3: memoryview

    raises_exc(
        with_cause(
            NoSuitableProvider(f"Cannot produce loader for type {Stub}"),
            with_notes(
                AggregateCannotProvide(
                    "Cannot create loader for model. Loaders for some fields cannot be created",
                    [
                        with_notes(
                            CannotProvide(
                                "There is no provider that can create specified loader",
                                is_terminal=False,
                                is_demonstrative=True,
                            ),
                            f"Exception was raised while processing field 'f2' of {Stub}",
                            "Location: type=<class 'memoryview'>, field_id='f2',"
                            " default=NoDefault(), metadata=mappingproxy({}), is_required=True",
                        ),
                        with_notes(
                            CannotProvide(
                                "There is no provider that can create specified loader",
                                is_terminal=False,
                                is_demonstrative=True,
                            ),
                            f"Exception was raised while processing field 'f3' of {Stub}",
                            "Location: type=<class 'memoryview'>, field_id='f3',"
                            " default=NoDefault(), metadata=mappingproxy({}), is_required=True",
                        ),
                    ],
                    is_terminal=True,
                    is_demonstrative=True,
                ),
                f"Location: type={Stub}",
            ),
        ),
        lambda: retort.get_loader(Stub),
    )


def test_cannot_produce_dumper():
    retort = Retort()

    @dataclass
    class Stub:
        f1: int
        f2: memoryview
        f3: memoryview

    raises_exc(
        with_cause(
            NoSuitableProvider(f"Cannot produce dumper for type {Stub}"),
            with_notes(
                AggregateCannotProvide(
                    "Cannot create dumper for model. Dumpers for some fields cannot be created",
                    [
                        with_notes(
                            CannotProvide(
                                "There is no provider that can create specified dumper",
                                is_terminal=False,
                                is_demonstrative=True,
                            ),
                            f"Exception was raised while processing field 'f2' of {Stub}",
                            "Location: type=<class 'memoryview'>, field_id='f2',"
                            " default=NoDefault(), metadata=mappingproxy({}),"
                            " accessor=DescriptorAccessor(attr_name='f2', access_error=None)",
                        ),
                        with_notes(
                            CannotProvide(
                                "There is no provider that can create specified dumper",
                                is_terminal=False,
                                is_demonstrative=True,
                            ),
                            f"Exception was raised while processing field 'f3' of {Stub}",
                            "Location: type=<class 'memoryview'>, field_id='f3',"
                            " default=NoDefault(), metadata=mappingproxy({}),"
                            " accessor=DescriptorAccessor(attr_name='f3', access_error=None)",
                        ),
                    ],
                    is_terminal=True,
                    is_demonstrative=True,
                ),
                f"Location: type={Stub}",
            ),
        ),
        lambda: retort.get_dumper(Stub),
    )


def test_cannot_produce_converter_no_linking_required():
    @dataclass
    class Book:
        title: str
        price: int

    @dataclass
    class BookDTO:
        title: str
        price: int
        author: str

    raises_exc(
        with_cause(
            NoSuitableProvider(
                f"Cannot produce converter for"
                f" <Signature (src: {Book.__module__}.{Book.__qualname__}, /)"
                f" -> {BookDTO.__module__}.{BookDTO.__qualname__}>",
            ),
            AggregateCannotProvide(
                "Linkings for some fields are not found",
                [
                    with_notes(
                        CannotProvide(
                            f"Cannot find paired field of `{BookDTO.__qualname__}.author` for linking",
                            is_terminal=False,
                            is_demonstrative=True,
                        ),
                        "Note: This is a required filed, so it must take value",
                    ),
                ],
                is_terminal=True,
                is_demonstrative=True,
            ),
        ),
        lambda: get_converter(Book, BookDTO),
    )


def test_cannot_produce_converter_no_linking_optional():
    @dataclass
    class Book:
        title: str
        price: int

    @dataclass
    class BookDTO:
        title: str
        price: int
        author: str = ""

    raises_exc(
        with_cause(
            NoSuitableProvider(
                f"Cannot produce converter for"
                f" <Signature (src: {Book.__module__}.{Book.__qualname__}, /)"
                f" -> {BookDTO.__module__}.{BookDTO.__qualname__}>",
            ),
            AggregateCannotProvide(
                "Linkings for some fields are not found",
                [
                    with_notes(
                        CannotProvide(
                            f"Cannot find paired field of `{BookDTO.__qualname__}.author` for linking",
                            is_terminal=False,
                            is_demonstrative=True,
                        ),
                        "Note: Current policy forbids unlinked optional fields,"
                        " so you need to link it to another field"
                        " or explicitly confirm the desire to skipping using `allow_unlinked_optional`",
                    ),
                ],
                is_terminal=True,
                is_demonstrative=True,
            ),
        ),
        lambda: get_converter(Book, BookDTO),
    )


def test_cannot_produce_converter_no_coercer():
    @dataclass
    class Book:
        title: str
        price: int
        author: int

    @dataclass
    class BookDTO:
        title: str
        price: int
        author: str

    raises_exc(
        with_cause(
            NoSuitableProvider(
                f"Cannot produce converter for"
                f" <Signature (src: {Book.__module__}.{Book.__qualname__}, /)"
                f" -> {BookDTO.__module__}.{BookDTO.__qualname__}>",
            ),
            AggregateCannotProvide(
                "Coercers for some linkings are not found",
                [
                    CannotProvide(
                        f"Cannot find coercer for linking"
                        f" `{Book.__qualname__}.author: int -> {BookDTO.__qualname__}.author: str`",
                        is_terminal=False,
                        is_demonstrative=True,
                    ),
                ],
                is_terminal=True,
                is_demonstrative=True,
            ),
        ),
        lambda: get_converter(Book, BookDTO),
    )


def test_cannot_produce_converter_no_coercer_complex_type():
    @dataclass
    class Book:
        title: str
        price: int
        authors: List[str]

    @dataclass
    class BookDTO:
        title: str
        price: int
        authors: List[int]

    raises_exc(
        with_cause(
            NoSuitableProvider(
                f"Cannot produce converter for"
                f" <Signature (src: {Book.__module__}.{Book.__qualname__}, /)"
                f" -> {BookDTO.__module__}.{BookDTO.__qualname__}>",
            ),
            AggregateCannotProvide(
                "Coercers for some linkings are not found",
                [
                    CannotProvide(
                        f"Cannot find coercer for linking"
                        f" `{Book.__qualname__}.authors: List[str] -> {BookDTO.__qualname__}.authors: List[int]`",
                        is_terminal=False,
                        is_demonstrative=True,
                    ),
                ],
                is_terminal=True,
                is_demonstrative=True,
            ),
        ),
        lambda: get_converter(Book, BookDTO),
    )


@requires(HAS_STD_CLASSES_GENERICS)
def test_cannot_produce_converter_no_coercer_complex_builtin_type():
    @dataclass
    class Book:
        title: str
        price: int
        authors: list[str]

    @dataclass
    class BookDTO:
        title: str
        price: int
        authors: list[int]

    raises_exc(
        with_cause(
            NoSuitableProvider(
                f"Cannot produce converter for"
                f" <Signature (src: {Book.__module__}.{Book.__qualname__}, /)"
                f" -> {BookDTO.__module__}.{BookDTO.__qualname__}>",
            ),
            AggregateCannotProvide(
                "Coercers for some linkings are not found",
                [
                    CannotProvide(
                        f"Cannot find coercer for linking"
                        f" `{Book.__qualname__}.authors: list[str] -> {BookDTO.__qualname__}.authors: list[int]`",
                        is_terminal=False,
                        is_demonstrative=True,
                    ),
                ],
                is_terminal=True,
                is_demonstrative=True,
            ),
        ),
        lambda: get_converter(Book, BookDTO),
    )
