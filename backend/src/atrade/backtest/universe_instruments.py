"""The Instruments tab of a multi-instrument backtest: one row for each universe member
(docs/architecture/backtest.md section 10.10.7)."""

from dataclasses import dataclass
from decimal import Decimal

from atrade.backtest.backtest_metrics import (
    BacktestTrade,
    InstrumentKey,
    find_instrument_key,
    find_round_trips,
    walk_instrument_round_trips,
)

type MemberKey = tuple[str, str]


@dataclass(frozen=True)
class UniverseInstrument:
    """`net_profit_usd` sums the round trips that ended, after commissions. `quarter_count` counts the universe
    periods in which the instrument is a member."""

    symbol: str
    exchange: str
    trade_count: int
    net_profit_usd: Decimal
    quarter_count: int


def summarize_instruments(
    trades: list[BacktestTrade], quarter_counts: dict[MemberKey, int]
) -> list[UniverseInstrument]:
    """One row for each member, by symbol."""
    trades_by_member: dict[MemberKey, list[BacktestTrade]] = {}
    for trade in trades:
        if trade.symbol is not None and trade.exchange is not None:
            trades_by_member.setdefault((trade.symbol, trade.exchange), []).append(trade)
    instruments: list[UniverseInstrument] = []
    for (symbol, exchange), quarter_count in sorted(quarter_counts.items()):
        member_trades = trades_by_member.get((symbol, exchange), [])
        instruments.append(
            UniverseInstrument(
                symbol=symbol,
                exchange=exchange,
                trade_count=len(member_trades),
                net_profit_usd=sum(
                    (round_trip.profit_usd for round_trip in find_round_trips(member_trades)), Decimal(0)
                ),
                quarter_count=quarter_count,
            )
        )
    return instruments


def find_round_trip_net_profits(trades: list[BacktestTrade]) -> list[Decimal | None]:
    """For each trade, in the order of `trades`: the net profit after commissions of the round trip that the trade
    ends, else None. The round trip rule of `summarize_instruments` (docs/architecture/indicator.md section 23.9.9)."""
    trades_by_instrument: dict[InstrumentKey, list[BacktestTrade]] = {}
    for trade in trades:
        trades_by_instrument.setdefault(find_instrument_key(trade), []).append(trade)
    # By object identity: two trades can be equal.
    net_profits: dict[int, Decimal] = {
        id(trade): round_trip.profit_usd
        for instrument_trades in trades_by_instrument.values()
        for trade, round_trip in walk_instrument_round_trips(instrument_trades)
        if round_trip is not None
    }
    return [net_profits.get(id(trade)) for trade in trades]
