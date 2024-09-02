from dataclasses import dataclass

from tests_helpers import raises_exc, with_cause, with_notes

from adaptix import AggregateCannotProvide, CannotProvide, ProviderNotFoundError
from adaptix.conversion import get_converter


def test_source_is_not_a_model():
    class Book:
        title: str
        price: int
        author: int

    @dataclass
    class BookDTO:
        title: str
        price: int
        author: int

    raises_exc(
        with_cause(
            with_notes(
                ProviderNotFoundError(
                    f"Cannot produce converter for"
                    f" <Signature (src: {Book.__module__}.{Book.__qualname__}, /)"
                    f" -> {BookDTO.__module__}.{BookDTO.__qualname__}>",
                ),
                "Note: The attached exception above contains verbose description of the problem",
            ),
            AggregateCannotProvide(
                "Cannot create top-level coercer",
                [
                    with_notes(
                        CannotProvide(
                            "Cannot find coercer",
                            is_terminal=False,
                            is_demonstrative=True,
                        ),
                        f"Linking: `{Book.__qualname__} => {BookDTO.__qualname__}`",
                        "Hint: Class `Book` is not recognized as model. Did your forget `@dataclass` decorator?"
                        " Check documentation what model kinds are supported",
                    ),
                ],
                is_terminal=True,
                is_demonstrative=True,
            ),
        ),
        lambda: get_converter(Book, BookDTO),
    )


def test_destination_is_not_a_model():
    @dataclass
    class Book:
        title: str
        price: int
        author: int

    class BookDTO:
        title: str
        price: int
        author: int

    raises_exc(
        with_cause(
            with_notes(
                ProviderNotFoundError(
                    f"Cannot produce converter for"
                    f" <Signature (src: {Book.__module__}.{Book.__qualname__}, /)"
                    f" -> {BookDTO.__module__}.{BookDTO.__qualname__}>",
                ),
                "Note: The attached exception above contains verbose description of the problem",
            ),
            AggregateCannotProvide(
                "Cannot create top-level coercer",
                [
                    with_notes(
                        CannotProvide(
                            "Cannot find coercer",
                            is_terminal=False,
                            is_demonstrative=True,
                        ),
                        f"Linking: `{Book.__qualname__} => {BookDTO.__qualname__}`",
                        "Hint: Class `BookDTO` is not recognized as model. Did your forget `@dataclass` decorator?"
                        " Check documentation what model kinds are supported",
                    ),
                ],
                is_terminal=True,
                is_demonstrative=True,
            ),
        ),
        lambda: get_converter(Book, BookDTO),
    )


def test_both_are_not_a_model():
    class Book:
        title: str
        price: int
        author: int

    class BookDTO:
        title: str
        price: int
        author: int

    raises_exc(
        with_cause(
            with_notes(
                ProviderNotFoundError(
                    f"Cannot produce converter for"
                    f" <Signature (src: {Book.__module__}.{Book.__qualname__}, /)"
                    f" -> {BookDTO.__module__}.{BookDTO.__qualname__}>",
                ),
                "Note: The attached exception above contains verbose description of the problem",
            ),
            AggregateCannotProvide(
                "Cannot create top-level coercer",
                [
                    with_notes(
                        CannotProvide(
                            "Cannot find coercer",
                            is_terminal=False,
                            is_demonstrative=True,
                        ),
                        f"Linking: `{Book.__qualname__} => {BookDTO.__qualname__}`",
                    ),
                ],
                is_terminal=True,
                is_demonstrative=True,
            ),
        ),
        lambda: get_converter(Book, BookDTO),
    )
