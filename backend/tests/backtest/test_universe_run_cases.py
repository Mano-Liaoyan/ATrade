"""Multi-instrument rule builder cases on the real engine, without the HTTP routes: `run_universe` with the bars of
each case (docs/architecture/strategy.md section 9.8.6, docs/architecture/backtest.md section 10.10)."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

from atrade.backtest import BacktestTrade, EquityPoint
from atrade.backtest.backtest_run import BacktestInputs, UniverseInputs, run_universe
from atrade.backtest.backtest_store import BacktestRequest, BacktestUniverse, UniversePeriod
from atrade.backtest.backtest_universe import MemberBars, UniverseBars
from atrade.foundation.bar import Bar, BarPeriod, TimeRange
from atrade.foundation.instrument import Instrument
from atrade.strategy.rules_code import make_rules_code
from atrade.strategy.strategy_rules import StrategyRules
from tests.backtest.universe_data import AAA, BBB, CCC
from tests.strategy.rules_examples import Json, indicator, make_universe_rules

START_UTC = datetime(2026, 1, 1, tzinfo=UTC)
SECOND_QUARTER_UTC = datetime(2026, 4, 1, tzinfo=UTC)
THIRD_QUARTER_UTC = datetime(2026, 7, 1, tzinfo=UTC)
END_UTC = datetime(2026, 9, 30, tzinfo=UTC)
LOOK_BACK_DAYS = 10
STARTING_CASH = Decimal(100000)


def day_bar(start_utc: datetime, close: float) -> Bar:
    price = Decimal(str(close))
    return Bar(start_utc=start_utc, open=price, high=price, low=price, close=price, volume=Decimal(1000000))


def days_from(first_utc: datetime, last_utc: datetime) -> list[datetime]:
    return [first_utc + timedelta(days=index) for index in range((last_utc - first_utc).days)]


def find_member_days(periods: list[UniversePeriod], member: Instrument) -> list[datetime]:
    days: list[datetime] = []
    for index, period in enumerate(periods):
        period_end_utc = periods[index + 1].start_utc if index + 1 < len(periods) else END_UTC
        if member in period.members:
            days.extend(days_from(period.start_utc, period_end_utc))
    return days


def make_member(
    instrument: Instrument, periods: list[UniversePeriod], closes: dict[datetime, float], first_close: float
) -> MemberBars:
    """`closes` holds the change days: each day has the close of the last change at or before it."""

    def find_close(day: datetime) -> float:
        known = [close for change_utc, close in sorted(closes.items()) if change_utc <= day]
        return known[-1] if known else first_close

    member_days = find_member_days(periods, instrument)
    look_back = sorted(
        {
            day - timedelta(days=count)
            for day in member_days
            if day - timedelta(days=1) not in member_days
            for count in range(1, LOOK_BACK_DAYS + 1)
        }
    )
    return MemberBars(
        instrument=instrument,
        bars=[day_bar(day, find_close(day)) for day in member_days],
        look_back_bars=[day_bar(day, find_close(day)) for day in look_back],
        open_bars=[day_bar(day, find_close(day)) for day in days_from(START_UTC, END_UTC)],
    )


def run_case(
    tmp_path: Path, rules: Json, periods: list[UniversePeriod], members: list[MemberBars]
) -> tuple[list[BacktestTrade], list[EquityPoint]]:
    code = make_rules_code(StrategyRules.model_validate(rules))
    request = BacktestRequest(
        strategy_version_id=1,
        instrument=None,
        bar_period=BarPeriod.ONE_DAY,
        time_range=TimeRange(START_UTC, END_UTC),
        paper_capital_usd=STARTING_CASH,
        universe=BacktestUniverse(kind="list", currency="USD"),
    )
    universe = UniverseInputs(periods=periods, bars=UniverseBars(members=members, bar_count_by_source={}))
    inputs = BacktestInputs(
        request=request,
        code=code,
        bars=[],
        look_back_bars=[],
        bar_count_by_source={},
        exchange_rates=None,
        universe=universe,
    )
    return run_universe(inputs, universe, STARTING_CASH, tmp_path, [])


def rank_rules(hold_count: int, period: str = "monthly") -> Json:
    return make_universe_rules(
        rank_indicator=indicator("sma", period=3), hold_count=hold_count, rebalance_period=period
    )


def test_the_equity_of_a_last_period_without_members_counts_the_sell_at_the_next_open(tmp_path: Path) -> None:
    periods = [UniversePeriod(START_UTC, [AAA]), UniversePeriod(SECOND_QUARTER_UTC, [])]
    member = make_member(AAA, periods, {SECOND_QUARTER_UTC: 130}, first_close=100)

    trades, equity_curve = run_case(tmp_path, rank_rules(hold_count=1), periods, [member])

    assert [trade.side for trade in trades] == ["BUY", "SELL"]
    # 95% of 100000 buys 950 shares at 100. They sell at 130.
    assert equity_curve[-1].equity_usd == Decimal(128500)


def find_sides(trades: list[BacktestTrade], instrument: Instrument) -> list[str]:
    return [trade.side for trade in trades if trade.symbol == instrument.symbol]


def test_a_member_that_comes_back_gets_a_new_rank(tmp_path: Path) -> None:
    periods = [
        UniversePeriod(START_UTC, [AAA, BBB]),
        UniversePeriod(SECOND_QUARTER_UTC, [BBB]),
        UniversePeriod(THIRD_QUARTER_UTC, [AAA, BBB]),
    ]
    # AAA has the best rank in the first quarter. Its close falls below BBB while it is out of the universe.
    members = [
        make_member(AAA, periods, {SECOND_QUARTER_UTC: 50}, first_close=200),
        make_member(BBB, periods, {}, first_close=100),
    ]

    trades, _ = run_case(tmp_path, rank_rules(hold_count=1), periods, members)

    assert find_sides(trades, AAA) == ["BUY", "SELL"]
    # BBB replaces AAA at the second quarter and stays. The old rank of AAA must not buy AAA again.
    assert find_sides(trades, BBB) == ["BUY"]


def test_a_rebalance_sells_a_buy_that_filled_after_its_instrument_left_the_universe(tmp_path: Path) -> None:
    periods = [UniversePeriod(START_UTC, [AAA, BBB]), UniversePeriod(SECOND_QUARTER_UTC, [AAA, CCC])]
    switch_utc = datetime(2026, 3, 25, tzinfo=UTC)
    members = [
        make_member(AAA, periods, {}, first_close=200),
        # The rebalance of 2026-03-31 sells AAA. The buy of BBB goes at the next bar, 2026-04-01 00:00, and it fills
        # after the list of the second quarter removes BBB.
        make_member(BBB, periods, {switch_utc: 300}, first_close=100),
        make_member(CCC, periods, {}, first_close=100),
    ]

    trades, equity_curve = run_case(tmp_path, rank_rules(hold_count=1, period="weekly"), periods, members)

    assert find_sides(trades, BBB) == ["BUY", "SELL"]
    # After the sell of BBB, the blocked buy of the best member can go.
    assert find_sides(trades, AAA) == ["BUY", "SELL", "BUY"]
    assert equity_curve[-1].equity_usd == STARTING_CASH


def test_a_rebalance_does_not_sell_a_position_with_an_open_sell_order_again(tmp_path: Path) -> None:
    periods = [UniversePeriod(START_UTC, [AAA, BBB]), UniversePeriod(SECOND_QUARTER_UTC, [BBB])]
    members = [
        make_member(AAA, periods, {}, first_close=200),
        make_member(BBB, periods, {}, first_close=100),
    ]
    rules = rank_rules(hold_count=1, period="quarterly")

    trades, _ = run_case(tmp_path, rules, periods, members)

    # The list sells AAA at the period start, in the same bar time as the mark of the rebalance.
    assert find_sides(trades, AAA) == ["BUY", "SELL"]
