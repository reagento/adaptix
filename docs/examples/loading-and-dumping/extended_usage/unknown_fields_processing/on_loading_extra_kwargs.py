from adaptix import ExtraKwargs, Retort, name_mapping


class Book:
    def __init__(self, title: str, price: int, **kwargs):
        self.title = title
        self.price = price
        self.kwargs = kwargs

    def __eq__(self, other):
        return (
            self.title == other.title
            and self.price == other.price
            and self.kwargs == other.kwargs
        )


data = {
    "title": "Fahrenheit 451",
    "price": 100,
    "unknown1": 1,
    "unknown2": 2,
}

retort = Retort(
    recipe=[
        name_mapping(Book, extra_in=ExtraKwargs()),
    ],
)

book = retort.load(data, Book)
assert book == Book(title="Fahrenheit 451", price=100, unknown1=1, unknown2=2)
