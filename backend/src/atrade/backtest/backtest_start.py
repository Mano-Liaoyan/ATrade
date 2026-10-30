"""The start of a backtest: the checks of the request, then a queued row (docs/architecture/backtest.md 10.3).

The HTTP route of port 8000 starts a backtest without a conversation. Port 8001 starts one with the conversation ID
of the AI assistant (docs/architecture/assistant.md 25.5.1).
"""

from dataclasses import dataclass
from datetime import datetime

from atrade.backtest.backtest_access import (
    add_global_source_order,
    check_backtest_request,
    check_saved_bars,
    queue_backtest,
)
from atrade.backtest.backtest_exchange_rates import save_exchange_rates
from atrade.backtest.backtest_store import BacktestRequest, UniversePeriod
from atrade.backtest.backtest_universe import check_universe_bars
from atrade.market_data import ExchangeRateReader
from atrade.strategy import read_strategy_version


@dataclass(frozen=True)
class BacktestRefusal:
    """Why the backtest did not start. The HTTP routes answer 422 with it."""

    detail: str


async def start_backtest(  # noqa: PLR0913 readability-exception: the keywords of a start from either port.
    *,
    database_url: str,
    exchange_rate_reader: ExchangeRateReader,
    request: BacktestRequest,
    created_at_utc: datetime,
    universe_periods: list[UniversePeriod] | None = None,
    conversation_id: int | None = None,
) -> int | BacktestRefusal:
    """Queues the backtest and returns its ID, or returns why it cannot start. A multi-instrument backtest also needs
    the members of each universe period (docs/architecture/backtest.md 10.10.6)."""
    refusal = check_backtest_request(request)
    if refusal is not None:
        return BacktestRefusal(refusal)
    strategy_version = await read_strategy_version(
        database_url=database_url, strategy_version_id=request.strategy_version_id
    )
    if strategy_version is None:
        return BacktestRefusal(f"Strategy version {request.strategy_version_id} does not exist.")
    request = await add_global_source_order(database_url=database_url, request=request)
    # Refuse before the row exists: a backtest without saved bars can only fail (docs/architecture/backtest.md 10.3).
    if request.universe is None:
        missing_bars = await check_saved_bars(database_url=database_url, request=request)
    else:
        missing_bars = await check_universe_bars(
            database_url=database_url,
            request=request,
            periods=universe_periods or [],
            source_order=request.source_order or [],
        )
    if missing_bars is not None:
        return BacktestRefusal(missing_bars)
    # The child never calls IBKR, so the rates of an instrument that is not in USD are saved first (section 10.8).
    missing_rates = await save_exchange_rates(
        database_url=database_url, exchange_rate_reader=exchange_rate_reader, request=request
    )
    if missing_rates is not None:
        return BacktestRefusal(missing_rates)
    return await queue_backtest(
        database_url=database_url,
        request=request,
        created_at_utc=created_at_utc,
        universe_periods=universe_periods,
        conversation_id=conversation_id,
    )
