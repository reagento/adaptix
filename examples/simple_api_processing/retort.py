from datetime import datetime, timezone

from adaptix import Retort, dumper, loader, name_mapping

from .models import Forecast, Weather

OPEN_WEATHER_RETORT = Retort(
    recipe=[
        name_mapping(
            Forecast,
            map={
                "timestamp": "dt",
            },
        ),
        name_mapping(
            Weather,
            map={
                "icon_id": "icon",
                "name": "main",
            },
        ),
        name_mapping(
            omit_default=True,
        ),
        # default dumper and loader requires isoformat strings
        loader(datetime, lambda x: datetime.fromtimestamp(x, tz=timezone.utc)),
        dumper(datetime, lambda x: x.astimezone(timezone.utc).timestamp()),
    ],
)
