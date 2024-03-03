from datetime import datetime, timezone

from .models import Alert, Forecast, ForecastPack, Weather
from .retort import OPEN_WEATHER_RETORT

# subset of official example
OFFICIAL_EXAMPLE_DUMPED = {
    "lat": 39.31,
    "lon": -74.5,
    "timezone": "America/New_York",
    "timezone_offset": -18000,
    "alerts": [
        {
            "description": "...",
            "end": 1646380800.0,
            "event": "Small Craft Advisory",
            "sender_name": "NWS Philadelphia - Mount Holly (New Jersey, Delaware, Southeastern Pennsylvania)",
            "start": 1646344800.0,
        },
    ],
    "current": {
        "clouds": 40,
        "dew_point": 275.99,
        "dt": 1646318698.0,
        "weather": [
            {
                "description": "scattered clouds",
                "icon": "03d",
                "id": 802,
                "main": "Clouds",
            },
        ],
        "sunrise": 1646306882.0,
        "sunset": 1646347929.0,
    },
    "daily": [
        {
            "clouds": 49,
            "dew_point": 273.12,
            "dt": 1646326800.0,
            "weather": [
                {
                    "description": "light rain",
                    "icon": "10d",
                    "id": 500,
                    "main": "Rain",
                },
            ],
            "sunrise": 1646306882.0,
            "sunset": 1646347929.0,
        },
    ],
    "hourly": [
        {
            "clouds": 52,
            "dew_point": 276.16,
            "dt": 1646316000.0,
            "weather": [
                {
                    "description": "broken clouds",
                    "icon": "04d",
                    "id": 803,
                    "main": "Clouds",
                },
            ],
        },
    ],
}
OFFICIAL_EXAMPLE_LOADED = ForecastPack(
    lat=39.31,
    lon=-74.5,
    timezone="America/New_York",
    timezone_offset=-18000,
    current=Forecast(
        timestamp=datetime(2022, 3, 3, 14, 44, 58, tzinfo=timezone.utc),
        weather=[
            Weather(
                id=802,
                name="Clouds",
                description="scattered clouds",
                icon_id="03d",
            ),
        ],
        clouds=40,
        dew_point=275.99,
        sunrise=datetime(2022, 3, 3, 11, 28, 2, tzinfo=timezone.utc),
        sunset=datetime(2022, 3, 3, 22, 52, 9, tzinfo=timezone.utc),
    ),
    hourly=[
        Forecast(
            timestamp=datetime(2022, 3, 3, 14, 0, tzinfo=timezone.utc),
            weather=[
                Weather(id=803, name="Clouds", description="broken clouds", icon_id="04d"),
            ],
            clouds=52,
            dew_point=276.16,
            sunrise=None,
            sunset=None,
        ),
    ],
    daily=[
        Forecast(
            timestamp=datetime(2022, 3, 3, 17, 0, tzinfo=timezone.utc),
            weather=[
                Weather(id=500, name="Rain", description="light rain", icon_id="10d"),
            ],
            clouds=49,
            dew_point=273.12,
            sunrise=datetime(2022, 3, 3, 11, 28, 2, tzinfo=timezone.utc),
            sunset=datetime(2022, 3, 3, 22, 52, 9, tzinfo=timezone.utc),
        ),
    ],
    alerts=[
        Alert(
            sender_name="NWS Philadelphia - Mount Holly (New Jersey, Delaware, Southeastern Pennsylvania)",
            event="Small Craft Advisory",
            start=datetime(2022, 3, 3, 22, 0, tzinfo=timezone.utc),
            end=datetime(2022, 3, 4, 8, 0, tzinfo=timezone.utc),
            description="...",
        ),
    ],
)


def test_official_example_loading():
    assert OPEN_WEATHER_RETORT.load(OFFICIAL_EXAMPLE_DUMPED, ForecastPack) == OFFICIAL_EXAMPLE_LOADED


def test_official_example_dumping():
    assert OPEN_WEATHER_RETORT.dump(OFFICIAL_EXAMPLE_LOADED) == OFFICIAL_EXAMPLE_DUMPED
