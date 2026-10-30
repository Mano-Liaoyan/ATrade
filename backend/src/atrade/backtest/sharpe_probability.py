"""PSR(0) and DSR (docs/architecture/backtest.md section 10.9.5; Bailey and López de Prado, 2012 and 2014).

They use the daily Sharpe ratio, not annualized, and `statistics.NormalDist` for `Φ` and `Φ⁻¹` (no numpy, no scipy).
"""

import math
import statistics
from collections.abc import Sequence
from decimal import Decimal
from typing import Literal

PERCENT_STEP = Decimal("0.01")
MIN_DAILY_RETURNS = 60
FEWER_THAN_60_DAILY_RETURNS = "Fewer than 60 daily returns"
NO_STANDARD_DEVIATION = "The standard deviation of the daily returns is 0"
EULER_MASCHERONI = 0.5772156649015329
LIKELY_REAL_PERCENT = Decimal(95)
UNCERTAIN_PERCENT = Decimal(50)
STANDARD_NORMAL = statistics.NormalDist()

type SharpeProbabilityStatus = Literal["likely_real", "uncertain", "likely_luck"]


def calculate_daily_sharpe(daily_returns: Sequence[Decimal]) -> float | None:
    """`mean / sample stdev` of the daily returns. None with fewer than 2 returns or a standard deviation of 0."""
    if len(daily_returns) < 2:  # noqa: PLR2004 - a sample standard deviation needs 2 values.
        return None
    returns = [float(daily_return) for daily_return in daily_returns]
    standard_deviation = statistics.stdev(returns)
    if standard_deviation == 0:
        return None
    return statistics.mean(returns) / standard_deviation


def find_sharpe_probability_reason(daily_returns: Sequence[Decimal]) -> str | None:
    """The reason why the daily returns give no PSR or DSR, or None when they give a value."""
    if len(daily_returns) < MIN_DAILY_RETURNS:
        return FEWER_THAN_60_DAILY_RETURNS
    if calculate_daily_sharpe(daily_returns) is None:
        return NO_STANDARD_DEVIATION
    return None


def calculate_sharpe_probability(daily_returns: Sequence[Decimal], threshold_sharpe: float) -> Decimal | None:
    """`PSR(SR*) = Φ((SR − SR*) × sqrt(n − 1) / sqrt(1 − γ3 × SR + (γ4 − 1) / 4 × SR²))` as a percent with 2
    decimal places. `γ3` and `γ4` are the skewness and the kurtosis (not the excess kurtosis) from the population
    moments of the returns."""
    sharpe = calculate_daily_sharpe(daily_returns)
    if len(daily_returns) < MIN_DAILY_RETURNS or sharpe is None:
        return None
    returns = [float(daily_return) for daily_return in daily_returns]
    mean_return = statistics.mean(returns)
    second_moment = statistics.mean((value - mean_return) ** 2 for value in returns)
    third_moment = statistics.mean((value - mean_return) ** 3 for value in returns)
    fourth_moment = statistics.mean((value - mean_return) ** 4 for value in returns)
    skewness = third_moment / second_moment**1.5
    kurtosis = fourth_moment / second_moment**2
    variance_factor = 1 - skewness * sharpe + (kurtosis - 1) / 4 * sharpe**2
    if variance_factor <= 0:
        # Not reachable with real data: the factor is at least (γ3 × SR / 2 − 1)², which is 0 only on one line.
        return None
    score = (sharpe - threshold_sharpe) * math.sqrt(len(returns) - 1) / math.sqrt(variance_factor)
    return Decimal(str(STANDARD_NORMAL.cdf(score) * 100)).quantize(PERCENT_STEP)


def calculate_probabilistic_sharpe(*, daily_returns: Sequence[Decimal]) -> Decimal | None:
    """PSR(0): the probability in percent that the real Sharpe ratio is above 0. None with fewer than 60 daily
    returns or a standard deviation of 0."""
    return calculate_sharpe_probability(daily_returns, 0.0)


def calculate_deflated_sharpe(
    *, daily_returns: Sequence[Decimal], trial_sharpe_ratios: Sequence[Decimal | float]
) -> Decimal | None:
    """DSR: the PSR with the threshold `SR* = sqrt(V) × ((1 − γ) × Φ⁻¹(1 − 1/N) + γ × Φ⁻¹(1 − 1/(N × e)))`.

    `trial_sharpe_ratios` are the daily Sharpe ratios of the N trials, this backtest too. `V` is their sample
    variance. `V` needs 2 trials: with fewer, the threshold is 0 and the DSR is the PSR(0).
    """
    trial_count = len(trial_sharpe_ratios)
    if trial_count < 2:  # noqa: PLR2004 - a sample variance needs 2 values.
        return calculate_probabilistic_sharpe(daily_returns=daily_returns)
    variance = statistics.variance([float(sharpe) for sharpe in trial_sharpe_ratios])
    expected_maximum = (1 - EULER_MASCHERONI) * STANDARD_NORMAL.inv_cdf(
        1 - 1 / trial_count
    ) + EULER_MASCHERONI * STANDARD_NORMAL.inv_cdf(1 - 1 / (trial_count * math.e))
    return calculate_sharpe_probability(daily_returns, math.sqrt(variance) * expected_maximum)


def find_sharpe_probability_status(percent: Decimal | None) -> SharpeProbabilityStatus | None:
    """95 % or more is "likely_real", 50 % to below 95 % is "uncertain", below 50 % is "likely_luck"."""
    if percent is None:
        return None
    if percent >= LIKELY_REAL_PERCENT:
        return "likely_real"
    if percent >= UNCERTAIN_PERCENT:
        return "uncertain"
    return "likely_luck"
