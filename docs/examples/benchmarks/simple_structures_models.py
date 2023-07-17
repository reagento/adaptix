from dataclasses import dataclass
from typing import List


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
    reviews: List[Review]  # contains 100 items
