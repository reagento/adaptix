from datetime import datetime

from dataclass_factory import Retort, dumper, loader

base_retort = Retort(
    recipe=[
        loader(datetime, datetime.fromtimestamp),
        dumper(datetime, datetime.timestamp),
    ],
)

specific_retort1 = base_retort.extend(
    recipe=[
        loader(bytes, bytes.hex),
        loader(bytes, bytes.fromhex),
    ],
)

# same as

specific_retort2 = Retort(
    recipe=[
        loader(bytes, bytes.hex),
        loader(bytes, bytes.fromhex),
        loader(datetime, datetime.fromtimestamp),
        dumper(datetime, datetime.timestamp),
    ],
)
