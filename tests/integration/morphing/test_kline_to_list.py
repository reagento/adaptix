from dataclasses import dataclass
from decimal import Decimal

from adaptix import Retort, name_mapping


@dataclass
class Kline:
    open_time: int
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal
    close_time: int
    quote_volume: Decimal
    count: int
    taker_buy_volume: Decimal
    taker_buy_quote_volume: Decimal
    ignore: str


def test_kline():
    retort = Retort(
        recipe=[
            name_mapping(
                Kline,
                as_list=True,
            ),
        ],
    )

    data = [
        1499040000000,
        "0.01634790",
        "0.80000000",
        "0.01575800",
        "0.01577100",
        "148976.11427815",
        1499644799999,
        "2434.19055334",
        308,
        "1756.87402397",
        "28.46694368",
        "0",
    ]
    kline = retort.load(data, Kline)
    assert kline == Kline(
        open_time=1499040000000,
        open=Decimal("0.01634790"),
        high=Decimal("0.80000000"),
        low=Decimal("0.01575800"),
        close=Decimal("0.01577100"),
        volume=Decimal("148976.11427815"),
        close_time=1499644799999,
        quote_volume=Decimal("2434.19055334"),
        count=308,
        taker_buy_volume=Decimal("1756.87402397"),
        taker_buy_quote_volume=Decimal("28.46694368"),
        ignore="0",
    )
    assert retort.dump(kline) == data
