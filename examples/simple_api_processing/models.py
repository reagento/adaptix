from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional


@dataclass
class Weather:
    id: int
    name: str
    description: str
    icon_id: str


@dataclass
class Forecast:
    timestamp: datetime
    weather: List[Weather]

    clouds: int
    dew_point: float

    sunrise: Optional[datetime] = None
    sunset: Optional[datetime] = None


@dataclass
class Alert:
    sender_name: str
    event: str
    start: datetime
    end: datetime
    description: str


@dataclass
class ForecastPack:
    lat: float
    lon: float
    timezone: str
    timezone_offset: int

    current: Optional[Forecast] = None
    minutely: List[Forecast] = field(default_factory=list)
    hourly: List[Forecast] = field(default_factory=list)
    daily: List[Forecast] = field(default_factory=list)
    alerts: List[Alert] = field(default_factory=list)
