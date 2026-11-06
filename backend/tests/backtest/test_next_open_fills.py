"""A market order fills at the open of the next bar (docs/architecture/backtest.md section 10.10.3).

The bars have an open that differs from the close of the bar before, so a test can tell the two prices apart.
"""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pytest

from atrade.backtest.backtest_metrics import BacktestTrade
from atrade.backtest.backtest_store import BacktestRequest, ParameterValues, UniversePeriod
from atrade.backtest.backtest_universe import MemberBars
from atrade.backtest.strategy_engine_run import StrategyRun, make_fill_warning, run_strategy_on_bars
from atrade.backtest.universe_engine_run import UniverseRun, run_universe_strategy
from atrade.foundation.bar import Bar, BarPeriod, TimeRange
from atrade.foundation.instrument import Instrument
from atrade.strategy.rules_code import make_rules_code
from atrade.strategy.strategy_rules import StrategyRules
from tests.strategy.rules_examples import condition, group, make_rules, number, price

STRATEGIES_DIRECTORY = Path(__file__).parent / "strategies"
BAR_COUNT_CODE = (STRATEGIES_DIRECTORY / "buy_and_sell_by_bar_count.py").read_text()
BRACKET_CODE = (STRATEGIES_DIRECTORY / "bracket_with_all_cash.py").read_text()
CLOSE_TWICE_CODE = (STRATEGIES_DIRECTORY / "close_position_twice.py").read_text()
FOLLOW_UNIVERSE_CODE = (STRATEGIES_DIRECTORY / "follow_universe.py").read_text()
REBALANCE_CODE = (STRATEGIES_DIRECTORY / "rebalance_in_one_bar.py").read_text()
START_UTC = datetime(2026, 3, 2, tzinfo=UTC)
OPEN_FILL_DELAY = timedelta(milliseconds=1)
WAVE = Instrument(symbol="WAVE", exchange="ARCA", currency="USD")
AAA = Instrument(symbol="AAA", exchange="NASDAQ", currency="USD")
BBB = Instrument(symbol="BBB", exchange="NYSE", currency="USD")
LOOK_BACK_BAR_COUNT = 30
HUNDRED_SHARES: ParameterValues = {"trade_quantity_shares": 100}


def make_bar(day: int, open_price: int, close: int, volume: int = 1000000) -> Bar:
    return Bar(
        start_utc=START_UTC + timedelta(days=day),
        open=Decimal(open_price),
        high=Decimal(max(open_price, close) + 1),
        low=Decimal(min(open_price, close) - 1),
        close=Decimal(close),
        volume=Decimal(volume),
    )


def find_open_time(day: int) -> datetime:
    return START_UTC + timedelta(days=day) + OPEN_FILL_DELAY


def read_fills(trades: list[BacktestTrade]) -> list[tuple[datetime, str, Decimal, Decimal]]:
    return [(trade.time_utc, trade.side, trade.price_usd, trade.quantity_shares) for trade in trades]


def run_single(
    bars: list[Bar],
    work_directory: Path,
    *,
    code: str = BAR_COUNT_CODE,
    cash: int = 100000,
    parameters: ParameterValues | None = None,
) -> tuple[list[BacktestTrade], list[str]]:
    """The strategy of `BAR_COUNT_CODE` buys at bar 3 and sells at bar 8. Returns the trades and the changed orders."""
    request = BacktestRequest(
        strategy_version_id=1,
        instrument=WAVE,
        bar_period=BarPeriod.ONE_DAY,
        time_range=TimeRange(start_utc=START_UTC, end_utc=START_UTC + timedelta(days=len(bars))),
        paper_capital_usd=Decimal(cash),
        parameters=parameters,
    )
    changed_orders: list[str] = []
    run = StrategyRun(code=code, request=request, starting_cash=Decimal(cash), bars=bars, look_back_bars=[])
    return run_strategy_on_bars(run, work_directory, changed_orders), changed_orders


def make_flat_bars(day_count: int) -> list[Bar]:
    return [make_bar(day, 100, 100) for day in range(day_count)]


def test_a_buy_fills_at_the_open_of_the_next_bar_and_not_at_the_close_of_its_bar(tmp_path: Path) -> None:
    bars = [*make_flat_bars(2), make_bar(2, 100, 120), make_bar(3, 150, 200), *make_flat_bars(9)[4:]]

    trades, changed_orders = run_single(bars, tmp_path)

    # The signal bar closes at 120. The next bar opens at 150 and closes at 200.
    assert read_fills(trades)[0] == (find_open_time(3), "BUY", Decimal("150.00"), Decimal(10))
    assert changed_orders == []


def test_an_order_on_the_last_bar_has_no_next_open_and_fills_at_the_last_close(tmp_path: Path) -> None:
    bars = [*make_flat_bars(2), make_bar(2, 100, 120)]

    trades, _ = run_single(bars, tmp_path)

    assert read_fills(trades) == [(START_UTC + timedelta(days=3), "BUY", Decimal("120.00"), Decimal(10))]


def test_a_buy_that_gaps_over_the_cash_is_reduced_and_the_run_has_a_warning(tmp_path: Path) -> None:
    bars = [*make_flat_bars(3), make_bar(3, 130, 130), make_bar(4, 130, 130)]

    trades, changed_orders = run_single(bars, tmp_path, cash=10000, parameters=HUNDRED_SHARES)

    # 100 shares cost 10000 at the close of 100, but 13000 at the open of 130. The cash pays for 76 shares.
    assert read_fills(trades) == [(find_open_time(3), "BUY", Decimal("130.00"), Decimal(76))]
    assert changed_orders == ["2026-03-05 00:00 UTC: BUY 100 WAVE reduced to 76 at 130.00"]
    assert make_fill_warning(changed_orders) == (
        "Changed orders: 1. Earliest: 2026-03-05 00:00 UTC: BUY 100 WAVE reduced to 76 at 130.00."
    )


def test_the_fill_warning_names_the_oldest_order() -> None:
    changed_orders = [
        "2026-03-06 00:00 UTC: BUY 5 AAA reduced to 4 at 10.00",
        "2026-03-05 00:00 UTC: BUY 7 BBB refused",
    ]

    assert make_fill_warning(changed_orders) == "Changed orders: 2. Earliest: 2026-03-05 00:00 UTC: BUY 7 BBB refused."


def test_a_reduced_order_above_the_open_tick_volume_does_not_end_the_run(tmp_path: Path) -> None:
    # The open tick holds 1000 shares. The engine fills the rest 1 cent higher, so the check adds 1 cent.
    bars = [*make_flat_bars(3), make_bar(3, 2, 2, volume=4000), make_bar(4, 2, 2, volume=4000)]

    trades, changed_orders = run_single(bars, tmp_path, cash=10000, parameters={"trade_quantity_shares": 9000})

    assert sum(trade.quantity_shares for trade in trades) == Decimal(4975)
    assert sum(trade.price_usd * trade.quantity_shares for trade in trades) <= Decimal(10000)
    assert changed_orders == ["2026-03-05 00:00 UTC: BUY 9000 WAVE reduced to 4975 at 2.00"]


def test_a_buy_refused_because_the_cash_pays_for_no_share_does_not_fail_the_run(tmp_path: Path) -> None:
    bars = [*make_flat_bars(3), make_bar(3, 20000, 20000), make_bar(4, 20000, 20000)]

    trades, changed_orders = run_single(bars, tmp_path, cash=10000, parameters=HUNDRED_SHARES)

    assert trades == []
    assert len(changed_orders) == 1
    assert "BUY 100 WAVE refused (NOTIONAL_EXCEEDS_FREE_BALANCE" in changed_orders[0]


def test_a_full_position_buy_on_a_day_that_closes_below_its_open_is_not_refused(tmp_path: Path) -> None:
    # The cash check uses the next open of 95, not the open of 130 of the signal bar.
    bars = [*make_flat_bars(2), make_bar(2, 130, 100), make_bar(3, 95, 90), make_bar(4, 90, 90)]

    trades, changed_orders = run_single(bars, tmp_path, cash=10000, parameters=HUNDRED_SHARES)

    assert read_fills(trades) == [(find_open_time(3), "BUY", Decimal("95.00"), Decimal(100))]
    assert changed_orders == []


def test_a_buy_on_the_last_bar_fits_the_cash_at_the_close_that_fills_it(tmp_path: Path) -> None:
    # 100 shares cost 9500 at the open of 95, but 10500 at the close of 105. The order has no next open.
    bars = [*make_flat_bars(2), make_bar(2, 95, 105)]

    trades, changed_orders = run_single(bars, tmp_path, cash=10000, parameters=HUNDRED_SHARES)

    assert read_fills(trades) == [(START_UTC + timedelta(days=3), "BUY", Decimal("105.00"), Decimal(95))]
    assert changed_orders == ["2026-03-05 00:00 UTC: BUY 100 WAVE reduced to 95 at 105.00"]


def test_a_full_cash_buy_on_a_last_bar_that_closes_below_its_open_is_not_refused(tmp_path: Path) -> None:
    bars = [*make_flat_bars(2), make_bar(2, 130, 100)]

    trades, changed_orders = run_single(bars, tmp_path, cash=10000, parameters=HUNDRED_SHARES)

    assert read_fills(trades) == [(START_UTC + timedelta(days=3), "BUY", Decimal("100.00"), Decimal(100))]
    assert changed_orders == []


def test_a_bracket_order_keeps_the_fill_at_the_close_and_stops_out_at_a_gap_through_its_stop(tmp_path: Path) -> None:
    bars = [make_bar(0, 100, 100), make_bar(1, 90, 90), make_bar(2, 90, 90)]

    trades, changed_orders = run_single(bars, tmp_path, code=BRACKET_CODE, cash=10000, parameters={"stop_price": 95.0})

    # An order list is not held: the entry fills at the close of 100. The stop is in the market before the gap.
    assert read_fills(trades) == [
        (START_UTC + timedelta(days=1), "BUY", Decimal("100.00"), Decimal(100)),
        (find_open_time(1), "SELL", Decimal("90.00"), Decimal(100)),
    ]
    assert changed_orders == []


def test_a_post_only_limit_bracket_rests_and_fills_at_its_limit_at_a_gap_down(tmp_path: Path) -> None:
    bars = [make_bar(0, 102, 102), make_bar(1, 95, 96), make_bar(2, 96, 96)]

    trades, changed_orders = run_single(
        bars, tmp_path, code=BRACKET_CODE, cash=20000, parameters={"limit_price": 100.0}
    )

    assert [(trade.side, trade.price_usd) for trade in trades] == [("BUY", Decimal("100.00"))]
    assert changed_orders == []


def test_a_stop_that_the_venue_rejects_is_in_the_fill_warning(tmp_path: Path) -> None:
    # The sell stop of 110 is above the close of 100. The position has no exit, so the run must say it.
    bars = [make_bar(0, 100, 100), make_bar(1, 100, 100), make_bar(2, 100, 100)]

    _, changed_orders = run_single(bars, tmp_path, code=BRACKET_CODE, cash=20000, parameters={"stop_price": 110.0})

    assert any("SELL 100 WAVE refused" in line for line in changed_orders)


def test_rule_code_does_not_buy_two_times_when_the_next_bar_has_no_volume(tmp_path: Path) -> None:
    code = make_rules_code(
        StrategyRules.model_validate(make_rules(group("all_of", condition(price(), "above", number(100)))))
    )
    bars = [make_bar(0, 100, 110), make_bar(1, 102, 102, volume=0), make_bar(2, 103, 104), make_bar(3, 104, 105)]

    trades, _ = run_single(bars, tmp_path, code=code)

    # The bar without volume has an open tick. The order fills before `on_bar` of that bar.
    assert {trade.side for trade in trades} == {"BUY"}
    assert sum(trade.quantity_shares for trade in trades) == Decimal(10)
    assert {trade.time_utc for trade in trades} == {find_open_time(1)}


def test_a_position_closed_two_times_sells_one_time_at_the_next_open(tmp_path: Path) -> None:
    bars = [make_bar(0, 100, 100), make_bar(1, 110, 120), make_bar(2, 130, 140), make_bar(3, 150, 160)]

    trades, _ = run_single(bars, tmp_path, code=CLOSE_TWICE_CODE)

    assert read_fills(trades) == [
        (find_open_time(1), "BUY", Decimal("110.00"), Decimal(10)),
        (find_open_time(2), "SELL", Decimal("130.00"), Decimal(10)),
    ]


@dataclass(frozen=True)
class Member:
    instrument: Instrument
    # One (open, close) for each bar from the backtest start.
    prices: list[tuple[int, int]]
    # The bars of the universe periods. The other bars are only open bars.
    member_bar_count: int


def make_member(member: Member, *, has_later_bars: bool = True) -> MemberBars:
    first_day = -LOOK_BACK_BAR_COUNT
    bars = [make_bar(day, *prices) for day, prices in enumerate(member.prices)]
    return MemberBars(
        instrument=member.instrument,
        bars=bars[: member.member_bar_count],
        look_back_bars=[make_bar(day, 100, 100) for day in range(first_day, 0)],
        open_bars=bars if has_later_bars else bars[: member.member_bar_count],
    )


def run_universe(
    members: list[MemberBars],
    periods: list[UniversePeriod],
    work_directory: Path,
    code: str = FOLLOW_UNIVERSE_CODE,
    changed_orders: list[str] | None = None,
) -> list[BacktestTrade]:
    run = UniverseRun(
        code=code,
        bar_period=BarPeriod.ONE_DAY,
        currency="USD",
        starting_cash=Decimal(100000),
        members=members,
        periods=periods,
    )
    return run_universe_strategy(run, work_directory, changed_orders)


def read_symbol_fills(trades: list[BacktestTrade]) -> set[tuple[str | None, str, Decimal, datetime]]:
    return {(trade.symbol, trade.side, trade.price_usd, trade.time_utc) for trade in trades}


@pytest.mark.parametrize("reverse_members", [False, True])
def test_all_members_of_one_rebalance_fill_at_their_next_open_in_each_member_order(
    tmp_path: Path, reverse_members: bool
) -> None:
    first = Member(AAA, [(100, 120), (150, 200), (170, 180)], 3)
    second = Member(BBB, [(50, 60), (70, 90), (80, 85)], 3)
    members = [make_member(first), make_member(second)]
    if reverse_members:
        members.reverse()

    periods = [UniversePeriod(start_utc=START_UTC, members=[AAA, BBB])]
    trades = run_universe(members, periods, tmp_path, REBALANCE_CODE)

    assert read_symbol_fills(trades) == {
        ("AAA", "BUY", Decimal("150.00"), find_open_time(1)),
        ("BBB", "BUY", Decimal("70.00"), find_open_time(1)),
    }


def test_an_order_held_for_the_last_open_of_the_data_fills_at_that_open(tmp_path: Path) -> None:
    # The bar of day 1 is outside the member periods. Only its open tick and its last close tick go to the engine.
    held = Member(AAA, [(100, 120), (150, 200)], 1)
    other = Member(BBB, [(50, 60)], 1)
    changed_orders: list[str] = []
    periods = [UniversePeriod(start_utc=START_UTC, members=[AAA, BBB])]

    trades = run_universe([make_member(held), make_member(other)], periods, tmp_path, REBALANCE_CODE, changed_orders)

    assert ("AAA", "BUY", Decimal("150.00"), find_open_time(1)) in read_symbol_fills(trades)
    assert changed_orders == []


def make_exit_periods() -> list[UniversePeriod]:
    return [
        UniversePeriod(start_utc=START_UTC, members=[AAA, BBB]),
        UniversePeriod(start_utc=START_UTC + timedelta(days=3), members=[BBB]),
    ]


def test_a_member_that_leaves_sells_at_its_next_open_outside_its_periods(tmp_path: Path) -> None:
    leaver = Member(AAA, [(100, 120), (150, 200), (170, 180), (90, 95), (91, 96)], 3)
    stayer = Member(BBB, [(50, 60), (70, 90), (80, 85), (81, 86), (82, 87)], 5)

    trades = run_universe([make_member(leaver), make_member(stayer)], make_exit_periods(), tmp_path)

    # The list of the new period comes at the end of bar 3. The real next open of AAA is the open of bar 4.
    assert ("AAA", "SELL", Decimal("90.00"), find_open_time(3)) in read_symbol_fills(trades)


def test_a_member_without_later_bars_sells_at_its_last_close_at_once(tmp_path: Path) -> None:
    leaver = Member(AAA, [(100, 120), (150, 200), (170, 180)], 3)
    stayer = Member(BBB, [(50, 60), (70, 90), (80, 85), (81, 86), (82, 87)], 5)
    members = [make_member(leaver, has_later_bars=False), make_member(stayer)]

    trades = run_universe(members, make_exit_periods(), tmp_path)

    assert ("AAA", "SELL", Decimal("180.00"), START_UTC + timedelta(days=3)) in read_symbol_fills(trades)
