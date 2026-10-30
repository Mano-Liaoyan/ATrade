"""The Instruments tab of a multi-instrument backtest: one row for each universe member
(docs/architecture/backtest.md section 10.10.7)."""

from dataclasses import dataclass
from decimal import Decimal

from atrade.backtest.backtest_metrics import BacktestTrade, find_round_trips

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
