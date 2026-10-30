"""The probabilistic and the deflated Sharpe ratio of docs/architecture/backtest.md section 10.9.5.

The expected values are calculated by hand from the formulas of the specification (Bailey and López de Prado,
2012 and 2014). `Φ` values come from a table of the standard normal distribution.
"""

import re
import tomllib
from decimal import Decimal
from pathlib import Path

import pytest

from atrade.backtest import (
    calculate_deflated_sharpe,
    calculate_probabilistic_sharpe,
    find_sharpe_probability_status,
)

# 30 days of +2 % and 30 days of -1 %.
#   mean = (30 × 0.02 − 30 × 0.01) / 60 = 0.005
#   sample stdev = sqrt(60 × 0.015² / 59) = 0.0151266
#   SR = 0.005 / 0.0151266 = 0.330544
#   The returns are symmetric about the mean: γ3 = 0, γ4 = 0.015⁴ / (0.015²)² = 1, so the denominator is 1.
#   PSR(0) = Φ(0.330544 × sqrt(59)) = Φ(2.53896) = 0.99444
SYMMETRIC_RETURNS = [Decimal("0.02"), Decimal("-0.01")] * 30


def test_probabilistic_sharpe_of_symmetric_returns_has_the_hand_calculated_value() -> None:
    assert calculate_probabilistic_sharpe(daily_returns=SYMMETRIC_RETURNS) == Decimal("99.44")


def test_probabilistic_sharpe_uses_the_skewness_and_the_kurtosis() -> None:
    # 50 days of +1 % and 10 days of -3 %.
    #   mean = (0.50 − 0.30) / 60 = 0.0033333; the deviations are +0.0066667 (50 times) and −0.0333333 (10 times).
    #   m2 = (50 × 0.0066667² + 10 × 0.0333333²) / 60 = 2.22222e-4
    #   m3 = (50 × 0.0066667³ − 10 × 0.0333333³) / 60 = −5.92593e-6, γ3 = m3 / m2^1.5 = −1.78885
    #   m4 = (50 × 0.0066667⁴ + 10 × 0.0333333⁴) / 60 = 2.07407e-7, γ4 = m4 / m2² = 4.2
    #   sample stdev = sqrt(60 × m2 / 59) = 0.0150329, SR = 0.0033333 / 0.0150329 = 0.221736
    #   denominator = sqrt(1 + 1.78885 × 0.221736 + 3.2 / 4 × 0.221736²) = sqrt(1.43598) = 1.19832
    #   PSR(0) = Φ(0.221736 × sqrt(59) / 1.19832) = Φ(1.42131) = 0.92239
    returns = [Decimal("0.01")] * 50 + [Decimal("-0.03")] * 10

    assert calculate_probabilistic_sharpe(daily_returns=returns) == Decimal("92.24")


def test_deflated_sharpe_has_the_hand_calculated_value() -> None:
    # N = 2 trials with the daily Sharpe ratios 0.1 and 0.3: V = ((0.1 − 0.2)² + (0.3 − 0.2)²) / 1 = 0.02.
    #   Φ⁻¹(1 − 1/2) = 0, Φ⁻¹(1 − 1/(2e)) = Φ⁻¹(0.816060) = 0.900453
    #   SR* = sqrt(0.02) × (0.422784 × 0 + 0.577216 × 0.900453) = 0.141421 × 0.519756 = 0.0735047
    #   DSR = Φ((0.330544 − 0.0735047) × sqrt(59)) = Φ(1.97433) = 0.97583
    deflated = calculate_deflated_sharpe(
        daily_returns=SYMMETRIC_RETURNS, trial_sharpe_ratios=[Decimal("0.1"), Decimal("0.3")]
    )

    assert deflated == Decimal("97.58")


def test_deflated_sharpe_with_fewer_than_2_trial_sharpe_ratios_is_the_probabilistic_sharpe() -> None:
    # V needs 2 trials. With 1 trial, V is 0 and the threshold is 0.
    deflated = calculate_deflated_sharpe(daily_returns=SYMMETRIC_RETURNS, trial_sharpe_ratios=[Decimal("0.3")])

    assert deflated == Decimal("99.44")


def test_fewer_than_60_daily_returns_have_no_value() -> None:
    returns = SYMMETRIC_RETURNS[:59]

    assert calculate_probabilistic_sharpe(daily_returns=returns) is None
    assert (
        calculate_deflated_sharpe(daily_returns=returns, trial_sharpe_ratios=[Decimal("0.1"), Decimal("0.3")]) is None
    )


def test_daily_returns_without_a_change_have_no_value() -> None:
    assert calculate_probabilistic_sharpe(daily_returns=[Decimal("0.01")] * 60) is None


@pytest.mark.parametrize(
    ("percent", "status"),
    [
        (Decimal("100.00"), "likely_real"),
        (Decimal("95.00"), "likely_real"),
        (Decimal("94.99"), "uncertain"),
        (Decimal("50.00"), "uncertain"),
        (Decimal("49.99"), "likely_luck"),
        (Decimal("0.00"), "likely_luck"),
    ],
)
def test_status_thresholds(percent: Decimal, status: str) -> None:
    assert find_sharpe_probability_status(percent) == status


def test_no_value_has_no_status() -> None:
    assert find_sharpe_probability_status(None) is None


def test_the_backend_has_no_numpy_and_no_scipy() -> None:
    # Section 10.9.5: `statistics.NormalDist` is sufficient. numpy is only a dependency of other packages (uv.lock).
    backend_directory = Path(__file__).parents[2]
    project = tomllib.loads((backend_directory / "pyproject.toml").read_text())
    requirements = [
        *project["project"]["dependencies"],
        *(requirement for group in project.get("dependency-groups", {}).values() for requirement in group),
    ]
    names = {re.split(r"[^A-Za-z0-9_.-]", str(requirement), maxsplit=1)[0].lower() for requirement in requirements}
    imports = [
        path
        for path in (backend_directory / "src" / "atrade").rglob("*.py")
        if re.search(r"^\s*(import|from)\s+(numpy|scipy)\b", path.read_text(), re.MULTILINE)
    ]

    assert not names & {"numpy", "scipy"}
    assert imports == []
