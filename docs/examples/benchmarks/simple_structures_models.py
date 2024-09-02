from dataclasses import dataclass


@dataclass
class Review:
    id: int
    title: str
    rating: float
    content: str  # renamed to 'text'


@dataclass
class Book:
    id: int
    name: str
    reviews: list[Review]  # contains 100 items
