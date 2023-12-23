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
    "name": "Fahrenheit 451",
    "price": 100,
    "title": "Celsius 232.778",
}

retort = Retort(
    recipe=[
        name_mapping(Book, map={'title': 'name'}),
        name_mapping(Book, extra_in=ExtraKwargs()),
    ]
)

try:
    retort.load(data, Book)
except TypeError as e:
    assert str(e).endswith("__init__() got multiple values for argument 'title'")
