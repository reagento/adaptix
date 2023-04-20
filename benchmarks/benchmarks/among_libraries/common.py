from typing import Any, Dict

_REVIEW_TEXT = """
Asimov is a must-read for any science fiction fan.
Luckily he’s been a very productive author, so there is plenty of material available.
His concepts on psychohistory and especially the Laws of Robotics are unique.
""".strip().rstrip()


def get_review_text(*, idx: int) -> str:
    return _REVIEW_TEXT + f" {idx ** 2}"


def create_dumped_book(*, reviews_count: int) -> Dict[str, Any]:
    return {
        'id': 24,
        'name': 'The End of Eternity',
        'reviews': [
            {
                'id': 482 + i ** 2,
                'title': 'Funny thing',
                'rating': 4.6,
                'text': get_review_text(idx=i),
            }
            for i in range(reviews_count)
        ],
    }


def create_book(book_cls: type, review_cls: type, *, reviews_count: int):
    return book_cls(
        id=24,
        name='The End of Eternity',
        reviews=[
            review_cls(
                id=482 + i ** 2,
                title='Funny thing',
                rating=4.6,
                content=get_review_text(idx=i),
            )
            for i in range(reviews_count)
        ],
    )
