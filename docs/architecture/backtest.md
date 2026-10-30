# Backtest

This document is section 10 of the architecture specification
([`docs/architecture.md`](../architecture.md)). It was moved to its own file
to keep the specification shorter than 1000 lines (section 18). Terms have
the meaning that [`GLOSSARY.md`](../../GLOSSARY.md) gives them.

Sources: [Strategy editing and run isolation](https://github.com/Mano-Liaoyan/ATrade/issues/48),
[Module division](https://github.com/Mano-Liaoyan/ATrade/issues/38),
[Run a backtest and see the result](https://github.com/Mano-Liaoyan/ATrade/issues/70),
[Backtest list and version comparison](https://github.com/Mano-Liaoyan/ATrade/issues/72),
[Backtest isolation controls](https://github.com/Mano-Liaoyan/ATrade/issues/71),
[Backtests of instruments that are not in USD](https://github.com/Mano-Liaoyan/ATrade/issues/80),
[NautilusTrader 2.0 indicators, multi-instrument backtests, and batch backtests](https://github.com/Mano-Liaoyan/ATrade/issues/131),
[Strategy robustness check methods](https://github.com/Mano-Liaoyan/ATrade/issues/132),
[Scope of metrics and robustness checks](https://github.com/Mano-Liaoyan/ATrade/issues/137),
[Content of the strategy template library](https://github.com/Mano-Liaoyan/ATrade/issues/139),
[Design of the AI strategy assistant](https://github.com/Mano-Liaoyan/ATrade/issues/140),
[Decision on the screen data sources](https://github.com/Mano-Liaoyan/ATrade/issues/141),
[Design of the multi-instrument backtest and the parameter sweep](https://github.com/Mano-Liaoyan/ATrade/issues/142),
[Screen page prototype](https://github.com/Mano-Liaoyan/ATrade/issues/145),
[Forward tests of multi-instrument strategies](https://github.com/Mano-Liaoyan/ATrade/issues/146),
[How the AI assistant uses screens](https://github.com/Mano-Liaoyan/ATrade/issues/150).

### Implementation phases of this section

The planning map
[Wayfinder: indicators, screens, and strategy help](https://github.com/Mano-Liaoyan/ATrade/issues/129)
puts the new parts of this section in phases.

| Phase | Parts |
|---|---|
| Existing | Sections 10.1 to 10.8, without the parts marked with a phase. |
| Phase 1 | The new metrics, the win rate in the backend, the in-sample and out-of-sample split, the probabilistic and deflated Sharpe ratio, and their display (section 10.9). They use only the existing single-instrument backtest. |
| Phase 2 | The `run_backtest` tool of the AI assistant for single-instrument backtests, and the conversation ID of a backtest (section 10.13). |
| Phase 3 | The bar sources of a backtest and the survivorship bias warning (section 10.12), the multi-instrument backtest with a universe (section 10.10), the parameter sweep with the walk-forward check, the parameter sensitivity check, and the probability of backtest overfitting (section 10.11), the universe parameters of `run_backtest` (section 10.13), and the memory limit default `8g` (section 10.1). |

## 10.1 Decisions

- A backtest request contains the strategy version, the instrument, the bar
  type, the time range, and `paper_capital_usd`. `paper_capital_usd` is
  required.
- Phase 1: the request also contains `out_of_sample_share` (section 10.9.4).
- Phase 3: the request names a universe in place of the instrument
  (section 10.10), and it can contain a source order (section 10.12).
- Backtests do not include cash dividends. The bars are adjusted for stock
  splits only: IBKR `TRADES` bars are adjusted for stock splits and not for
  dividends, and ATrade adjusts the Databento bars in the same way
  ([#141](https://github.com/Mano-Liaoyan/ATrade/issues/141),
  [#149](https://github.com/Mano-Liaoyan/ATrade/issues/149),
  [ADR 0008](../adr/0008-stock-splits-from-ibkr-evidence.md)). Thus the total
  return of an instrument that pays dividends is lower than its real total
  return. This version does not handle cash dividends.
- The paper capital, the equity curve, the trades, and the metrics are in
  USD for all instruments. A backtest of an instrument that is not in USD
  converts with daily exchange rates (section 10.8).
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
  the child failure (`describe_missing_bars()`). It names the bar period
  ("1 min"), the instrument, and the period in UTC ("2026-03-01 00:00 UTC").
  It says that ATrade saves bars when a bar chart loads them from IBKR and
  when a forward test receives them,
  and that IBKR has bars only for the regular trading hours, so a period when
  the market was closed has no bars. It tells the user to open the bar chart
  with this bar period or to select a period with trading hours. Partial coverage is allowed: one
  saved bar in the range is enough. The range can start before the first
  saved bar or end after the last one, and the backtest runs on the saved
  bars only. The check uses `has_saved_bars()` of `market_data`, which
  selects the same rows as `read_saved_bars()` (bar start in
  `[start_utc, end_utc)`, through the global source order of
  `docs/architecture/market_data.md` section 8.7.2).
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
- The memory limit of the `web` container is `ATRADE_WEB_MEMORY_LIMIT`.
  Done in #199: the default changed from `4g` to `8g`
  ([#142](https://github.com/Mano-Liaoyan/ATrade/issues/142)): a
  multi-instrument backtest of 500 instruments on 1-hour bars can need 4 to
  5 GB (estimate, section 10.10.3). The server has 16 GB. With concurrency 2,
  two such backtests can reach the 8 GB limit. Tests cannot check the
  out-of-memory order. Section 17.8 has the manual check.

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

### 10.2.1 New columns and tables

Each phase adds its columns in a new migration. Existing rows do not change.
New columns are null on existing rows, except where a default is given.

| Phase | Table | Change |
|---|---|---|
| 1 | `backtest` | Add the metric columns of section 10.9.2: `cagr_percent`, `annual_volatility_percent`, `sharpe_ratio`, `sortino_ratio`, `calmar_ratio`, `profit_factor`, `average_win_usd`, `average_win_percent`, `average_loss_usd`, `exposure_percent`, `turnover_per_year`, and `win_rate_percent`. Each is null until the backtest finishes, and null when the metric shows "–" (section 10.9.3). Migration `8d4b6f2a1c93_backtest_add_metric_columns.py`. |
| 1 | `backtest` | Add `out_of_sample_share` (integer percent, 0 to 50, not null; existing rows get 0) and `split_time_utc` (null when `out_of_sample_share` is 0). The start route sets `split_time_utc`. Nothing changes it later. Migration `2f6a9c1e4d85_backtest_add_out_of_sample_split.py`. |
| 2 | `backtest` | Add `conversation_id` (foreign key to `assistant_conversation`, `ON DELETE SET NULL`). It is set when the AI assistant starts the backtest ([#140](https://github.com/Mano-Liaoyan/ATrade/issues/140)). Done (#180): migration `4a6c8e1b3d57_backtest_add_conversation_id.py`. |
| 3 | `backtest` | `symbol`, `exchange`, and `currency` can be null. Add `universe_kind` (`single`, `rule`, `list`, or `screen`; not null, default `single`), the universe parameters of section 10.10.2 (done in #199: `universe_top_n`, migration `d7b9c5d5e28d_backtest_add_universe.py`; a multi-instrument backtest has null `symbol` and `exchange`, and `currency` holds the currency of all members), `sweep_id` (foreign key to `parameter_sweep`, null for a backtest that is not in a sweep), and `parameters` (JSON, the parameter values of a sweep run, else null). |
| 3 | `backtest` | Add `source_order` (JSON list of bar sources) and `bar_count_by_source` (JSON object), section 10.12. Done in #197: migration `2f6b8d1c4e97_backtest_add_bar_source_columns.py`, 2 `jsonb` columns. |
| 3 | `backtest_universe_member` | New. `backtest_id`, `period_start_utc`, `symbol`, `exchange`. One row for each member of the universe in each universe period (section 10.10.2). `ON DELETE CASCADE` with its backtest. Done in #199. |
| 3 | `backtest_trade` | Add `symbol` and `exchange`. The exchange is the real exchange, not the simulated venue `SMART` ([ADR 0003](../adr/0003-one-simulated-venue-per-currency.md)). Done in #199: a single-instrument backtest writes its instrument too. Trades from before the migration have null. |
| 3 | `parameter_sweep` | New. `id`, `strategy_version_id` (foreign key to `strategy_version` with no `ON DELETE` action), the universe columns of `backtest`, `bar_period`, `start_utc`, `end_utc`, `paper_capital_usd`, `out_of_sample_share`, `parameter_grid` (JSON, section 10.11.1), `created_at_utc`. |

- Phase 3 adds the status `cancelled` for the queued runs of a cancelled
  parameter sweep (section 10.11.2).
- The decisions name the `backtest` columns `universe_kind`, `sweep_id`, and
  `parameters`, and the tables `backtest_universe_member` and
  `parameter_sweep`. The other new names are choices of this document. The
  implementation can change them.

## 10.3 Run flow

1. `POST /api/backtests` checks the request, checks that saved bars exist in
   the range (section 10.1), saves the missing daily exchange rates of an
   instrument that is not in USD (section 10.8), and adds a `queued` row.
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
   instrument and bar period before the start (section 10.3.1), and for an
   instrument that is not in USD the saved exchange rates (section 10.8).
4. The child converts the bars to Arrow bytes (`decimal128(38, 16)` prices
   and volume, `uint64` times). `ts_event` is the bar end, so a strategy sees
   a bar only after its period. `BarDataWrangler` makes NautilusTrader bars
   from the bytes.
5. The child imports the strategy code from a file in a temporary directory
   under `/tmp`, so that tracebacks show the line numbers. It makes the
   strategy configuration with `instrument_id` and `bar_type`
   (`<symbol>.<exchange>-<bar period>-LAST-EXTERNAL`), and runs the engine:
   one `Equity` instrument, a `CASH` account in the instrument currency with
   the paper capital in that currency (section 10.8), `NETTING` positions,
   and a zero commission (`FixedFeeModel`).
6. The child calculates the equity curve and the metrics with the metric
   functions (section 10.4), and writes them, the trades, and the status
   `finished` in one transaction. Phase 1: the metrics include the metrics of
   section 10.9.2.
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
- No saved exchange rate before the start of an instrument that is not in
  USD (section 10.8). The start route refuses such a request first.
- A Web restart during a run: the runner sets the `running` backtests to
  `failed` at start, because their children ended with the old process.

Limits of this stage:

- The commission is zero.
- `request_bars` gets only the look-back bars of the backtest bar type
  (section 10.3.1).
- Cash dividends are not in the backtest (section 10.1).

Phase 3 changes steps 1, 3, and 5 for a backtest with a universe (section
10.10.4) and for the source order (section 10.12).

### 10.3.1 Look-back bars

Decision of the owner (review finding 2 of #61, option a): in a backtest,
`request_bars` returns look-back bars from before the backtest start. A
temporary NautilusTrader `ParquetDataCatalog` holds them. The child fills it
from the saved bars in PostgreSQL. So a strategy warms up its indicators as
in a forward test, and it can trade on the first bar of the range.

- Look-back: `find_look_back(bar_period, warm_up_bar_count)` in
  `backtest/backtest_run.py`. It gives a read length and an optional bar
  count (`LookBack`).
- Decided (#164): a rule builder version (a version with `rules`) gets the
  last N saved bars before the start. N is the largest look-back count of
  the indicators in its rules ([`indicator.md`](indicator.md) section 23.4,
  `find_warm_up_bar_count()` in `strategy/rules_code.py`).
  `read_strategy_version()` gives N as `warm_up_bar_count`. The child reads
  the saved bars of the range `start_utc` minus `N × bar period × factor`
  (factor 2 for 1-day bars, 6 for intraday bars, because a bar comes only
  in the trading hours), and at least the default length below, to
  `start_utc`. It keeps only the last N bars. So SMA(200) has a value on the
  first bar of the range when PostgreSQL has 200 daily bars before the
  start. The generated code asks `request_bars` for
  `max(bar period × N × 6, 7 days)` before the start, so the request holds
  all N bars. With the earlier 60 days, SMA(200) had no value in the first
  months of the range (a test with 20 bars in the range made no trade).
- A version without rules, or with rules without an indicator ("Blank code"
  and code written by hand), keeps the default length and all bars of it.
  The default length is the warm-up of the "Blank code" start
  point (`backend/src/atrade/strategy/strategy_template.py`,
  [`strategy.md`](strategy.md) section 9.2): 3 average periods of the
  default 20 bars of its SMA(20), and 7 days at least
  (`max(bar period × 60, 7 days)`). For daily bars this is 60 days. The
  "Blank code" start point is not a strategy template: it only shows the
  strategy file format and is not in the template library
  ([#139](https://github.com/Mano-Liaoyan/ATrade/issues/139)). Phase 3: a
  multi-instrument backtest on 1-day bars has a look-back length of 1 year,
  the same as a multi-instrument forward test
  ([#146](https://github.com/Mano-Liaoyan/ATrade/issues/146)). Decided (#199):
  a multi-instrument backtest on 1-hour bars uses the single-instrument length
  (`find_universe_look_back_length()` in `backtest/backtest_universe.py`).
  When the look-back of the strategy version (#164) is longer, it applies. The child
  reads the saved bars from `start_utc` minus this length to `start_utc`
  (not included). A strategy chooses its own request start. A request that
  starts earlier gets only these bars. When PostgreSQL has no saved bars
  before the start, `request_bars` gets no bars and the indicator warms up on
  the first bars of the range.
- A forward test uses the same look-back and the same catalog for its
  warm-up bars (`find_look_back()` and `write_look_back_catalog()` of the
  public entry, [`forward_test.md`](forward_test.md) section 12.15).
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
- Tests: `tests/backtest/test_strategy_template_backtest.py` (the "Blank
  code" start point buys on the first bar of the range with look-back bars,
  and does not without them; it trades on 120 daily bars without look-back
  bars) and
  `test_the_template_warms_up_on_saved_bars_before_the_start` in
  `tests/backtest/test_backtest_runs.py` (a real child process reads the
  look-back bars from PostgreSQL). `tests/backtest/test_rules_backtest.py`:
  a rule builder version with SMA(200) buys on the first bar of the range
  with 300 saved bars before the start, and SMA(3) without saved bars before
  the start warms up on the first bars of the range.

## 10.4 Metric functions

The public entry `atrade.backtest` exports the metric functions. Forward tests
use the same functions for the comparison (section 12.10).

| Name | Purpose |
|---|---|
| `BacktestTrade` | One fill: `time_utc`, `side`, `quantity_shares`, `price_usd`, `commission_usd`. Phase 3 (#199): `symbol` and `exchange` (the real exchange), null for a forward test fill. |
| `EquityPoint` | `time_utc`, `equity_usd`. |
| `calculate_equity_curve(*, start_cash, bars, bar_period, trades)` | One point at the end of each bar: the cash plus the position at the bar close price. A trade counts in the first point at or after its time. `start_cash`, the trades, and the bars are in one currency, and the points are in that currency. |
| `calculate_metrics(*, paper_capital_usd, equity_curve, trade_count)` | `BacktestMetrics`: `final_equity_usd`, `total_return_percent`, `max_drawdown_percent` (the largest fall from a peak, as a percent of the peak; the paper capital is the first peak), and `trade_count`. Percents have 2 decimal places. |
| Phase 1: `calculate_daily_returns(*, start_capital_usd, equity_curve)` | The daily returns of section 10.9.1, as fractions (0.02 is 2 %). |
| Phase 1: `find_round_trips(trades)` | `RoundTrip` list: `start_utc`, `end_utc`, `profit_usd` (after commissions), and `entry_amount_usd` (the amount of the fills on the side of the first fill). A round trip goes from a position of 0 back to a position of 0. A position that is still open is not a round trip. The win rate, the profit factor, the average win, and the average loss use it. |
| Phase 1: `calculate_metrics(*, paper_capital_usd, time_range, equity_curve, trades)` | Also gives the metrics of section 10.9.2 and the win rate, and `missing_reasons` (section 10.9.3). It takes the trades in place of `trade_count` (`trade_count` is the number of trades), and the time range for `years`. It takes no bars: the equity curve has one point at the end of each bar, so the exposure counts the points. Thus a forward test, which has no saved bars, uses the same function. Ratios, percents, and money have 2 decimal places. |
| Phase 3 (#199): `calculate_universe_equity_curve(*, start_cash, bars_by_instrument, bar_period, trades)` | One point at each bar end of any instrument: the cash plus each position at the last close price of its instrument. A trade counts in the first point at or after its time. |
| Phase 1: `calculate_split_metrics(*, paper_capital_usd, time_range, equity_curve, trades, split_time_utc)` | `SplitMetrics`: `in_sample` and `out_of_sample`, each a `BacktestMetrics` (section 10.9.4). |
| Phase 1: `calculate_probabilistic_sharpe(*, daily_returns)` and `calculate_deflated_sharpe(*, daily_returns, trial_sharpe_ratios)` | Section 10.9.5. |
| Phase 1: `find_sharpe_probability_status(percent)` | The status of a PSR or DSR percent: `likely_real`, `uncertain`, `likely_luck`, or None without a value (section 10.9.5). |

Phase 1: forward tests use the new metric functions too. A forward test has
no in-sample and out-of-sample split, because a forward test is out of
sample ([#137](https://github.com/Mano-Liaoyan/ATrade/issues/137)). The
function names of this phase are choices of this document.

For other capabilities (#78), the public entry exports
`BacktestRequest`, `BacktestStatus`, `check_backtest_request(request)` (the
reason why the request cannot run, or `None`: an empty time range;
`POST /api/backtests` uses it too), `queue_backtest(*, database_url,
request, created_at_utc)` (returns the ID of a queued backtest), and
`read_backtest_outcome(*, database_url, backtest_id)` (`BacktestOutcome`:
the request, status, error message, metrics, equity curve, and trades, or
`None`). They are in `backtest_access.py`.

The public entry also exports `create_backtest_router(*, database_url,
clock, exchange_rate_reader)`, `BacktestRunner(*, database_url, clock, process_command)` with
`keep_running()`, and
`run_backtest(*, database_url, backtest_id, clock)` for the child.

## 10.5 HTTP routes

| Route | Behavior |
|---|---|
| `POST /api/backtests` | Body `{"strategy_version_id", "symbol", "exchange", "currency", "bar_period", "start_utc", "end_utc", "paper_capital_usd"}`. `201` with the queued backtest. `422` when `paper_capital_usd` is missing or not above 0, a time has no time zone, the bar period is unknown, the range does not end after it starts, the strategy version does not exist, PostgreSQL has no saved bar of the instrument and bar period in the range (section 10.1), or the daily exchange rates of an instrument that is not in USD cannot be saved (section 10.8). |
| `GET /api/backtests` | `200` with all backtests, the newest first. |
| `GET /api/backtest-limits` | `200` with `{"timeout_seconds", "concurrency"}`. The defaults are `7200` and `1`. |
| `PUT /api/backtest-limits` | Body `{"timeout_seconds", "concurrency"}`. `200` with the saved limits. `422` when `timeout_seconds` is not from 1 to 604800 or `concurrency` is not from 1 to 16. |
| `GET /api/backtests/{backtest_id}` | `200` with the backtest, `equity_curve` (`[{"time_utc", "equity_usd"}]`), and `trades`. `404` when the backtest does not exist. |
| `GET /api/backtests/{backtest_id}/comparison/{other_backtest_id}` | `200` with `{"strategy_id", "strategy_name", "first", "second"}`. `first` and `second` are the two backtests as `GET /api/backtests/{backtest_id}` gives them, each with the `code` of its strategy version. `422` when the two backtests use different strategies, or when the two IDs are the same. `404` when a backtest does not exist. Section 10.7. |

A backtest has `id`, `strategy_version_id`, `strategy_id`, `strategy_name`,
`version_number`, the request fields, `status`, `error_message`,
`created_at_utc`, `started_at_utc`, `ended_at_utc`, and `metrics` (null until
the backtest finishes). Money values and percents are decimal strings.

Changes of later phases:

| Phase | Route | Change |
|---|---|---|
| 1 | `POST /api/backtests` | The body can contain `out_of_sample_share` (integer percent). Without it, the route uses 30. `422` when it is not from 0 to 50. The route calculates `split_time_utc` (section 10.9.4). The same-period backtest of a forward test uses 0. |
| 1 | `GET /api/backtests`, `POST /api/backtests` | Each backtest has `out_of_sample_share` and `split_time_utc`. |
| 1 | `GET /api/backtests/{backtest_id}` | The backtest also has `out_of_sample_share`, `split_time_utc`, `metrics` with the metrics of section 10.9.2 (`cagr_percent`, `annual_volatility_percent`, `sharpe_ratio`, `sortino_ratio`, `calmar_ratio`, `profit_factor`, `average_win_usd`, `average_win_percent`, `average_loss_usd`, `exposure_percent`, `turnover_per_year`), `win_rate_percent`, and `missing_reasons` (section 10.9.3), `split_metrics` (`{"in_sample", "out_of_sample"}`, each a `metrics` object, or null without a split), and `robustness` (section 10.9.5): `{"trial_count", "sharpe_probability_percent", "sharpe_probability_kind"` (`probabilistic` when the trial count is 1, else `deflated`), `"sharpe_probability_status"` (`likely_real`, `uncertain`, `likely_luck`, or null), `"out_of_sample_to_in_sample_sharpe_percent", "out_of_sample_use_count"}`. The route calculates `robustness` at each read, so a later backtest changes it. #166 adds `split_metrics` and the two out-of-sample fields of `robustness`. `split_metrics` is also null until the backtest finishes. Without a split, both out-of-sample fields are null. Decided (#167): `robustness.missing_reasons` gives the reason of a null `sharpe_probability_percent` by the field name, as `metrics.missing_reasons` does (section 10.9.3). Only `GET /api/backtests/{backtest_id}` and the comparison route have `robustness`. `GET /api/backtests` does not. |
| 1 | `GET /api/backtests/{backtest_id}/comparison/{other_backtest_id}` | `first` and `second` have the Phase 1 fields too. |
| 2 | `POST /api/backtests` | The AI assistant port allows this route (section 10.13). A backtest has `conversation_id`. Done (#180): each backtest of `GET /api/backtests` and `GET /api/backtests/{backtest_id}` has `conversation_id` (null for a backtest of the user). The route of port 8000 never sets it. The public entry exports `start_backtest(*, database_url, exchange_rate_reader, request, created_at_utc, universe_periods, conversation_id)`: it makes the checks of `POST /api/backtests` and returns the ID of the queued backtest or a `BacktestRefusal` (`detail`). Port 8001 calls it with the conversation ID (#181). |
| 3 | `POST /api/backtests` | The body names a universe (section 10.10.6, done in #199 for `single`, `rule`, and `list`) and can contain `source_order` (section 10.12, done in #197): a list of `BarSource` values, only for this backtest. Without it, the route saves the global source order. `422` when the list is empty, has a value 2 times, has a value that is not a `BarSource`, or leaves out a bar source; then no row is added. The saved-bar check of the start route reads through this source order. |
| 3 | `GET /api/backtests` | Without the query `sweep_id`, the list has no sweep runs. With `sweep_id`, it has only the runs of that sweep. |
| 3 | `GET /api/backtests/{backtest_id}` | The backtest also has `universe_kind`, the universe parameters, `sweep_id`, `parameters`, `source_order`, `bar_count_by_source`, `survivorship_bias` (boolean, section 10.12), and `instruments` (section 10.10.7). Each trade has `symbol` and `exchange`. Done in #197: `source_order`, `bar_count_by_source` (`{"ibkr": 9, "databento": 11}`, null until the backtest finishes), and `survivorship_bias`. Done in #199: `universe_kind` and `universe_top_n` (also in `GET /api/backtests`), and `symbol` and `exchange` of each trade. `symbol` and `exchange` of a multi-instrument backtest are null. Both lists are null on a backtest from before the migration. `GET /api/backtests` has the same 3 fields. |
| 3 | `/api/sweeps` | New routes, section 10.11.3. |

The JSON names of the Phase 1 and Phase 3 fields are choices of this
document. The implementation can change them.

## 10.6 Frontend

- `frontend/src/lib/backtest/` holds the HTTP client (`startBacktest`,
  `listBacktests`, `readBacktest`), the value formats, and the parts that the
  backtest page, the strategy page, and the forward test page share (spec
  [#99](https://github.com/Mano-Liaoyan/ATrade/issues/99)):
  - `KeyMetricRow` (`metrics`, `startCapitalUsd`): the key metrics of
    `readKeyMetrics()` in this order: Total return, Net profit (USD), Max
    drawdown, Sharpe ratio, Win rate, Trades, Final equity (USD). Each is a
    `MetricTile` of
    `foundation/metric_tile`. The API gives the max drawdown as a positive
    percent; the row shows it as a negative percent (for example
    "-37.71 %"), with the sign rule of `formatSignedNumber`. Total return, net
    profit, and max drawdown show their direction with `ChangeText`. The
    Sharpe ratio and the win rate come from the API (section 10.9.2,
    [#137](https://github.com/Mano-Liaoyan/ATrade/issues/137), #168). A null
    value shows "–". The frontend does not calculate the win rate.
  - Phase 1: under the row, the robustness row of section 10.9.6 shows.
  - `EquityDrawdownChart` (`curves`, `label`, `interruptions`, `fill`): the
    equity curves and, under them, the drawdown curves
    (`computeDrawdownCurve()`, a negative percent from the highest equity so
    far, which starts at the start capital) on one `lightweight-charts` chart
    with 2 panes. The panes share one time scale, so the curves zoom and
    scroll together. The drawdown axis is a percent. Only other curves fit the
    time scale again, so new live points keep the zoom of the user.
  - `formatMaxDrawdown()`: the one max drawdown format of all pages (the
    comparison view and the forward test pages too).
- `/backtests/<id>` is the backtest workbench (`routes/backtests/[[backtestId]]`),
  one page for the list and the open backtest. `/backtests` opens the newest
  backtest. The page is a `Workbench` (docs/architecture.md section 13):
  - The "Backtests" `SideColumn` has the "New backtest" and "Backtest limits"
    icon buttons and the backtest list (section 10.7).
  - The `PanelSplit` has the backtest panel and the "Backtest tables" panel.
    The backtest panel header line has the number, the strategy version (a
    link to that version on the strategy page), the instrument symbol (a link to the
    instrument page), the bar period, the status, and the "Start forward
    test" icon button. The button starts a forward test of the same strategy
    version, instrument, and bar period and opens it. For a bar period that
    is not live (`isLiveBarPeriod`), the button is disabled and its name says
    why. The body has the `KeyMetricRow` and the `EquityDrawdownChart`, which
    fills the rest of the panel. A queued or running backtest shows its
    status in the body instead.
  - The "Backtest tables" panel has the tabs Trades (32px rows), Orders, and
    Logs. The API has no orders, so Orders shows "No orders". Logs shows the
    strategy error of a failed backtest, or "No logs". Phase 1 adds the tab
    Metrics (section 10.9.6, `BacktestMetricTable`, #168). Phase 3 adds the
    tab Instruments and the Symbol column of Trades (section 10.10.7), and
    the tab Bar sources (section 10.12).
  - The page reads the open backtest each second until its status is final,
    and the list every 2 seconds while a backtest in it is queued or running.
- The "New backtest" dialog (`StartBacktestDialog`) has the start form (form
  id `start-backtest`). The address `#start-backtest` (command palette) opens
  it. After the start, the page opens the new backtest. The form combines the
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
- Phase 1: the form has the number input "Out-of-sample share" (section
  10.9.4). Phase 3: "Instrument" becomes "Instruments" (section 10.10.7),
  and the form can change the source order (section 10.12). Done in #197:
  the select "Source order" offers each order of the bar sources (for
  example "IBKR, Databento"). Each open selects the global source order.
- The "Backtest limits" dialog (a passive Carbon modal) has the "Limits" form
  (`BacktestLimitsForm`). It shows
  the timeout in minutes (`formatTimeoutMinutes`) and takes only whole
  minutes (`convertTimeoutMinutesToSeconds`). The client functions are
  `readBacktestLimits` and `changeBacktestLimits`.
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

- The backtest list (`routes/backtests/BacktestList.svelte`) has 32px rows:
  the number, the strategy version, the instrument symbol, the status (icon
  and word), and the total return (`ChangeText`). The open backtest has the
  Carbon selected row color, and a click on a row opens its backtest. The
  columns have fixed widths, and a long strategy name ends with an ellipsis.
  The list is in a `ScrollRegion` that fills the side column.
- Each row has a check box. When 2 or more rows are checked, the Carbon batch
  action bar shows above the list with "Compare" and "Cancel".
  `checkComparisonSelection()` of `#lib/backtest` accepts exactly 2
  backtests of the same strategy. For other selections, Compare is disabled
  and the status "Comparison selection" gives the reason. The backend route
  applies the same rule (section 10.5), so a typed URL with different
  strategies shows the refusal.
- Two backtests of the same strategy version are also accepted. They can
  differ in the instrument, the period, or the paper capital. Their code diff
  is empty.
- The page `/backtests/<id>/comparison/<other id>` reads
  `compareBacktests()` and shows a workbench (spec #99, #109): the
  "Backtests" side column (both compared rows marked), the comparison panel
  over the "Comparison tables" panel. The backtest with the lower ID is
  first.
- The comparison panel shows `ComparedKeyMetrics` of `#lib/backtest` (region
  "Compared metrics": one `KeyMetricRow` "Metrics of <name>" for each
  backtest, the same metrics and formats as the backtest page, and a line
  above it with the curve line style and a link to the backtest) and
  `EquityDrawdownChart` with both equity and drawdown curves on one time
  axis. The first curve is a solid line in `--cds-text-primary`, the second a
  dashed line in `--cds-interactive`.
- The Code difference tab shows the code diff (`CodeDiff` of
  `#lib/foundation/code_editor` with `fill`, read-only `@codemirror/merge`
  with wrapped lines, unchanged lines collapsed to the changed parts and 3
  lines around them, in a `ScrollRegion` named "Code difference").
- When both backtests have the same code (the same strategy version), the
  tab shows the status "Same strategy version: no code difference." in place
  of the diff. A closed "Show the code" disclosure shows the full code
  without collapsed lines.
- Phase 1 ([#137](https://github.com/Mano-Liaoyan/ATrade/issues/137)):
  under the `KeyMetricRow` of each backtest, the comparison panel shows the
  robustness row of that backtest (section 10.9.6). The "Comparison tables"
  panel adds the tab Metrics: the Metrics table of section 10.9.6 with the
  columns Metric and one value column for each backtest (the values of the
  full range).

## 10.8 Instruments that are not in USD

Source: [#80](https://github.com/Mano-Liaoyan/ATrade/issues/80). Decisions
of the owner on 2026-10-28:

- The exchange rates are the daily IBKR forex rates. `market_data` saves
  them in PostgreSQL ([`market_data.md`](market_data.md) section 8.6). The
  child reads only saved rates and never calls IBKR.
- At the start, the backtest converts all paper capital to the instrument
  currency. The engine account is in the instrument currency, so the
  strategy sees its cash in that currency. The cash and the position both
  change in USD value when the rate changes.

Rules:

- The rate at a time is the rate of the last day that ended at or before
  that time. A day rate is the close of the day, so a time inside a day
  uses the day before. Thus a backtest never uses a rate from the future.
- `POST /api/backtests` calls `save_exchange_rates()`
  (`backtest/backtest_exchange_rates.py`). It saves the missing rates from 7
  days before the start (`EXCHANGE_RATE_LOOK_BACK`) to the end. The 7 days
  give the start a rate over a weekend or a holiday of the forex market.
  When rates are missing and ATrade is not connected to IB Gateway, or IBKR
  does not return them, the route refuses the request (`422`, no row). The
  message names the currency, the range in UTC, and the reason. Saved rates
  need no IB Gateway.
- When no saved rate is before the start, the route refuses the request
  ("There is no saved HKD to USD exchange rate of a day in the 7 days before
  ..."). The child fails with the same message.
- The child:
  1. Converts the paper capital to the instrument currency at the start
     rate, with the decimal places of the currency (2 for HKD).
  2. Runs the engine with this cash. The trades are in the instrument
     currency.
  3. Calculates the equity curve in the instrument currency with
     `calculate_equity_curve`, then multiplies each point by the rate at its
     time (2 decimal places).
  4. Converts each trade price (4 decimal places) and commission (2 decimal
     places) with the rate at its fill time.
  5. Calculates the metrics in USD from `paper_capital_usd`. So a change of
     the rate is in the total return and the drawdown.
- A USD instrument needs no rates. Its run does not change.
- A same-period backtest of a forward test stays USD only, because a
  forward test has no exchange rates ([`forward_test.md`](forward_test.md)
  section 12.10).
- Tests: `tests/backtest/test_backtest_exchange_rates.py` (the route saves
  the rates from the IBKR fake, uses saved rates without IB Gateway, refuses
  without rates; a real child process converts an HKD backtest with two
  rates, and the test asserts the exact USD trades, equity curve, and
  metrics).

## 10.9 Metrics and robustness checks

Phase 1. Sources: [#132](https://github.com/Mano-Liaoyan/ATrade/issues/132),
[#137](https://github.com/Mano-Liaoyan/ATrade/issues/137). The owner
accepted all recommended options on 2026-10-29. The checks use only the
saved data of one backtest and of the earlier backtests. They need no new
backtest run and no new data source.

### 10.9.1 Daily returns

- All metrics that need a return series use daily returns, for all bar
  periods.
- A daily return is the change of the last equity point of a trading day
  from the last equity point of the trading day before. The first trading
  day uses the paper capital in place of the day before. A backtest on
  1-hour bars thus also has daily returns.
- The annual factor `A` is 252.
- The risk-free rate is 0.
- Reason: a 1-hour backtest and a 1-day backtest give results that the user
  can compare, and `A` does not depend on the trading hours. A backtest
  with about 90 days of 1-hour bars has about 60 daily returns.
- The values differ from TradingView, which uses monthly returns and a
  risk-free rate of 2 %.
- Decided (#165): the trading day of a daily return is the UTC date of the
  equity point. Reason: it is the simplest, and the bars of one US trading
  session end on one UTC date. A day after an equity of 0 has no daily
  return, because a change from 0 has no value.

### 10.9.2 New metrics

The backend calculates the metrics. Backtests and forward tests save them
and use the same functions (section 10.4). `E_0` is the paper capital.
`E_end` is the final equity. `years` is the number of calendar days of the
range divided by 365.25. Decided (#165): the range goes from `start_utc` to
`end_utc` of the backtest request. A forward test uses its start and its stop
(or now). The mean equity of the turnover is the mean of all equity points.

| Metric | Definition |
|---|---|
| CAGR | `(E_end / E_0)^(1 / years) − 1`. |
| Annual volatility | `stdev(daily returns) × sqrt(A)`. `stdev` is the sample standard deviation. |
| Sharpe ratio | `mean(daily returns) / stdev(daily returns) × sqrt(A)`. |
| Sortino ratio | `mean(daily returns) / DD × sqrt(A)`, with `DD = sqrt(Σ min(0, daily return)² / n)`. `n` is the number of all days, not only of the days with a loss. The minimum acceptable return is 0. This is the definition of Sortino and Price (1994). QuantConnect LEAN uses a different `DD`, and its value is about 8 % higher in a test with synthetic data. |
| Calmar ratio | `CAGR / abs(max drawdown)`, on the full range. |
| Profit factor | The sum of the profits of the round trips with a profit, divided by the absolute sum of the profits of the round trips with a loss. Profits are after commissions. |
| Average win | The mean profit (USD) of the round trips with a profit. It also shows as a percent of the entry amount. |
| Average loss | The mean profit (USD, a negative number) of the round trips with a loss. |
| Exposure | The number of bars with a position that is not 0, divided by the number of bars in the range. |
| Turnover | The sum of the amounts of all fills (buy and sell), divided by the mean equity, divided by `years`. The page shows it as a multiple each year, for example "3.2× per year". |
| Win rate | The share of round trips with a profit after commissions. It moves from the frontend to the backend. The profit factor and the win rate use the same round trips (`find_round_trips`). |

### 10.9.3 Short data

When a metric has no meaning, it shows "–". Its tooltip gives the reason.

| Condition | Metrics that show "–" |
|---|---|
| Fewer than 2 daily returns, or a standard deviation of 0 | The ratio metrics (Sharpe ratio, Sortino ratio) |
| The range is shorter than 90 days | CAGR and Calmar ratio |
| The max drawdown is 0 | Calmar ratio |
| No round trip with a loss | Profit factor |
| Fewer than 60 daily returns | The probabilistic and the deflated Sharpe ratio (section 10.9.5), with the reason "Fewer than 60 daily returns" |

Decided (#165): the API gives each "–" value as `null`, and
`metrics.missing_reasons` gives its reason by the field name, for example
`{"sharpe_ratio": "Fewer than 2 daily returns"}`. The reasons come from the
saved values, so the table needs no reason column. These are the reasons:

| Field | Reason |
|---|---|
| `annual_volatility_percent`, `sharpe_ratio`, `sortino_ratio` | "Fewer than 2 daily returns" |
| `sharpe_ratio`, `sortino_ratio` | "The standard deviation of the daily returns is 0" |
| `sortino_ratio` | "No daily return with a loss" (the `DD` is 0) |
| `cagr_percent`, `calmar_ratio` | "The range is shorter than 90 days", or "The final equity is not above 0" |
| `calmar_ratio` | "The max drawdown is 0" |
| `win_rate_percent` and the round trip metrics | "No round trips" |
| `average_win_usd`, `average_win_percent` | "No round trip with a profit" |
| `profit_factor`, `average_loss_usd` | "No round trip with a loss" |
| `turnover_per_year` | "The mean equity is not above 0, or the range has no length" |
| All 12 new fields | "The test has no equity points, or it ended before ATrade calculated this metric" (a backtest that finished before the migration) |

The average win in percent is the mean of the percents of the round trips
with a profit.

Reason for 90 days: a return of 10 % in 3 months gives a CAGR of about
46 %, which misleads. A 1-hour backtest of only the bars that a chart loads
(about 90 days) is at this limit. To see the CAGR, the user must save
longer bars first.

### 10.9.4 In-sample and out-of-sample split

- The "New backtest" form has the number input "Out-of-sample share", in %.
  The default is 30. The range is 0 to 50. 0 means no split.
- The out-of-sample part is the last `out_of_sample_share` percent of the
  backtest range. The split time is the start of the out-of-sample part.
- The start route calculates `split_time_utc`. After the start, nobody can
  change it. To use a different share, the user starts a new backtest.
  Reason: the user must not move the split time after the user sees the
  result.
- The metric functions calculate all metrics of section 10.9.2 three times:
  for the full range ("All"), for the in-sample part, and for the
  out-of-sample part.
- Out-of-sample use count: ATrade counts the finished backtests of the same
  strategy (all strategy versions), the same instrument, and the same bar
  period. It counts only the backtests whose out-of-sample part overlaps
  the out-of-sample part of this backtest. The count includes this
  backtest. A count above 1 means that
  the user saw this out-of-sample part before. ATrade does not refuse such
  a backtest.
- A forward test has no split.
- Decided (#166): the out-of-sample share is a share of the calendar time
  of the range: `split_time_utc = start_utc + (end_utc − start_utc) ×
  (100 − out_of_sample_share) / 100`. The split time does not align to a bar
  end. An equity point or a fill at or before the split time is in sample.
  A round trip is in the part where it ends. The in-sample range goes from
  `start_utc` to the split time, and the out-of-sample range from the split
  time to `end_utc`. The out-of-sample part starts with the equity of the
  last in-sample point (the paper capital when there is none) and with the
  position that is open at the split time. Reason: it is the simplest, and
  it needs no bars.
- Decided (#166): the backend saves no split metrics. The route calculates
  them at each read from the saved equity curve and trades. Reason: no new
  columns, and the metric functions are fast.
- Decided (#166): "Out-of-sample Sharpe / in-sample Sharpe" is
  `out_of_sample sharpe_ratio / in_sample sharpe_ratio × 100`, from the two
  rounded values, with 2 decimal places. It is null when the in-sample
  Sharpe ratio is 0, below 0, or null, or when the out-of-sample Sharpe
  ratio is null. Reason: a percent of a value that is 0 or below has no
  meaning.
- Decided (#166): without `out_of_sample_share`, `POST /api/backtests` uses
  30. Two out-of-sample parts overlap when each starts before the other ends.

### 10.9.5 Probabilistic and deflated Sharpe ratio

- The probabilistic Sharpe ratio PSR(0) is the probability that the real
  Sharpe ratio is above 0. The deflated Sharpe ratio DSR is the PSR with a
  threshold that grows with the trial count
  (Bailey and López de Prado, 2012 and 2014).
- The trial count `N` is the number of finished backtests of the same
  strategy (all strategy versions), the same instrument, and the same bar
  period. The time range does not matter. A change of the code and a change
  of a parameter both count. Phase 3: each run of a parameter sweep counts.
- ATrade calculates `N` when it reads a backtest. Thus a later backtest
  makes the DSR of an earlier backtest lower.
- When `N` is 1, the page shows PSR(0). When `N` is above 1, the page shows
  the DSR.
- The functions use the daily Sharpe ratio (not annualized) of each trial.
  Each backtest has a saved equity curve, so the daily Sharpe ratio of each
  trial comes from the saved data, with no new run.
- Formulas. `SR` is the daily Sharpe ratio of this backtest. `n` is its
  number of daily returns. `γ3` is the skewness and `γ4` the kurtosis (not
  the excess kurtosis) of its daily returns. `Φ` is the standard normal
  distribution.
  - `PSR(SR*) = Φ((SR − SR*) × sqrt(n − 1) / sqrt(1 − γ3 × SR + (γ4 − 1) / 4 × SR²))`.
  - PSR(0) uses `SR* = 0`.
  - DSR uses `SR* = sqrt(V) × ((1 − γ) × Φ⁻¹(1 − 1 / N) + γ × Φ⁻¹(1 − 1 / (N × e)))`.
    `V` is the variance of the daily Sharpe ratios of the `N` trials. `γ` is
    the Euler–Mascheroni constant (about 0.5772). `V` needs at least 2
    trials.
- The backend has no numpy and no scipy. `statistics.NormalDist` of the
  Python standard library has `cdf` and `inv_cdf`. These are sufficient.
- Decided (#167): the route calculates the daily Sharpe ratio of each trial
  from its saved equity curve at each read (`backtest_robustness.py`). It
  saves no Sharpe ratio. Reason: it is the simplest, it needs no migration,
  and the trial count changes at each read too.
- Decided (#167): the daily Sharpe ratio of a trial is the mean of its daily
  returns divided by their sample standard deviation. A trial with fewer
  than 2 daily returns, or with a standard deviation of 0, has no daily
  Sharpe ratio. `V` and the `N` of the formula use only the trials that have
  a daily Sharpe ratio. The trial count of the response counts all trials.
- Decided (#167): when fewer than 2 trials have a daily Sharpe ratio, `V` is
  0. Then `SR*` is 0 and the DSR is equal to PSR(0). The kind stays
  `deflated` when the trial count is above 1.
- Decided (#167): `γ3` and `γ4` use the population moments of the daily
  returns. The functions return a percent with 2 decimal places. The status
  uses this rounded percent.
- Decided (#167): daily returns with a standard deviation of 0 give no PSR
  and no DSR, with the reason "The standard deviation of the daily returns
  is 0".

| Value | Status | Look |
|---|---|---|
| 95 % or more | "Likely real" | Green, checkmark icon |
| 50 % to below 95 % | "Uncertain" | Yellow, warning icon |
| Below 50 % | "Likely luck" | Red, error icon |
| Fewer than 60 daily returns | "–" and the reason "Fewer than 60 daily returns" | No status |

- 95 % is the example value of the source paper. It is strict. Most short
  1-hour backtests show "Uncertain" or "–".
- Not added: a Monte Carlo reorder of the round trips (it measures the path
  risk, not overfitting), White's Reality Check, Hansen's SPA, purged
  cross-validation, and CPCV.

### 10.9.6 Display

- Robustness row: under the `KeyMetricRow`, one `MetricRow` with 3
  `MetricTile`s:
  - "Deflated Sharpe": the percent, the status of section 10.9.5 (icon,
    word, and color), and "<N> backtests counted".
  - "Out-of-sample Sharpe / in-sample Sharpe": a percent.
  - "Out-of-sample used": the count, for example "3 times". A count above 1
    adds a warning icon.
  - Without a split (`out_of_sample_share` 0), the row has only "Deflated
    Sharpe".
- Metrics tab of the "Backtest tables" panel: a Carbon data table with 32px
  rows. The columns are Metric, All, In-sample, and Out-of-sample. Without a
  split, the columns are Metric and All. The number columns are right
  aligned and use tabular numbers.
- Each metric name in the Metrics table has a tooltip with its definition
  and "Risk-free rate: 0". A "–" value has a tooltip with its reason.
- `EquityDrawdownChart` draws one vertical line at the split time. The two
  parts have no names.
- The comparison page shows a robustness row under the `KeyMetricRow` of each
  backtest, and a Metrics table with one value column for each backtest
  (section 10.7).
- The page adds no other label or description (AGENTS.md, frontend rule
  one).
- Decided (#168): the Metrics table has the metrics of section 10.9.2 in
  this order: CAGR, Annual volatility, Sharpe ratio, Sortino ratio, Calmar
  ratio, Profit factor, Win rate, Average win (USD), Average loss (USD),
  Exposure, and Turnover. These are the English names in the UI. The
  average win shows the USD value and the percent of the entry amount, for
  example "+1,234.50 (+2.10 %)". The turnover shows the API value with 2
  decimal places, for example "3.20× per year". Each name is a Carbon
  definition term. Its tooltip is the formula and "Risk-free rate: 0".
  `readMetricRows(metricSets)` gives one value column for each set of
  metrics, so the In-sample and Out-of-sample columns (#169) and the
  comparison page can use the same rows.

### 10.9.7 Left to the implementation

- The tile name and the tooltip when the tile shows PSR(0) (trial count 1).

## 10.10 Multi-instrument backtest

Phase 3. Sources: [#131](https://github.com/Mano-Liaoyan/ATrade/issues/131),
[#142](https://github.com/Mano-Liaoyan/ATrade/issues/142),
[#145](https://github.com/Mano-Liaoyan/ATrade/issues/145),
[#146](https://github.com/Mano-Liaoyan/ATrade/issues/146). Decision record:
[ADR 0003](../adr/0003-one-simulated-venue-per-currency.md).

### 10.10.1 Decisions

- A backtest can trade a universe in place of one instrument.
- The platform gives the strategy only the universe of the current time. At
  the start of each universe period, the platform tells the strategy the new
  list and gives it the bars of the new members. The strategy cannot read a
  later list. Reason: a list of all quarters in the strategy configuration
  lets the code read future lists (look-ahead bias), and the platform cannot
  check that.
- The strategy code does the ranking, sets the rebalance period, and sends
  the orders. The multi-instrument code templates show a monthly rebalance:
  sell first, then buy after the sell orders fill
  ([`strategy.md`](strategy.md) section 9.9.3).
- All instruments of one currency go on one simulated venue (`SMART` for US
  instruments). The strategy gets the instrument IDs `SYMBOL.SMART`. All
  instruments share one cash account. The trade table records the real
  exchange. A single-instrument backtest keeps the exchange as the venue.
- A multi-instrument backtest has one currency. The equity curve and the
  metrics change to USD as in section 10.8.
- The bar period is 1 day or 1 hour. One backtest uses one bar period.
- The child reads the bars of each instrument only for the universe periods
  in which it is a member, plus its look-back bars.
- The look-back length of a multi-instrument backtest on 1-day bars is
  1 year ([#146](https://github.com/Mano-Liaoyan/ATrade/issues/146)).

### 10.10.2 Universe kinds

| `universe_kind` | Source | Universe period | Universe parameters |
|---|---|---|---|
| `single` | One instrument. The existing backtest. | None | `symbol`, `exchange`, `currency` |
| `rule` | Point-in-time rule: the top N instruments by trading value of each quarter (`us_universe_member` with `rank` ≤ N, [`market_data.md`](market_data.md) section 8.9). N is 500 at most. US only. | Quarter | `universe_top_n` |
| `list` | Fixed list: the watchlist, a screen result, or the selected rows of a screen result. The list does not change in the range. The form warns of survivorship bias. | The full range | The members (`backtest_universe_member` with `period_start_utc` = `start_utc`) |
| `screen` | Point-in-time rule: at each universe period start, the platform runs a copy of the screen again on the daily bars known at that date. The result is the new list. | Quarter (default) or month | `universe_screen` (JSON copy of the screen), `universe_rebalance_period` (`quarter` or `month`) |

- The backtest saves a copy of the screen. A later change of the screen does
  not change the backtest ([#145](https://github.com/Mano-Liaoyan/ATrade/issues/145)).
- A `screen` backtest calculates the indicators of all instruments of the
  base universe at each universe period start (for example 34 quarters × 500
  instruments).
- `backtest_universe_member` holds the members of each universe period. The
  Instruments tab and the same-period backtest read it.
- The same-period backtest of a multi-instrument forward test uses the
  allocated capital as paper capital and the members that the forward test
  recorded for each quarter
  ([#146](https://github.com/Mano-Liaoyan/ATrade/issues/146),
  [`forward_test.md`](forward_test.md) section 12.10).

### 10.10.3 Engine facts

Checked with NautilusTrader 2.0.0rc7 and synthetic bars
([#131](https://github.com/Mano-Liaoyan/ATrade/issues/131),
[#142](https://github.com/Mano-Liaoyan/ATrade/issues/142)):

- One `BacktestEngine` can hold many instruments. A strategy can subscribe
  to the bars of each instrument and rank them on a timer
  (`clock.set_timer`).
- NautilusTrader makes one cash account for each venue. `routing=True` does
  not merge the venues: the engine refuses an instrument whose venue was
  not added.
- In one multi-currency account, USD cash cannot pay for an HKD instrument.
  The engine does not convert cash, also with a USD/HKD pair in the account.
- A market order fills at the open of the next bar. The cash of a sell is
  free only after its fill. A buy that the strategy sends at the same time
  as a sell can use only the cash from before the sell.
- One fill uses at most 1/4 of the bar volume. The engine fills the rest of
  the order in one more fill, at a price 1 tick different. All orders end as
  `FILLED`. Thus a test can have more trades than orders (29 trades for 23
  orders).
- 500 instruments × 2,500 daily bars: `run()` takes 2.45 seconds, with a
  peak memory of about 2 GB.
- Custom data (checked in #198): `subscribe_data(DataType(...))` without a
  client ID gets the custom data that `add_data` added. With a client ID,
  the backtest engine finds no data client and logs an error. Data items
  with the same time come in the order of the `add_data` calls.
- Estimate, not checked: a universe of 500 instruments on 1-hour bars has
  about 7.35 million bars (about 2,100 trading days × 7 bars). One run then
  takes about 15 seconds, with a peak memory of 4 to 5 GB.

### 10.10.4 Run flow changes

1. `POST /api/backtests` checks the universe (section 10.10.6). For a
   universe that is not in USD, it saves the missing exchange rates as in
   section 10.8.
2. The runner does not change.
3. The child reads the saved bars of each member for its universe periods,
   plus the look-back bars, through the source order (section 10.12).
4. The child converts the bars of all members to Arrow bytes.
5. The child runs the engine with one simulated venue for the currency, one
   `CASH` account with the paper capital in that currency, one `Equity`
   instrument for each member, `NETTING` positions, and a zero commission.
6. The equity curve is the cash plus the value of all positions at the bar
   close prices. The metric functions take trades of many instruments.
7. The child writes the trades with `symbol` and the real `exchange`.

Done in #199: `backtest/backtest_universe.py` (universe periods, the saved-bar
check, the bars of each member), `backtest/universe_engine_run.py` (the
engine run), and `backtest/universe_update.py` (`UniverseUpdate`). The
look-back bars of all members go to one catalog. A `request_bars` gets only
the bars up to the engine time: NautilusTrader refuses an `end` after the
engine time, and without `end` it stops at the engine time. Thus the
look-back bars of a later member cannot give a strategy future bars. Tests:
`tests/backtest/test_universe_backtest_routes.py`,
`test_universe_backtest_runs.py`, `test_universe_bars.py`, and
`test_universe_metrics.py`.

### 10.10.5 Metrics

- A multi-instrument backtest uses the metric functions of section 10.4 and
  section 10.9.
- The key metrics and the equity curve do not change.

### 10.10.6 HTTP

`POST /api/backtests` has the field `universe_kind`. Without it, the kind is
`single`, and the body is the body of section 10.5.

| `universe_kind` | Fields |
|---|---|
| `single` | `symbol`, `exchange`, `currency` |
| `rule` | `top_n` |
| `list` | `instruments` (`[{"symbol", "exchange", "currency"}]`), or `screen_result_id` with an optional `symbols` list (a part of that screen result) |
| `screen` | `screen_id`, `rebalance_period` (`quarter` or `month`, default `quarter`) |

`422` (no row) in these cases, in addition to the cases of section 10.5:

- `universe_kind` is not a known value.
- `top_n` is not from 1 to 500.
- The list has no instrument, or its instruments have more than one
  currency, or it has one symbol on 2 exchanges (the simulated venue has
  one instrument for each symbol, ADR 0003).
- The body has a universe field that its `universe_kind` does not use, for
  example `top_n` with `list`.
- The bar period of a universe that is not `single` is not 1 day or 1 hour.
- The screen or the screen result does not exist.
- No universe data covers the range (`rule`).

The field names are choices of this document. The implementation can change
them.

Done in #199 for `single`, `rule`, and `list` with `instruments`. The
`screen` kind and `screen_result_id` are
[#208](https://github.com/Mano-Liaoyan/ATrade/issues/208): the route refuses
`universe_kind=screen` with `422` until then. The first `rule` period starts
at `start_utc` and holds the members of the last quarter that starts at or
before `start_utc`. Each later quarter that starts before `end_utc` is one
more period. When no quarter starts at or before `start_utc`, the route
refuses the request ("No universe data covers the range").

### 10.10.7 Frontend

- The "Instrument" select of the "New backtest" form becomes "Instruments".
  It has these options:
  - One instrument (the existing select).
  - Top N by trading value, with a number input for N. The form shows the
    first and the last day with universe data.
  - Watchlist. The form shows a survivorship bias warning.
  - Screen ([#145](https://github.com/Mano-Liaoyan/ATrade/issues/145)): a
    screen and a mode. The mode is the point-in-time rerun (the default,
    with the period Quarter or Month), or the fixed list of one screen
    result. The fixed list shows a survivorship bias warning.
- On the screen page, "Run backtest on this screen result" and "Run backtest
  on selected" open the "New backtest" form with the screen filled in.
- The backtest panel header line of a multi-instrument backtest shows the
  universe in place of the instrument symbol, for example "Top 500 by
  trading value" or "Watchlist (12)". Example header line:
  "#42 Momentum v3 · Top 500 by trading value · 1 day · Finished".
- The "Backtest tables" panel adds the tab Instruments: one row for each
  instrument. The columns are the instrument, the trade count, the net
  profit (USD), and the number of quarters in the universe. The number
  columns are right aligned and use tabular numbers.
- The Trades table adds the column Symbol.
- The `KeyMetricRow` and the `EquityDrawdownChart` do not change.

### 10.10.8 Left to the implementation

- Decided (#198): the platform tells the strategy the new list at a
  universe period start with NautilusTrader custom data, not with a
  platform timer. For each universe period start, the child adds one
  `CustomData` with `DataType("UniverseUpdate")` to the engine data. Its
  data is a `UniverseUpdate` (`@customdataclass`). The field `bar_types`
  holds the bar types of the members, joined with commas, for example
  `AAA.SMART-1-DAY-LAST-EXTERNAL,BBB.SMART-1-DAY-LAST-EXTERNAL`.
  `ts_event` and `ts_init` are the period start. The child adds the bars
  before the `UniverseUpdate` items. Thus the bar that closes at a period
  start comes before the list of that period (section 10.10.3). The strategy calls
  `subscribe_data(DataType("UniverseUpdate"))` in `on_start` and gets the
  list in `on_data(data)` as `data.data.bar_types`. Then it subscribes to
  the bars of the new members and unsubscribes from the bars of the old
  members. Reason: a timer needs the list in the strategy before the time,
  so the strategy can read a later list. The engine sends the custom data
  in time order with the bars, so the strategy cannot read a later list.
  The regression test is `backend/tests/backtest/test_universe_update.py`.
  The test file holds the `UniverseUpdate` class until the
  multi-instrument backtest
  ([#199](https://github.com/Mano-Liaoyan/ATrade/issues/199)) moves it to
  the platform code. Done in #199: `backend/src/atrade/backtest/universe_update.py`.
- Decided (#198): the configuration of a multi-instrument strategy has no
  `instrument_id`, no `bar_type`, and no universe field. The platform fills
  no universe field. The strategy gets the bar types only from
  `UniverseUpdate`, and the instrument ID of a member from
  `BarType.instrument_id`.
- Decided (#199): the start route writes `backtest_universe_member` in the
  transaction that adds the backtest row. A `screen` universe (#208) can
  decide again, because it needs the daily bars of each date.
- The decision names the member column "quarter start". This document uses
  `period_start_utc`, because a `screen` universe can change each month.
- Decided (#199): the bar check of section 10.1 for a universe needs one
  saved bar of one member in a period in which it is a member. The check
  stops at the first member with a bar.
- Decided (#199): the look-back length of a multi-instrument backtest on
  1-hour bars is the single-instrument length (section 10.3.1): 7 days.
- Decided (#199): a `list` universe has 500 instruments at most, the same
  as `top_n`.
- Decided (#199): all members are on the simulated venue `SMART`, also for
  a currency that is not USD. A strategy that sells a member at the period
  start in which it leaves gets a fill at the last close of that member: the
  child reads no bars of the member after its last period.
- The header line text of a `screen` universe, and the Instruments tab
  column for a monthly `screen` universe (quarters or months).
- The `universe_kind` value of the same-period backtest of a
  multi-instrument forward test.
- Decided (#199): the round trips count for each instrument
  (`find_round_trips` groups the trades by `symbol` and `exchange`), so the
  win rate, the profit factor, and the average win and loss use them. The
  exposure counts the bars with a position that is not 0 in any instrument.
  The trial count of section 10.9.5 counts the finished backtests of the same
  strategy, bar period, `universe_kind`, currency, and `universe_top_n`.
  Single-instrument results do not change.
- Whether `run_backtest` of the AI assistant also accepts `rule` and the
  watchlist (section 10.13).

## 10.11 Parameter sweep

Phase 3. Sources: [#131](https://github.com/Mano-Liaoyan/ATrade/issues/131),
[#132](https://github.com/Mano-Liaoyan/ATrade/issues/132),
[#137](https://github.com/Mano-Liaoyan/ATrade/issues/137),
[#142](https://github.com/Mano-Liaoyan/ATrade/issues/142).

### 10.11.1 Parameters

- A parameter is a field of the `StrategyConfig` subclass with an `int`,
  `float`, or `bool` type annotation and a default value. `instrument_id`,
  `bar_type`, and the universe are not parameters.
- ATrade reads the parameters from the `__init__` of the `StrategyConfig`
  subclass with the Python AST. It does not import the user code (the same
  rule as the checks before save, [`strategy.md`](strategy.md) section 9.3).
  A field without a type annotation cannot be in a sweep.
- For an `int` or `float` parameter, the user gives a start, an end, and a
  step. For a `bool` parameter, the sweep uses both values.
- ATrade makes a grid of all combinations.
- Limits: 3 parameters at most. 200 runs at most for each sweep.
- `parameter_grid` (JSON) holds the grid:
  `[{"name", "type", "start", "end", "step"}]`, or
  `{"name", "type": "bool", "values": [false, true]}` for a `bool`
  parameter.
- The child gives the `parameters` of a run to the strategy configuration.
  The other fields keep their default values.
- Each run counts in the trial count of the DSR (section 10.9.5).
- Not in this phase: a random search or an optimizer (for example a
  Bayesian optimizer).

### 10.11.2 Runs and the backtest limits

- Each combination is one `backtest` row with `sweep_id` and `parameters`.
  It waits in the same queue as other backtests.
- Each run has its own child process and its own timeout. The sweep has no
  timeout of its own. The concurrency of the backtest limits applies.
- The user can cancel a sweep. The queued runs get the status `cancelled`.
- A run opens on the backtest page like any other backtest.
- Cost, measured on 2026-10-29 with synthetic daily bars, a rotation
  strategy, and one `SMART` venue
  ([#142](https://github.com/Mano-Liaoyan/ATrade/issues/142)):

| Instruments × bars × runs | One engine with `reset()` | One child for each run | Peak memory |
|---|---|---|---|
| 50 × 1,000 × 20 | 1.98 s (0.094 s each run) | 5.43 s (0.272 s each run) | 324 MB / 302 MB |
| 500 × 2,500 × 5 | 13.37 s (2.40 s each run) | 19.57 s (3.91 s each run) | 1,696 MB / 1,986 MB |
| 500 × 10,000 × 1 | 10.0 s | — | 3,274 MB |

- Both methods give the same result for each run. ATrade uses one child for
  each run. A sweep of 200 runs on the daily bars of 500 instruments takes
  about 13 minutes with concurrency 1 (estimate).
- `BacktestNode` of NautilusTrader 2.0.0rc7 accepts only 1 run
  configuration. It cannot run a sweep.

### 10.11.3 HTTP routes

| Route | Behavior |
|---|---|
| `GET /api/sweeps/parameters?strategy_version_id=<id>` | `200` with `{"parameters": [{"name", "type", "default"}]}`, the parameters of section 10.11.1. `404` when the strategy version does not exist. |
| `POST /api/sweeps` | Body: the fields of `POST /api/backtests` (strategy version, universe, bar period, range, `paper_capital_usd`, `out_of_sample_share`) and `parameters` (the grid of section 10.11.1). `201` with the sweep. The route queues all runs. `422` (no row) in these cases: a backtest field has an error (the cases of `POST /api/backtests`). The grid has no parameter or more than 3. A name is not a parameter of the strategy version. A step is not above 0. An end is before its start. The grid has more than 200 runs. |
| `GET /api/sweeps` | `200` with all sweeps, the newest first. Each sweep has `id`, the strategy version fields, the universe, the bar period, the range, `run_count`, and the number of runs in each status. |
| `GET /api/sweeps/{sweep_id}` | `200` with the sweep and `runs` (`[{"backtest_id", "parameters", "status", "metrics"}]`). `404` when the sweep does not exist. |
| `POST /api/sweeps/{sweep_id}/cancel` | `200` with the sweep. The queued runs get `cancelled`. `404` when the sweep does not exist. |

- `strategy` exports the function that reads the parameters with the AST.
  `backtest` already imports `strategy`.
- The AI assistant port does not allow these routes
  ([#150](https://github.com/Mano-Liaoyan/ATrade/issues/150)).
- The route paths and the JSON names are choices of this document. The
  implementation can change them.

### 10.11.4 Sweep page

`/sweeps/<id>` is the sweep workbench. It has the layout of the backtest page.
Most products with parameter optimization (QuantConnect, MetaTrader 5,
NinjaTrader 8) show the result in a separate view with a sorted result table
and a parameter chart. ATrade uses a heat map, not a 3D chart, because a 3D
chart is hard to read on flat Carbon surfaces.

- The "Parameter sweeps" `SideColumn` has the "New parameter sweep" icon
  button and the sweep list. Each row has the number, the strategy version,
  the status, and the finished runs / all runs.
- Top panel:
  - A status line with the number of finished, failed, running, and queued
    runs.
  - With 1 parameter: a point chart. With 2 or 3 parameters: a heat map.
  - A "Metric" select. The default is Total return. With 3 parameters, a
    second select chooses the value of the third parameter.
  - Each heat map cell shows its value as text. The cell color is a Carbon
    sequential color.
- Bottom panel "Runs": one row for each run. The columns are the parameter
  values and the key metrics. The user can sort each column. A click on a
  row opens its backtest.
- The backtest list does not show sweep runs by default. The backtest panel
  header line of a sweep run has a link to its sweep.
- The "New parameter sweep" dialog has the fields of the "New backtest"
  form. It also has one row for each parameter. A row has the name, the
  default value, a check box that adds the parameter to the sweep, and the
  start, end, and step inputs. The dialog
  shows the run count while the user types. When the grid has more than 200
  runs or more than 3 parameters, "Start parameter sweep" is disabled, and
  the dialog says why.
- Prototype: a heat map of 8 × 12 cells for `roc_period` (5 to 40) and
  `rebalance_days` (5 to 60), and the Runs table sorted by Total return,
  highest first.
- The page adds no other label or description (AGENTS.md, frontend rule
  one).

### 10.11.5 Robustness checks of a sweep

These checks come with the parameter sweep
([#132](https://github.com/Mano-Liaoyan/ATrade/issues/132),
[#137](https://github.com/Mano-Liaoyan/ATrade/issues/137)):

- Parameter sensitivity: the point chart and the heat map of section
  10.11.4. They show if the near parameter values give similar results.
- Walk-forward check.
- Probability of backtest overfitting (PBO), with combinatorially symmetric
  cross-validation (CSCV).

Each run has a saved equity curve, so these checks can use the daily
returns of all runs of a sweep.

### 10.11.6 Left to the implementation

- The method, the windows, and the display of the walk-forward check.
- The partitions, the input, and the display of the PBO.
- What happens to a running run when the user cancels its sweep, and the
  status of a sweep.
- The header link to `/sweeps`, and the page that `/sweeps` without an ID
  opens.
- The chart library of the point chart and the heat map.
- The grid values of a `float` step that does not divide the range.
- How the backtest list shows sweep runs when the user asks for them.
- Whether a sweep has an out-of-sample share (this document adds it to
  `parameter_sweep`).

## 10.12 Bar sources and survivorship bias

Phase 3. Sources: [#141](https://github.com/Mano-Liaoyan/ATrade/issues/141),
[ADR 0002](../adr/0002-one-bar-table-per-bar-source.md),
[`market_data.md`](market_data.md) section 8.7.

- The child reads the bars and the look-back bars through a source order.
  By default, it is the global source order. The "New backtest" form can
  change it for one backtest.
- For each time range, the first bar source in the source order that saved
  the range gives all bars of the range. Another bar source does not fill a
  holiday.
- Each backtest saves the source order that it used (`source_order`) and
  the bar count of each bar source (`bar_count_by_source`). The backtest
  page shows both.
- The backtest page shows a survivorship bias warning for these backtests:
  - an HK backtest,
  - a US backtest that starts before 2018-05-01 (the start of the Databento
    history).
- The warning text is "The universe has survivorship bias: instruments that
  stopped trading are missing." It is a Carbon warning with an icon.
- Decided (#197): the "Bar sources" tab of the "Backtest tables" panel
  shows the source order and the bar counts: a data table with one row for
  each bar source in the source order, and the columns "Bar source" and
  "Bars" (right-aligned tabular numbers). A backtest from before the source
  order shows "No bar sources". A backtest that did not finish shows "–" as
  its bar counts.
- Decided (#197): `bar_count_by_source` counts the bars of the backtest
  range. The look-back bars are read through the same source order, but are
  not counted.
- Decided (#197): the backend gives `survivorship_bias`. An HK backtest is a
  backtest in `HKD`. A US backtest is a backtest in `USD`. The warning shows
  over the key metric row of the backtest panel. It is the shared component
  `SurvivorshipBiasWarning` of `frontend/src/lib/market_data/` (a low-contrast
  Carbon warning notification). The screen page and the multi-instrument
  backtest form use the same component.
- Code (#197): `backtest_access.py` (`has_survivorship_bias`,
  `add_global_source_order`), `backtest_run.py`, `backtest_store.py`, and
  `frontend/src/routes/backtests/BarSourceTable.svelte`. Tests:
  `backend/tests/backtest/test_backtest_bar_sources.py`,
  `frontend/e2e/backtest_bar_sources.spec.ts`.
- Left to the implementation: whether a `list` universe also shows the
  warning on the backtest page. The English warning text is a translation
  of the decided Chinese text.

## 10.13 Backtests of the AI assistant

Sources: [#140](https://github.com/Mano-Liaoyan/ATrade/issues/140),
[#150](https://github.com/Mano-Liaoyan/ATrade/issues/150).

Phase 2 ([#140](https://github.com/Mano-Liaoyan/ATrade/issues/140)):

- The AI assistant tool `run_backtest` calls `POST /api/backtests` on the
  assistant port.
- `run_backtest` waits at most 15 minutes after it queues the backtest, and
  sends the status while it waits. After 15 minutes, it returns "still
  running" and the backtest ID. The AI assistant reads the result later
  with `read_backtest`.
- The backtests of the AI assistant and of the user share one queue and one
  set of backtest limits.
- The AI assistant can run a backtest only on instruments and bar periods
  with saved bars. It cannot load bars.
- Each user message can start 5 backtests at most. At the limit, the tool
  returns an error, and the AI assistant must ask the user first.
- A backtest that the AI assistant starts records the conversation ID. When
  the user deletes the conversation, the ID becomes null. The backtest stays.
- The AI assistant cannot change the backtest limits and cannot start a
  parameter sweep.
- Decided (#181): `POST /api/backtests` on port 8001 makes the same checks
  as port 8000 (`start_backtest`). When the instrument is not in USD and a
  daily exchange rate is missing, it saves the rates from IBKR (section
  10.8), like port 8000. The rule "cannot load bars" is about bars only. A
  backtest without saved bars gets `422` (section 10.1).
- Decided (#182): only the tool `run_backtest` counts the 5 backtests of a
  user message. Port 8001 does not count them. A steer message is a new
  user message, so it starts a new count. Only a backtest that
  `POST /api/backtests` accepted counts. A `422` does not count. The tool
  counts a backtest before its POST, so parallel tool calls of one model
  turn also start at most 5.
- Decided (#182): while it waits, `run_backtest` reads
  `GET /api/backtests/{backtest_id}` every 2 seconds. It sends each new
  status (`queued`, `running`, then the final status) with `onUpdate`. The
  browser gets each one as a `tool_step` (assistant section 25.10). After a
  final status, the tool result is the `read_backtest` content and the
  browser gets `backtest_finished`. After 15 minutes, the tool returns
  "still running" with the backtest ID and the last status. The backtest
  continues in the queue.
- Decided (#182): no new route finds the instruments and bar periods with
  saved bars. The AI assistant uses the instrument that the user names, or
  an instrument of `list_backtests`. A range without saved bars gets `422`,
  and the tool gives this `422` to the model.

Phase 3 ([#150](https://github.com/Mano-Liaoyan/ATrade/issues/150)):

- `run_backtest` accepts 2 kinds of universe from a screen. The default is
  the point-in-time rerun:
  - Point-in-time rerun: a screen ID and the rebalance period (quarter or
    month). `universe_kind` is `screen`.
  - Fixed list: a screen result ID, and optionally a part of its
    instruments. `universe_kind` is `list`. The tool result has a
    survivorship bias warning. The AI assistant must write this warning in
    its reply.
- One multi-instrument backtest counts as 1 of the 5 backtests of a user
  message. The 15-minute wait does not change.
