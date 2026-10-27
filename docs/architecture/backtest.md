# Backtest

This document is section 10 of the architecture specification
([`docs/architecture.md`](../architecture.md)). It was moved to its own file
to keep the specification shorter than 1000 lines (section 18). Terms have
the meaning that [`GLOSSARY.md`](../../GLOSSARY.md) gives them.

Sources: [Strategy editing and run isolation](https://github.com/Mano-Liaoyan/ATrade/issues/48),
[Module division](https://github.com/Mano-Liaoyan/ATrade/issues/38),
[Run a backtest and see the result](https://github.com/Mano-Liaoyan/ATrade/issues/70),
[Backtest isolation controls](https://github.com/Mano-Liaoyan/ATrade/issues/71).

## 10.1 Decisions

- A backtest request contains the strategy version, the instrument, the bar
  type, the time range, and `paper_capital_usd`. `paper_capital_usd` is
  required.
- `paper_trading` exports `fetch_paper_capital_usd()`. It returns the paper
  account balance (`NetLiquidation` in USD) after a passed paper account check.
  Otherwise it returns the local value from `settings` (section 11.5). The
  frontend uses it to fill in the backtest form.
- Each backtest runs in its own child process (`app/backtest_process.py`),
  because the NautilusTrader backtest engine blocks the event loop.
- In NautilusTrader 2.0, `BarDataWrangler` takes Arrow bytes, not a
  DataFrame. The child converts the bars from PostgreSQL to Arrow.
- The isolation goal is to prevent accidents, not to stop hostile code. Only
  one user writes strategies.

| Control | Rule |
|---|---|
| Timeout | Default 120 minutes. After the timeout, the parent stops the child. The status is "timed out". |
| Concurrency | Default 1 backtest at a time. Other backtests wait in a queue. |
| Defaults | The user can change the timeout and the concurrency in the UI. PostgreSQL stores them. |
| Memory | Do not use `RLIMIT_AS`. The `web` container has a memory limit. The child sets `oom_score_adj` to 1000, so the kernel stops the backtest first when memory is low. |
| CPU | The child runs with `nice 10`. |
| Environment | Allow list: `PATH`, `HOME`, `TZ`, `DATABASE_URL`. IBKR and Cloudflare secrets are not passed. |
| Network | No network isolation. The child must connect to PostgreSQL. |
| File system | The container root file system is read-only. Only `/tmp` is writable. |

Implementation of the controls:

- The timeout and the concurrency are the backtest limits. The table
  `backtest_limits` holds at most one row. Without a row, the defaults apply
  (`backtest/backtest_limits.py`). `PUT /api/backtest-limits` writes the row
  (section 10.5). The timeout is from 1 second to 7 days. The concurrency is
  from 1 to 16.
- The runner reads the limits at each queue check (10.3 step 2). A change
  applies to the next backtest that starts. A running backtest keeps the
  timeout that it started with.
- The child (`app/backtest_process.py`) writes 1000 to
  `/proc/self/oom_score_adj` and calls `os.nice(10)` before it imports the
  strategy. Any process can make its own priority lower, so this needs no
  privilege.
- The memory limit of the `web` container is `ATRADE_WEB_MEMORY_LIMIT`
  (default `4g`). Tests cannot check the out-of-memory order. Section 17.8
  has the manual check.

## 10.2 Tables

Migration: `backend/migrations/versions/9a4c2f6e1b70_backtest_create_tables.py`.

| Table | Columns |
|---|---|
| `backtest` | `id`, `strategy_version_id` (not null, foreign key to `strategy_version` with no `ON DELETE` action), `symbol`, `exchange`, `currency`, `bar_period`, `start_utc`, `end_utc`, `paper_capital_usd` (above 0), `status`, `error_message`, `created_at_utc`, `started_at_utc`, `ended_at_utc`, and the metrics `final_equity_usd`, `total_return_percent`, `max_drawdown_percent`, `trade_count` (null until the backtest finishes) |
| `backtest_equity_point` | `backtest_id`, `time_utc`, `equity_usd`. Primary key `(backtest_id, time_utc)`. |
| `backtest_trade` | `id`, `backtest_id`, `time_utc`, `side` (`BUY` or `SELL`), `quantity_shares`, `price_usd`, `commission_usd` |
| `backtest_limits` | `single_row` (primary key, always true), `timeout_seconds` (above 0), `concurrency` (above 0). Migration `3e7a1c5d9b71_backtest_create_backtest_limits.py`. |

- `status` is one of `queued`, `running`, `finished`, `failed`, `timed_out`.
- Because of the `strategy_version_id` foreign key, a strategy that a
  backtest uses cannot be deleted (section 9.1).
- Rows of the result tables are deleted with their backtest
  (`ON DELETE CASCADE`). This stage has no route that deletes a backtest.

## 10.3 Run flow

1. `POST /api/backtests` checks the request and adds a `queued` row.
2. The backtest runner of the Web process (`backtest/backtest_runner.py`)
   checks the queue every 0.5 seconds. It reads the backtest limits from
   `backtest_limits`. While fewer backtests run than the
   concurrency, it sets the oldest queued backtest to `running` and starts
   `python -m atrade.app.backtest_process <backtest ID>`. The queue is the
   table, so queued backtests stay queued after a restart.
3. The child reads the request, the strategy version
   (`read_strategy_version()` of `strategy`), and the saved bars
   (`read_saved_bars()` of `market_data`) from PostgreSQL. It never calls
   IBKR.
4. The child converts the bars to Arrow bytes (`decimal128(38, 16)` prices
   and volume, `uint64` times). `ts_event` is the bar end, so a strategy sees
   a bar only after its period. `BarDataWrangler` makes NautilusTrader bars
   from the bytes.
5. The child imports the strategy code from a file in a temporary directory
   under `/tmp`, so that tracebacks show the line numbers. It makes the
   strategy configuration with `instrument_id` and `bar_type`
   (`<symbol>.<exchange>-<bar period>-LAST-EXTERNAL`), and runs the engine:
   one `Equity` instrument, a `CASH` account in USD with the paper capital,
   `NETTING` positions, and a zero commission (`FixedFeeModel`).
6. The child calculates the equity curve and the metrics with the metric
   functions (section 10.4), and writes them, the trades, and the status
   `finished` in one transaction.
7. When the child ends, the parent ends a backtest that is still `running`:
   `timed_out` after the timeout (the parent kills the child), else `failed`
   with the end of the child error output.

Failures that the user sees in `error_message`:

- An exception in the strategy code, for example in `on_bar` or in the
  configuration: the traceback. The engine logs a strategy exception and
  does not raise it. The child runs the engine with `shutdown_on_error` and
  writes `ERROR` log lines to a file. When the file is not empty, the backtest
  fails with its content.
- No saved bars in the range: a message that tells the user to open the bar
  chart of the instrument, which loads the bars from IBKR.
- A Web restart during a run: the runner sets the `running` backtests to
  `failed` at start, because their children ended with the old process.

Limits of this stage:

- A backtest supports only USD instruments. The paper capital is in USD and
  the backtest has no exchange rates. A request in another currency gets
  `422`.
- The commission is zero.
- `request_bars` in `on_start` gets no bars in a backtest. The engine has no
  historical data client and writes a warning. The indicator warms up on the
  first bars of the range.

## 10.4 Metric functions

The public entry `atrade.backtest` exports the metric functions. Forward tests
use the same functions for the comparison (section 12.10).

| Name | Purpose |
|---|---|
| `BacktestTrade` | One fill: `time_utc`, `side`, `quantity_shares`, `price_usd`, `commission_usd`. |
| `EquityPoint` | `time_utc`, `equity_usd`. |
| `calculate_equity_curve(*, paper_capital_usd, bars, bar_period, trades)` | One point at the end of each bar: the cash plus the position at the bar close price. A trade counts in the first point at or after its time. |
| `calculate_metrics(*, paper_capital_usd, equity_curve, trade_count)` | `BacktestMetrics`: `final_equity_usd`, `total_return_percent`, `max_drawdown_percent` (the largest fall from a peak, as a percent of the peak; the paper capital is the first peak), and `trade_count`. Percents have 2 decimal places. |

The public entry also exports `create_backtest_router(*, database_url,
clock)`, `BacktestRunner(*, database_url, clock, process_command)` with
`keep_running()`, and
`run_backtest(*, database_url, backtest_id, clock)` for the child.

## 10.5 HTTP routes

| Route | Behavior |
|---|---|
| `POST /api/backtests` | Body `{"strategy_version_id", "symbol", "exchange", "currency", "bar_period", "start_utc", "end_utc", "paper_capital_usd"}`. `201` with the queued backtest. `422` when `paper_capital_usd` is missing or not above 0, a time has no time zone, the bar period is unknown, the range does not end after it starts, the currency is not USD, or the strategy version does not exist. |
| `GET /api/backtests` | `200` with all backtests, the newest first. |
| `GET /api/backtest-limits` | `200` with `{"timeout_seconds", "concurrency"}`. The defaults are `7200` and `1`. |
| `PUT /api/backtest-limits` | Body `{"timeout_seconds", "concurrency"}`. `200` with the saved limits. `422` when `timeout_seconds` is not from 1 to 604800 or `concurrency` is not from 1 to 16. |
| `GET /api/backtests/{backtest_id}` | `200` with the backtest, `equity_curve` (`[{"time_utc", "equity_usd"}]`), and `trades`. `404` when the backtest does not exist. |

A backtest has `id`, `strategy_version_id`, `strategy_id`, `strategy_name`,
`version_number`, the request fields, `status`, `error_message`,
`created_at_utc`, `started_at_utc`, `ended_at_utc`, and `metrics` (null until
the backtest finishes). Money values and percents are decimal strings.

## 10.6 Frontend

- `frontend/src/lib/backtest/` holds the HTTP client (`startBacktest`,
  `listBacktests`, `readBacktest`), the value formats, and the
  `BacktestResult` component: the status, the strategy error, the metrics,
  the equity curve (`EquityChart`, a `lightweight-charts` line series with
  the TradingView attribution), and the trade table. The strategy error and
  the trade table are in `ScrollRegion`s.
- `/backtests` has the form and the list of backtests. The form combines the
  strategy versions (`#lib/strategy`), the bar periods (`#lib/market_data`),
  and the default paper capital (`readPaperCapital()` of
  `#lib/paper_trading`). Dates are days in UTC.
- `/backtests` also has the "Limits" form (`BacktestLimitsForm`). It shows
  the timeout in minutes (`formatTimeoutMinutes`) and takes only whole
  minutes (`convertTimeoutMinutesToSeconds`). The client functions are
  `readBacktestLimits` and `changeBacktestLimits`.
- `/backtests/<id>` shows the request and the result. It reads the backtest
  each second until the status is final.
- Tests: `backend/tests/backtest/` (HTTP routes, metric functions, and real
  child processes on the bar file `bars/btest_arca_usd_1_day.csv` with the
  test strategy `strategies/buy_and_sell_by_bar_count.py`; the tests assert
  exact results), `frontend/src/lib/backtest/*.test.ts`,
  `e2e/backtest.spec.ts`, and `e2e/backtest_limits.spec.ts`.
- Isolation tests (`backend/tests/backtest/test_backtest_isolation.py`) use
  the test strategy `strategies/write_process_facts.py`. It writes its
  environment, `oom_score_adj`, niceness, and process ID to a log file. The
  tests assert: a strategy that loops forever in `on_bar` with a 2 second
  timeout gets "timed out" and its process ended; the log has no IBKR
  variable; `oom_score_adj` is 1000 and the niceness is 10 more than the
  niceness of the test process; with concurrency 1 the second backtest waits
  in the queue; with concurrency 2 two backtests run at the same time.
