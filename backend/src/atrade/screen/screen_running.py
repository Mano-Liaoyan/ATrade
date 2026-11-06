"""A run of a saved screen: read the start instruments and the daily bar summary, run the 2 steps, and save the
screen result in one transaction (docs/architecture/screen.md sections 24.2 and 24.5)."""

import time
from datetime import datetime
from typing import Any

import psycopg

from atrade.foundation.bar import Bar
from atrade.foundation.clock import Clock
from atrade.foundation.instrument import Instrument
from atrade.market_data import (
    DailyBarSummary,
    read_current_us_universe_quarter,
    read_daily_bar_summaries,
    read_daily_bar_summaries_of_currency,
    read_hk_instrument_list,
    read_last_daily_bars,
    read_us_universe_members,
)
from atrade.screen import screen_store
from atrade.screen.screen_run import ScreenOutcome, ScreenRow, run_screen_steps
from atrade.watchlist import read_watchlist_instruments

MARKET_CURRENCIES = {"US": "USD", "HK": "HKD"}
UNIVERSE_SIZE = 500
CONVERSATION_FOREIGN_KEY = "screen_result_assistant_conversation_id_fkey"


class ConversationDeletedError(Exception):
    """The conversation of a run on port 8001 was deleted during the run."""


async def read_start_instruments(
    database_url: str, *, market: str, start: str, quarter_start_utc: datetime | None
) -> tuple[list[Instrument], list[DailyBarSummary] | None]:
    """The start instruments of section 24.2. `quarter_start_utc` selects the US universe (market_data.md section 8.9).
    With None, the universe is empty. `all_with_daily_bars` also gives the summary rows that its read returns, so a
    run needs no second read. The other start instruments give None."""
    currency = MARKET_CURRENCIES[market]
    if start == "all_with_daily_bars":
        summaries = await read_daily_bar_summaries_of_currency(database_url=database_url, currency=currency)
        return [summary.instrument for summary in summaries], summaries
    if start == "quarter_universe":
        if quarter_start_utc is None:
            return [], None
        members = await read_us_universe_members(
            database_url=database_url, quarter_start_utc=quarter_start_utc, top_n=UNIVERSE_SIZE
        )
        return [member.instrument for member in members], None
    if start == "hk_instrument_list":
        return await read_hk_instrument_list(database_url=database_url), None
    watchlist = await read_watchlist_instruments(database_url=database_url)
    return [instrument for instrument in watchlist if instrument.currency == currency], None


async def read_start_summaries(
    database_url: str, *, market: str, start: str, now_utc: datetime
) -> tuple[list[Instrument], list[DailyBarSummary]]:
    """The start instruments of section 24.2 and their daily bar summary rows."""
    quarter_start_utc = (
        await read_current_us_universe_quarter(database_url=database_url, now_utc=now_utc)
        if start == "quarter_universe"
        else None
    )
    instruments, summaries = await read_start_instruments(
        database_url, market=market, start=start, quarter_start_utc=quarter_start_utc
    )
    if summaries is None:
        summaries = await read_daily_bar_summaries(database_url=database_url, instruments=instruments)
    return instruments, summaries


def to_row_values(row: ScreenRow) -> tuple[str, str, str, dict[str, Any]]:
    values: dict[str, Any] = {
        "last_price": str(row.last_price),
        "average_trading_value_20": row.average_trading_value_20,
        "indicator_values": row.indicator_values,
        "percentiles": row.percentiles,
    }
    return row.instrument.symbol, row.instrument.exchange, row.instrument.currency, values


async def run_saved_screen(
    *, database_url: str, clock: Clock, screen: screen_store.ScreenRecord, assistant_conversation_id: int | None = None
) -> int | None:
    """Runs a checked screen and returns the ID of its new screen result, or None when the screen was deleted during
    the run. A run of the user has no conversation.

    Raises ConversationDeletedError when the conversation was deleted during the run."""
    run_at_utc = clock.read_now_utc()
    started = time.perf_counter()
    definition = screen.definition
    instruments, summaries = await read_start_summaries(
        database_url, market=screen.market, start=definition["start"], now_utc=run_at_utc
    )

    async def read_daily_bars(
        instruments: list[Instrument], before_utc: datetime, bar_count: int
    ) -> dict[Instrument, list[Bar]]:
        return await read_last_daily_bars(
            database_url=database_url, instruments=instruments, before_utc=before_utc, bar_count=bar_count
        )

    outcome: ScreenOutcome = await run_screen_steps(
        definition=definition, start_instruments=instruments, summaries=summaries, read_daily_bars=read_daily_bars
    )
    new_result = screen_store.NewScreenResult(
        screen_id=screen.id,
        run_at_utc=run_at_utc,
        definition=definition,
        market=screen.market,
        daily_bars_date=outcome.daily_bars_date,
        run_seconds=time.perf_counter() - started,
        start_count=outcome.start_count,
        after_filters_count=outcome.after_filters_count,
        after_indicator_conditions_count=outcome.after_indicator_conditions_count,
        rows=[to_row_values(row) for row in outcome.rows],
        exclusions=[
            (
                exclusion.instrument.symbol,
                exclusion.instrument.exchange,
                exclusion.instrument.currency,
                exclusion.reason,
            )
            for exclusion in outcome.exclusions
        ],
        assistant_conversation_id=assistant_conversation_id,
    )
    async with await psycopg.AsyncConnection.connect(database_url) as connection:
        try:
            screen_result_id = await screen_store.insert_screen_result(connection, new_result)
        except psycopg.errors.ForeignKeyViolation as error:
            # readability-exception: PostgreSQL reports a deleted screen or conversation only as an error.
            if error.diag.constraint_name == CONVERSATION_FOREIGN_KEY:
                raise ConversationDeletedError from error
            return None
        await connection.commit()
    return screen_result_id
