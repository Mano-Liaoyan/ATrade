# Backtest

This document is section 10 of the architecture specification
([`docs/architecture.md`](../architecture.md)). It was moved to its own file
to keep the specification shorter than 1000 lines (section 18). Terms have
the meaning that [`GLOSSARY.md`](../../GLOSSARY.md) gives them.

Sources: [Strategy editing and run isolation](https://github.com/Mano-Liaoyan/ATrade/issues/48),
[Module division](https://github.com/Mano-Liaoyan/ATrade/issues/38),
[Run a backtest and see the result](https://github.com/Mano-Liaoyan/ATrade/issues/70),
[Backtest list and version comparison](https://github.com/Mano-Liaoyan/ATrade/issues/72),
[Backtest isolation controls](https://github.com/Mano-Liaoyan/ATrade/issues/71).

## 10.1 Decisions

- A backtest request contains the strategy version, the instrument, the bar
  type, the time range, and `paper_capital_usd`. `paper_capital_usd` is
  required.
- `paper_trading` exports `fetch_paper_capital_usd()`. It returns the paper
  account balance (`NetLiquidation` converted to USD, section 11.9) after a
  passed paper account check.
  Otherwise it returns the local value from `settings` (section 11.5). The
  frontend uses it to fill in the backtest form.
- Each backtest runs in its own child process (`app/backtest_process.py`),
  because the NautilusTrader backtest engine blocks the event loop.
- In NautilusTrader 2.0, `BarDataWrangler` takes Arrow bytes, not a
  DataFrame. The child converts the bars from PostgreSQL to Arrow.
- A backtest needs saved bars. `POST /api/backtests` refuses (`422`, no
  row) a request when PostgreSQL has no saved bar of the instrument and bar
  period that starts in the time range. The message is the same message as
  the child failure ("PostgreSQL has no saved ... Open the bar chart of the
  instrument to load bars from IBKR."). Partial coverage is allowed: one
  saved bar in the range is enough. The range can start before the first
  saved bar or end after the last one, and the backtest runs on the saved
  bars only. The check uses `has_saved_bars()` of `market_data`, which
  selects the same rows as `read_saved_bars()` (`bar.start_utc` in
  `[start_utc, end_utc)`).
- The backtest form offers only watchlist instruments with saved bars of the
  selected bar period (section 10.6). It has no free-text symbol, exchange,
  or currency fields, so a request cannot name an instrument that has no
  bars by a typing error.
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

1. `POST /api/backtests` checks the request, checks that saved bars exist in
   the range (section 10.1), and adds a `queued` row.
2. The backtest runner of the Web process (`backtest/backtest_runner.py`)
   checks the queue every 0.5 seconds. It reads the backtest limits from
   `backtest_limits`. While fewer backtests run than the
   concurrency, it sets the oldest queued backtest to `running` and starts
   `python -m atrade.app.backtest_process <backtest ID>`. The queue is the
   table, so queued backtests stay queued after a restart.
3. The child reads the request, the strategy version
   (`read_strategy_version()` of `strategy`), and the saved bars
   (`read_saved_bars()` of `market_data`) from PostgreSQL. It never calls
   IBKR. It also reads the look-back bars: the saved bars of the same
   instrument and bar period before the start (section 10.3.1).
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
  chart of the instrument, which loads the bars from IBKR. The start route
  refuses such a request first. The child checks again, because it reads the
  bars after the request is queued.
- A Web restart during a run: the runner sets the `running` backtests to
  `failed` at start, because their children ended with the old process.

Limits of this stage:

- A backtest supports only USD instruments. The paper capital is in USD and
  the backtest has no exchange rates. A request in another currency gets
  `422`.
- The commission is zero.
- `request_bars` gets only the look-back bars of the backtest bar type
  (section 10.3.1).

### 10.3.1 Look-back bars

Decision of the owner (review finding 2 of #61, option a): in a backtest,
`request_bars` returns look-back bars from before the backtest start. A
temporary NautilusTrader `ParquetDataCatalog` holds them. The child fills it
from the saved bars in PostgreSQL. So a strategy warms up its indicators as
in a forward test, and it can trade on the first bar of the range.

- Look-back length: `find_look_back_length(bar_period)` in
  `backtest/backtest_run.py`. It is the warm-up of the strategy template:
  3 average periods of the default 20 bars, and 7 days at least
  (`max(bar period × 60, 7 days)`). For daily bars this is 60 days. The child
  reads the saved bars from `start_utc` minus this length to `start_utc`
  (not included). A strategy chooses its own request start. A request that
  starts earlier gets only these bars. When PostgreSQL has no saved bars
  before the start, `request_bars` gets no bars and the indicator warms up on
  the first bars of the range.
- Mechanism (`create_look_back_catalog()` in
  `backtest/strategy_engine_run.py`): the child writes the look-back bars to
  a catalog in its temporary work directory (`look_back_catalog/`) and gives
  the catalog to `BacktestEngineConfig(catalogs=...)`. The data engine
  answers `request_bars` from the catalog.
- The catalog says that it holds the bar type from the first to the last
  UNIX nanosecond. If not, the data engine sends the part of the request
  that the catalog does not hold to the venue data client. The backtest data
  client cannot answer (`Handler not implemented ... RequestBars`), and the
  request never gets a response. A request for another bar type (for
  example 1-hour bars in a 1-day backtest) still gets no bars.
- Only the bars of the range go to `engine.add_data()`. The look-back bars
  never fill an order and never make an equity point. The equity curve and
  the trades start at the first bar of the range.
- The catalog has no bars of the range. A request during the run gets only
  look-back bars, so a strategy cannot read bars from after the engine time.
- Tests: `tests/backtest/test_strategy_template_backtest.py` (the template
  buys on the first bar of the range with look-back bars, and does not
  without them; it trades on 120 daily bars without look-back bars) and
  `test_the_template_warms_up_on_saved_bars_before_the_start` in
  `tests/backtest/test_backtest_runs.py` (a real child process reads the
  look-back bars from PostgreSQL).

## 10.4 Metric functions

The public entry `atrade.backtest` exports the metric functions. Forward tests
use the same functions for the comparison (section 12.10).

| Name | Purpose |
|---|---|
| `BacktestTrade` | One fill: `time_utc`, `side`, `quantity_shares`, `price_usd`, `commission_usd`. |
| `EquityPoint` | `time_utc`, `equity_usd`. |
| `calculate_equity_curve(*, paper_capital_usd, bars, bar_period, trades)` | One point at the end of each bar: the cash plus the position at the bar close price. A trade counts in the first point at or after its time. |
| `calculate_metrics(*, paper_capital_usd, equity_curve, trade_count)` | `BacktestMetrics`: `final_equity_usd`, `total_return_percent`, `max_drawdown_percent` (the largest fall from a peak, as a percent of the peak; the paper capital is the first peak), and `trade_count`. Percents have 2 decimal places. |

For other capabilities (#78), the public entry exports
`BacktestRequest`, `BacktestStatus`, `check_backtest_request(request)` (the
reason why the request cannot run, or `None`: not USD, an empty time range;
`POST /api/backtests` uses it too), `queue_backtest(*, database_url,
request, created_at_utc)` (returns the ID of a queued backtest), and
`read_backtest_outcome(*, database_url, backtest_id)` (`BacktestOutcome`:
the request, status, error message, metrics, equity curve, and trades, or
`None`). They are in `backtest_access.py`.

The public entry also exports `create_backtest_router(*, database_url,
clock)`, `BacktestRunner(*, database_url, clock, process_command)` with
`keep_running()`, and
`run_backtest(*, database_url, backtest_id, clock)` for the child.

## 10.5 HTTP routes

| Route | Behavior |
|---|---|
| `POST /api/backtests` | Body `{"strategy_version_id", "symbol", "exchange", "currency", "bar_period", "start_utc", "end_utc", "paper_capital_usd"}`. `201` with the queued backtest. `422` when `paper_capital_usd` is missing or not above 0, a time has no time zone, the bar period is unknown, the range does not end after it starts, the currency is not USD, the strategy version does not exist, or PostgreSQL has no saved bar of the instrument and bar period in the range (section 10.1). |
| `GET /api/backtests` | `200` with all backtests, the newest first. |
| `GET /api/backtest-limits` | `200` with `{"timeout_seconds", "concurrency"}`. The defaults are `7200` and `1`. |
| `PUT /api/backtest-limits` | Body `{"timeout_seconds", "concurrency"}`. `200` with the saved limits. `422` when `timeout_seconds` is not from 1 to 604800 or `concurrency` is not from 1 to 16. |
| `GET /api/backtests/{backtest_id}` | `200` with the backtest, `equity_curve` (`[{"time_utc", "equity_usd"}]`), and `trades`. `404` when the backtest does not exist. |
| `GET /api/backtests/{backtest_id}/comparison/{other_backtest_id}` | `200` with `{"strategy_id", "strategy_name", "first", "second"}`. `first` and `second` are the two backtests as `GET /api/backtests/{backtest_id}` gives them, each with the `code` of its strategy version. `422` when the two backtests use different strategies, or when the two IDs are the same. `404` when a backtest does not exist. Section 10.7. |

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
  the watchlist instruments with saved bars (`#lib/watchlist`), and the
  default paper capital (`readPaperCapital()` of `#lib/paper_trading`).
  Dates are days in UTC.
- The "Instrument" select offers the watchlist instruments that have saved
  bars of the selected bar period (`selectInstrumentsWithSavedBars()`), as
  `<symbol> / <exchange> / <currency>`. The `saved_bars` field of
  `GET /api/watchlist` gives the bar periods with saved bars
  (`docs/architecture/market_data.md` section 8.3). The status "Saved bars"
  shows the first and the last saved bar of the selected instrument
  (`describeSavedBars()`). When no watchlist instrument has saved bars of the
  bar period, the select is disabled and the status links to the watchlist
  on the home page: the bar chart of a watchlist instrument saves its bars.
- `/backtests` also has the "Limits" form (`BacktestLimitsForm`). It shows
  the timeout in minutes (`formatTimeoutMinutes`) and takes only whole
  minutes (`convertTimeoutMinutesToSeconds`). The client functions are
  `readBacktestLimits` and `changeBacktestLimits`.
- `/backtests/<id>` shows the request and the result. It reads the backtest
  each second until the status is final.
- `/backtests/<id>/comparison/<other id>` is the comparison page (section
  10.7).
- Tests: `backend/tests/backtest/` (HTTP routes, metric functions, and real
  child processes on the bar file `bars/btest_arca_usd_1_day.csv` with the
  test strategy `strategies/buy_and_sell_by_bar_count.py`; the tests assert
  exact results), `frontend/src/lib/backtest/*.test.ts`,
  `e2e/backtest.spec.ts`, `e2e/backtest_comparison.spec.ts`, and
  `e2e/backtest_limits.spec.ts`.
- Isolation tests (`backend/tests/backtest/test_backtest_isolation.py`) use
  the test strategy `strategies/write_process_facts.py`. It writes its
  environment, `oom_score_adj`, niceness, and process ID to a log file. The
  tests assert: a strategy that loops forever in `on_bar` with a 2 second
  timeout gets "timed out" and its process ended; the log has no IBKR
  variable; `oom_score_adj` is 1000 and the niceness is 10 more than the
  niceness of the test process; with concurrency 1 the second backtest waits
  in the queue; with concurrency 2 two backtests run at the same time.

## 10.7 Backtest list and comparison

Source: [#72](https://github.com/Mano-Liaoyan/ATrade/issues/72). Rules:
section 9.5.

- The backtest list on `/backtests` shows the metrics of each backtest side by
  side: the final equity, the total return, the maximum drawdown, and the
  trade count. It is in a `ScrollRegion` with the height
  `min(24rem, 50vh)`.
- Each row has a check box. `checkComparisonSelection()` of `#lib/backtest`
  accepts exactly 2 backtests of the same strategy. For other selections, the
  "Compare selected backtests" button is disabled and the status line gives
  the reason. The backend route applies the same rule (section 10.5), so a
  typed URL with different strategies shows the refusal.
- Two backtests of the same strategy version are also accepted. They can
  differ in the instrument, the period, or the paper capital. Their code diff
  is empty.
- The page `/backtests/<id>/comparison/<other id>` reads
  `compareBacktests()` and shows `ComparisonView`. The backtest with the
  lower ID is first.
- `ComparisonView` (`frontend/src/lib/backtest/ComparisonView.svelte`) is the
  comparison view for backtests and forward tests (section 12.10). Its
  properties:

  | Property | Type | Meaning |
  |---|---|---|
  | `first`, `second` | `ComparedRun`: `{label, metrics, equityCurve}` | `metrics` is `BacktestMetrics` or `null` (shown as "No result"). `equityCurve` is a list of `EquityPoint`. |
  | `code` | `ComparedCode`: `{firstCode, secondCode}`, optional | Shows the code diff. Leave it out when both runs use the same strategy version. |

  It shows the code diff (`CodeDiff` of `#lib/foundation/code_editor`,
  read-only `@codemirror/merge` with wrapped lines, unchanged lines collapsed
  to the changed parts and 3 lines around them, in a `ScrollRegion` named
  "Code difference"), the metric table (in a `ScrollRegion` named "Compared
  metrics"), and both equity curves on one chart.
- When `firstCode` and `secondCode` are the same (two backtests of the same
  strategy version), the view shows the status "Same strategy version: no code
  difference." in place of the diff. A closed "Show the code" disclosure shows
  the full code without collapsed lines.
- `EquityChart` takes `curves: [{name, points}]`. The first curve is a solid
  line in `--color-text`, the second a dashed line in `--color-accent`. With
  more than one curve, a legend names each curve.
