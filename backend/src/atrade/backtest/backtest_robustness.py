"""The robustness checks of a backtest that the detail route calculates at each read (docs/architecture/backtest.md
section 10.9.5): the trial count and the probabilistic or deflated Sharpe ratio.

A later backtest changes the trial count, so these values are not saved.
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import Literal

import psycopg

from atrade.backtest import backtest_store
from atrade.backtest.backtest_metrics import EquityPoint, calculate_daily_returns
from atrade.backtest.backtest_store import BacktestRow
from atrade.backtest.sharpe_probability import (
    SharpeProbabilityStatus,
    calculate_daily_sharpe,
    calculate_deflated_sharpe,
    calculate_probabilistic_sharpe,
    find_sharpe_probability_reason,
    find_sharpe_probability_status,
)
from atrade.strategy import read_strategy_versions

type SharpeProbabilityKind = Literal["probabilistic", "deflated"]


@dataclass(frozen=True)
class Robustness:
    trial_count: int
    sharpe_probability_percent: Decimal | None
    sharpe_probability_kind: SharpeProbabilityKind
    sharpe_probability_status: SharpeProbabilityStatus | None
    missing_reasons: dict[str, str]


async def read_trial_sharpe_ratios(*, database_url: str, strategy_id: int, row: BacktestRow) -> list[float | None]:
    """The daily Sharpe ratio of each trial: each finished backtest of the strategy (all versions), the instrument or
    universe, and the bar period of `row`. A trial with fewer than 2 daily returns or a standard deviation of 0 has
    None."""
    async with await psycopg.AsyncConnection.connect(database_url) as connection:
        finished = await backtest_store.select_finished_backtests_of(connection, row)
        # Section 6.3: no JOIN with the strategy tables. The strategy capability gives the strategy of each version.
        versions = await read_strategy_versions(
            database_url=database_url, strategy_version_ids=[trial.strategy_version_id for trial in finished]
        )
        trials = [
            trial
            for trial in finished
            if trial.strategy_version_id in versions and versions[trial.strategy_version_id].strategy_id == strategy_id
        ]
        equity_curves = await backtest_store.select_equity_curves(connection, [trial.id for trial in trials])
    return [
        calculate_daily_sharpe(
            calculate_daily_returns(start_capital_usd=trial.paper_capital_usd, equity_curve=equity_curves[trial.id])
        )
        for trial in trials
    ]


async def read_robustness(
    *, database_url: str, row: BacktestRow, strategy_id: int, equity_curve: list[EquityPoint]
) -> Robustness:
    """PSR(0) when the trial count is 1 or less, else the DSR. The DSR uses only the trials with a daily Sharpe
    ratio for the variance of the Sharpe ratios and for N."""
    trial_sharpe_ratios = await read_trial_sharpe_ratios(database_url=database_url, strategy_id=strategy_id, row=row)
    daily_returns = calculate_daily_returns(start_capital_usd=row.paper_capital_usd, equity_curve=equity_curve)
    trial_count = len(trial_sharpe_ratios)
    if trial_count <= 1:
        kind: SharpeProbabilityKind = "probabilistic"
        percent = calculate_probabilistic_sharpe(daily_returns=daily_returns)
    else:
        kind = "deflated"
        percent = calculate_deflated_sharpe(
            daily_returns=daily_returns,
            trial_sharpe_ratios=[sharpe for sharpe in trial_sharpe_ratios if sharpe is not None],
        )
    reason = find_sharpe_probability_reason(daily_returns)
    return Robustness(
        trial_count=trial_count,
        sharpe_probability_percent=percent,
        sharpe_probability_kind=kind,
        sharpe_probability_status=find_sharpe_probability_status(percent),
        missing_reasons={} if reason is None else {"sharpe_probability_percent": reason},
    )
