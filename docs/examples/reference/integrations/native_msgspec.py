import datetime

from msgspec import Struct

from adaptix import Retort
from adaptix.integrations.msgspec import native_msgspec


class Music(Struct):
    released: datetime.date
    composition: str


data = {
    "released": datetime.date(2007,1,20),
    "composition": "Espacio de silencio",
}

retort = Retort(
    recipe=[
        native_msgspec(Music, to_builtins={"builtin_types":[datetime.date]}),
    ],
)

assert data == retort.dump(
    Music(
        datetime.date(2007, 1, 20),
        "Espacio de silencio",
    ),
)
