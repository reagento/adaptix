from datetime import datetime

from adaptix import Retort, dumper, loader, name_mapping

from .models import Forecast, Weather

OPEN_WEATHER_RETORT = Retort(
    recipe=[
        name_mapping(
            Forecast,
            map={
                'timestamp': 'dt',
            },
        ),
        name_mapping(
            Weather,
            map={
                'icon_id': 'icon',
                'name': 'main',
            },
        ),
        name_mapping(
            omit_default=True,
        ),
        loader(datetime, datetime.fromtimestamp),  # default dumper and loader requires isoformat strings
        dumper(datetime, datetime.timestamp),
    ]
)
