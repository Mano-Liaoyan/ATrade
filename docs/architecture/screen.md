# Screens

This document is section 24 of the architecture specification
([`docs/architecture.md`](../architecture.md)). It is a new section of the
planning map
[Wayfinder: indicators, screens, and strategy help](https://github.com/Mano-Liaoyan/ATrade/issues/129).
Terms have the meaning that [`GLOSSARY.md`](../../GLOSSARY.md) gives them.

Sources: [Indicator library scope and calculation place](https://github.com/Mano-Liaoyan/ATrade/issues/136),
[Screen page prototype](https://github.com/Mano-Liaoyan/ATrade/issues/145),
[How the AI assistant uses screens](https://github.com/Mano-Liaoyan/ATrade/issues/150),
ADR [0001](../adr/0001-one-indicator-definition-for-screens-and-strategies.md).

Phase: screens are part of phase 3 of the map #129 (data sources, screens,
multi-instrument backtest, parameter sweep and walk-forward,
multi-instrument forward test). The AI assistant tools of section 24.8 need
phase 2 (the AI assistant) and phase 3.

## 24.1 Decisions

Source: [Indicator library scope and calculation place](https://github.com/Mano-Liaoyan/ATrade/issues/136),
[Screen page prototype](https://github.com/Mano-Liaoyan/ATrade/issues/145).

- A new module `screen/` saves screens, runs them, and saves screen results.
- A screen uses the indicator classes of section 23 on saved daily bars.
  There is no table of indicator values. A run calculates the values from
  the saved daily bars.
- A run has 2 steps:
  1. Filters: a filter uses only the daily bar summary of each instrument
     and the instrument data (section 24.5). It reads 1 row for each
     instrument.
  2. Indicator conditions: only for the instruments that step 1 keeps. Each
     indicator reads only its look-back bars (section 23.4).
- All conditions must be true ("and"). The first version has no "or".
- The result does not depend on the order of the conditions.
- An instrument with "no value" for an indicator of a condition or of the
  order is not in the result. The excluded list gives the reason
  "No value: <indicator>".
- Each screen belongs to 1 market: US or HK. One multi-instrument backtest
  has 1 currency (ADR [0003](../adr/0003-one-simulated-venue-per-currency.md)),
  so a screen result can be the universe of one backtest.
- A screen has no versions. A change overwrites the screen. A backtest saves
  a copy of the screen that it used, so a later change does not change an
  old backtest.
- Each run saves 1 screen result: the run time, a copy of the screen, and
  the instruments in their order.
- The daily bars and the daily bar summary come from the bar sources in the
  global source order. Both use the same source order
  ([#141](https://github.com/Mano-Liaoyan/ATrade/issues/141), #136).

Measured in #136 (pure Python, no database read, 11 indicators, 260
synthetic daily bars for each instrument, 1 run): 10000 instruments in 1.97
seconds, 1500 instruments in 0.29 seconds.

## 24.2 Markets and start instruments

Source: [Screen page prototype](https://github.com/Mano-Liaoyan/ATrade/issues/145) Q3.

A screen starts from one list of instruments of its market:

| Market | Start instruments | Default |
|---|---|---|
| US | The universe of the current quarter: the top 500 common stocks by average trading value of the last 63 trading days, with no ETFs ([#141](https://github.com/Mano-Liaoyan/ATrade/issues/141)) | Yes |
| US | All US instruments with saved daily bars | No |
| US | The US instruments of the watchlist | No |
| HK | The HK instrument list (`market_data.md`, the HK instrument list section) | Yes |
| HK | The HK instruments of the watchlist | No |

- An HK screen shows a warning: "The universe has survivorship bias: it has
  no instruments that stopped trading." Source text (#145): 品种池含幸存者偏差：缺少已退市的品种。
- The user keeps the HK instrument list. The screen page does not change it.

## 24.3 Conditions and order

Source: [Screen page prototype](https://github.com/Mano-Liaoyan/ATrade/issues/145) Q2.

A screen has 4 parts, in this fixed order:

1. The start instruments (section 24.2).
2. Filters (step 1). Each filter uses the daily bar summary:

   | Field | Condition |
   |---|---|
   | Still trading | The instrument still trades. |
   | Close | The close (official close) of the last daily bar compared with a number. |
   | Avg trading value (20) | The average trading value of the last 20 daily bars compared with a number, in the currency of the market. |
   | Exchange | The exchange is one of the selected exchanges. |

3. Indicator conditions (step 2). 3 kinds:

   | Kind | Example |
   |---|---|
   | Indicator value compared with a number | RSI(14) < 30 |
   | Close above or below a line | Close above SMA(200). The lines are SMA, EMA, and the Donchian channel upper line. |
   | Rank | Top 20% by 12-1 momentum. Top or Bottom, N from 1 to 100 percent. |

4. One order: an indicator, a direction, and an optional "keep only the
   first N".

Rank rule:

- `screen` calculates the percentile of a rank condition only among the
  instruments that step 1 keeps and that have a value of the rank
  indicator.
- So the rank does not depend on the other indicator conditions, and the
  result does not depend on the order of the conditions.
- A rank condition adds a "Percentile" column to the result.

## 24.4 Tables

The tables belong to `screen`. The column names are choices of this
document.

| Table | Columns |
|---|---|
| `screen` | `id`, `name` (unique, 1 to 100 characters), `market` (`US` or `HK`), `definition` (JSON, section 24.4.1), `assistant_conversation_id` (null for a screen that the user made. Foreign key to the conversation table, `ON DELETE SET NULL`.), `kept` (boolean: true for a screen that the user made, false for a screen of the AI assistant until the user selects Keep), `created_at_utc`, `updated_at_utc` |
| `screen_result` | `id`, `screen_id`, `run_at_utc`, `definition` (a copy of the screen at the run), `market`, `daily_bars_date` (the date of the last daily bar that the run used), `run_seconds`, the 4 funnel counts (`start_count`, `after_filters_count`, `after_indicator_conditions_count`, `result_count`), `assistant_conversation_id` (null for a run of the user, `ON DELETE SET NULL`) |
| `screen_result_row` | `screen_result_id`, `position` (1 is the first), `symbol`, `exchange`, `currency`, `values` (JSON: last price, average trading value (20), each indicator value, each percentile). Primary key `(screen_result_id, position)`. |
| `screen_result_exclusion` | `screen_result_id`, `symbol`, `exchange`, `currency`, `reason` (the location of the condition that is not true, or "no value" with the indicator) |

- A screen result has at most 500 rows (#145 Q6, #150 A4).
- A delete of a conversation keeps its screens and its screen results. Their
  `assistant_conversation_id` becomes null (#150 A3, B4).
- PostgreSQL deletes the rows and the excluded list of a screen result with
  the screen result (`ON DELETE CASCADE`).
- Decided (#205): the migration `d41ce3053ba2_screen_create_tables.py` makes
  the 4 tables with these column names. `screen_result.screen_id` is
  `ON DELETE CASCADE`: a delete of a screen deletes its screen results. A
  backtest keeps its own copy of the screen (section 24.1). `result_count`
  and `screen_result_row.position` are at most 500.

### 24.4.1 Screen definition

The definition is JSON. The indicator reference is the reference of section
23.6. Example:

```json
{
  "start": "quarter_universe",
  "filters": [
    {"field": "still_trading"},
    {"field": "last_price", "operator": ">", "value": "5"},
    {"field": "average_trading_value_20", "operator": ">", "value": "5000000"},
    {"field": "exchange", "values": ["NASDAQ", "NYSE"]}
  ],
  "indicator_conditions": [
    {"kind": "compare", "indicator": {"indicator": "rsi", "parameters": {"period": 14}, "output": "value"}, "operator": "<", "value": "30"},
    {"kind": "close_versus_line", "indicator": {"indicator": "sma", "parameters": {"period": 200}, "output": "value"}, "side": "above"},
    {"kind": "rank", "indicator": {"indicator": "momentum_12_1", "parameters": {}, "output": "value"}, "end": "top", "percent": 20}
  ],
  "order": {"indicator": {"indicator": "momentum_12_1", "parameters": {}, "output": "value"}, "direction": "descending", "keep_first": 50}
}
```

- `start` is one of `quarter_universe`, `all_with_daily_bars`, `watchlist`
  (US), or `hk_instrument_list`, `watchlist` (HK).
- Numbers are decimal strings, as in the other routes.
- `keep_first` is optional.
- Decided (#205): the JSON has exactly these keys. All 4 top-level keys are
  required. The `filters` and `indicator_conditions` lists can be empty.

  | Part | Keys | Values |
  |---|---|---|
  | Filter `still_trading` | `field` | |
  | Filter `last_price`, `average_trading_value_20` | `field`, `operator`, `value` | `operator`: `<`, `<=`, `>`, `>=`. `value`: a decimal string. |
  | Filter `exchange` | `field`, `values` | A list of 1 or more exchanges. |
  | Condition `compare` | `kind`, `indicator`, `operator`, `value` | As the number filters. |
  | Condition `close_versus_line` | `kind`, `indicator`, `side` | `indicator`: `sma` or `ema` with the output `value`, or `donchian_channel` with the output `upper`. `side`: `above` or `below`. |
  | Condition `rank` | `kind`, `indicator`, `end`, `percent` | `end`: `top` or `bottom`. `percent`: an integer from 1 to 100. |
  | `order` | `indicator`, `direction`, optional `keep_first` | `direction`: `ascending` or `descending`. `keep_first`: an integer from 1 to 500. |

## 24.5 Run flow

Source: [Indicator library scope and calculation place](https://github.com/Mano-Liaoyan/ATrade/issues/136) Q2 of round 3,
[Screen page prototype](https://github.com/Mano-Liaoyan/ATrade/issues/145) Q4.

1. Read the start instruments (section 24.2).
2. Read the daily bar summary of each start instrument. Apply the filters.
3. For the instruments that step 2 keeps, read the daily bars that the
   indicators of the conditions and the order need (section 23.4). Read
   them for all instruments in one database read, not one read for each
   instrument.
4. Give the bars to the indicator classes. An instrument with "no value"
   goes to the excluded list.
5. Calculate the percentiles of the rank conditions (section 24.3).
6. Apply the indicator conditions. Sort by the order. Keep the first N when
   the order has N.
7. Save the screen result, its rows, and its excluded list in one
   transaction.

`screen` needs these parts from `market_data` (`market_data.md`):

| Need | Rule |
|---|---|
| Daily bar summary | 1 row for each instrument: the last daily bar date, the last close, the average trading value of the last 20 daily bars, and the trading status. The daily bar save updates it. Its average trading value (20) must be the value of the class `average_trading_value` (section 23.2) for the same bars (ADR 0001). The table belongs to `market_data`, because the bar save updates it. |
| Daily bars of many instruments | One read of the last n daily bars before a date, for a list of instruments, merged in the global source order. |
| Daily bar update | The `web` daily bar update after each trading day: the US universe of the current quarter, the HK instrument list, and the watchlist, from IBKR into `ibkr_bar`, with the daily bar summary (#145 Q4). When IB Gateway is not reachable, the update does not run. The screen page shows the date of the last daily bar. |
| HK instrument list | The list of section 24.2. |
| Universe of a quarter | The top 500 US instruments of a quarter (#141). |
| Instrument name | The "Name" column of the result table (section 24.10). |

Decided (#206):

- Code: `screen/screen_run.py` (`run_screen_steps`, the 2 steps without a
  database), `screen/screen_running.py` (`run_saved_screen`: the start
  instruments, the reads, and the save), and the store functions of
  `screen/screen_store.py`. Tests: `tests/screen/test_screen_run.py` and
  `tests/screen/test_screen_run_routes.py`.
- The start instruments come from these reads of `market_data` and
  `watchlist`: `read_us_universe_members` with the quarter of the first
  trading day of the run date (`quarter_universe`),
  `read_daily_bar_summaries_of_currency` with `USD`
  (`all_with_daily_bars`), `read_hk_instrument_list`
  (`hk_instrument_list`), and `read_watchlist_instruments` with only the
  instruments in the currency of the market (`USD` or `HKD`).
- The daily bar summary has no trading status (`market_data.md` section
  8.14). "Still trading" is a rule of `screen`: the last daily bar of the
  instrument is at most 7 calendar days older than the daily bars date of
  the run. The daily bars date is the date of the newest last daily bar of
  the start instruments.
- A start instrument without a summary row is excluded with the reason
  "No daily bars". A filter on the average trading value (20) of an
  instrument with fewer than 20 daily bars gives "No value: Avg trading
  value (20)".
- Step 2 reads the daily bars before the day after the daily bars date
  with one `read_last_daily_bars` call. Its `bar_count` is the longest
  look-back of the indicators (section 23.4). Each indicator gets only its
  own look-back bars, the last bars of the read.
- An instrument with "no value" for an indicator of a condition or of the
  order gets the reason "No value: <indicator>" with the first such
  indicator. The other excluded instruments get the reason of the first
  condition that is not true, in the form "<location>: <condition>", for
  example "filters[1]: Close > 5", "indicator_conditions[0]: RSI(14) < 30",
  "indicator_conditions[1]: Close above SMA(200)", or
  "indicator_conditions[2]: 12-1 momentum(252, 21) top 20%".
- The percentile of a rank condition is 100 × the share of the values that
  are lower or equal. "Top N" keeps a percentile above 100 − N. "Bottom N"
  keeps the instruments whose share of lower values is below N percent.
  Equal values get the same percentile and the same answer.
- The sort uses the order indicator, then the symbol. When more than 500
  instruments pass, the result keeps the first 500 of the order.
  `after_indicator_conditions_count` counts all passing instruments.
- A run saves the full excluded list, also for a run with all US
  instruments.
- `market_data` has no instrument name (`market_data.md` has no name
  source), so the result has no "Name" column yet. The name source needs a
  decision of the user.

## 24.6 Checks

Source: [How the AI assistant uses screens](https://github.com/Mano-Liaoyan/ATrade/issues/150) B5.

The create, change, and run routes check the screen. When a check fails,
the route returns `422` with a list of problems, in the same form as the
strategy code check ([`strategy.md`](strategy.md) section 9.3). Each problem
gives the location of the condition and the reason. The checks:

- The start instruments belong to the market of the screen.
- Each indicator is in the catalog of section 23.3, and each output belongs
  to the indicator.
- Each parameter is in its allowed range.
- The percent of a rank condition is from 1 to 100.
- Each operator and each field is known.
- The name is 1 to 100 characters.

Decided (#205): the check is `check_screen` in `screen/screen_check.py`. The
`422` body is `{"problems": [{"location", "message"}]}`. `location` is the
path in the request body, a list of keys and list indexes, for example
`["definition", "indicator_conditions", 0, "indicator", "parameters", "period"]`.
The indicator problems of section 23.6 get the location of their condition
before their own location. A name that another screen has gives the
problem `["name"]` with the reason "A screen with the name '<name>' exists.".
The market is a problem `["market"]` when it is not `US` or `HK`.

## 24.7 HTTP routes

Source: [How the AI assistant uses screens](https://github.com/Mano-Liaoyan/ATrade/issues/150) A8 and B3.
Decided (#205): the paths and the field names of this table are final.
`screen/http_routes.py` has the first 5 routes.

| Route | Behavior |
|---|---|
| `GET /api/screens` | `200` with `[{"id", "name", "market", "kept", "updated_at_utc"}]`, the last changed screen first. |
| `GET /api/screens/{screen_id}` | `200` with the screen (`id`, `name`, `market`, `definition`, `kept`, `assistant_conversation_id`, `created_at_utc`, `updated_at_utc`) and `recent_screen_results`: the last 10 screen results (`id`, `run_at_utc`, `result_count`), the last run first. `404` when the screen does not exist. |
| `POST /api/screens` | Body `{"name", "market", "definition"}`. `201` with the screen, as `GET /api/screens/{screen_id}` gives it. A screen of the user has `kept` true and `assistant_conversation_id` null. `422` with the problem list (section 24.6). |
| `PUT /api/screens/{screen_id}` | Body `{"name", "definition"}`. `200` with the screen. `422` with the problem list. `404` when the screen does not exist. On the AI assistant port, `403` for each screen that section 24.8 does not allow. |
| `DELETE /api/screens/{screen_id}` | `204`. Also deletes the screen results of the screen. `404` when the screen does not exist. Not on the AI assistant port. |
| `POST /api/screens/{screen_id}/runs` | Runs the saved screen. `201` with the screen result (as `GET /api/screen-results/{id}` gives it). `422` with the problem list. `404` when the screen does not exist. |
| `GET /api/screen-results/{screen_result_id}?offset=&limit=` | `200` with the summary and one page of rows. Default `limit` 50. `404` when the screen result does not exist. |

The screen result answer:

- `summary`: `row_count`, the 4 funnel counts, the count of each exclusion
  reason, `daily_bars_date`, `run_at_utc`, `run_seconds`.
- `definition`: the copy of the screen.
- `rows`: each row has all columns of the result table (section 24.10).
- `exclusions`: the excluded instruments with their reasons.

Decided (#206): the screen result answer is
`{"id", "screen_id", "market", "assistant_conversation_id", "summary", "definition", "rows", "exclusions"}`.

- `summary`: `row_count` (all rows, also the rows that are not on the
  page), `start_count`, `after_filters_count`,
  `after_indicator_conditions_count`, `result_count`, `exclusion_counts`
  (`[{"reason", "count"}]`, the most frequent reason first),
  `daily_bars_date` (null when no start instrument has daily bars),
  `run_at_utc`, and `run_seconds`.
- Each row: `position`, `symbol`, `exchange`, `currency`, `last_price`
  (decimal string), `average_trading_value_20` (null with fewer than 20
  daily bars), `indicator_values` (the value of each indicator of a
  condition or of the order by its name, for example `{"RSI(14)": 28.4}`),
  and `percentiles` (the percentile of each rank condition by the name of
  its indicator).
- `exclusions`: all excluded instruments (`symbol`, `exchange`,
  `currency`, `reason`), by symbol. The route does not page them.
- `offset` is 0 or more. `limit` is 1 to 500, default 50.
- A run of the user has `assistant_conversation_id` null.

Decided (#207): the screen result answer also has `indicator_names`:
`{"indicator_conditions": ["RSI(14)", ...], "order": "Momentum(252, 21)"}`.
It has one UI name for each indicator condition, in the order of the
definition, and the name of the order indicator. These names are the keys of
`indicator_values` and `percentiles`. The condition bar and the result table
use them, so the frontend has no copy of the indicator catalog.

## 24.8 AI assistant access

Source: [How the AI assistant uses screens](https://github.com/Mano-Liaoyan/ATrade/issues/150).
The AI assistant section of the specification has the port, the tool calls, and the condition
card. This section gives only what the screen routes must allow.

| Tool | Route on the AI assistant port | Rule |
|---|---|---|
| `list_screens` | `GET /api/screens` | |
| `read_screen` | `GET /api/screens/{id}` | |
| `create_screen` | `POST /api/screens` | Records the conversation ID. `kept` is false. |
| `update_screen` | `PUT /api/screens/{id}` | Only for a screen that the AI assistant made in the same conversation and that the user has not kept. Else `403`. |
| `run_screen` | `POST /api/screens/{id}/runs` | Records the conversation ID on the screen result. |
| `read_screen_result` | `GET /api/screen-results/{id}` | Default: the summary and the first 50 rows. The AI assistant can read more pages. |
| `run_backtest` | `POST /api/backtests` with the universe fields | Section 24.9. |

- The AI assistant never overwrites a screen that the user saved. To change
  one, it saves a new screen.
- The name of a new screen of the AI assistant is the old name with
  " (AI)". When that name is in use, it adds a number, for example
  "Momentum leaders (AI 2)". The user can rename it.
- Keep: the screen stays, and `kept` becomes true.
- Discard: deletes the screen that the AI assistant made. Old backtests keep
  their copy of the screen.
- When the user selects neither Keep nor Discard, the screen stays.
- Not on the AI assistant port: `DELETE /api/screens/{id}`, watchlist
  changes (also "Add to watchlist"), HK instrument list changes, the daily
  bar update, and parameter sweeps.
- The AI assistant discusses screens only in the AI assistant side column
  of the strategy page. The screen page has no AI assistant.

## 24.9 Screens as a backtest universe

Source: [Screen page prototype](https://github.com/Mano-Liaoyan/ATrade/issues/145) Q5,
[How the AI assistant uses screens](https://github.com/Mano-Liaoyan/ATrade/issues/150) A5 and A6.
[`backtest.md`](backtest.md) has the backtest form, the tables, and the run.

The "Instruments" field of the backtest form has the source "Screen", with 2
kinds:

| Kind | `universe_kind` | Input | Rule |
|---|---|---|---|
| Point-in-time (default) | `screen` | A screen ID and the rebalance period: each quarter (default) or each month | At each rebalance, the platform runs the screen again on the daily bars that close at or before that date. The result is the new universe. The backtest saves a copy of the screen. |
| Fixed list | `list` | A screen result ID, optionally only selected instruments | The instruments stay the same for the full range. The UI shows the survivorship bias warning, as for the watchlist. |

- A point-in-time run uses the rules of sections 23.1 and 24.5 with a date.
  It uses only bars that close at or before the rebalance. Its filter
  values must equal the values that the daily bar summary had at that date.
- For a fixed list from the AI assistant, the tool result has the
  survivorship bias warning. The AI assistant must write the warning in its
  answer.
- One multi-instrument backtest counts as 1 backtest of the 5 backtests
  that one user message can start. `run_backtest` waits at most 15 minutes
  ([#140](https://github.com/Mano-Liaoyan/ATrade/issues/140)).

## 24.10 Screen page

Source: [Screen page prototype](https://github.com/Mano-Liaoyan/ATrade/issues/145).

The first frontend rule of `AGENTS.md` applies first: no unnecessary
secondary labels and descriptions. A heading is a name only. The page has no
help sentence, no step labels (for example "1 Filters"), and no count label
that the user does not need to act.

Page addresses:

- `/screens/<id>` is the screen page. It is a workbench.
- `/screens` opens the screen that the user opened last.
- The header gets the page link "Screens".

Layout:

- Side column "Screens" at the start side:
  - Each row has the name and the market.
  - The current screen expands to its recent runs (time, instrument count).
  - The user can drag its width and minimize it
    ([#140](https://github.com/Mano-Liaoyan/ATrade/issues/140)).
- Main region, from top to bottom:
  1. Title row: the name, the US / HK `ContentSwitcher`, "Save as new
     screen", and "Save screen" (only when the screen has unsaved changes).
  2. Condition bar (section 24.10.1).
  3. Table toolbar: the "Result N" / "Excluded N" switch, the daily bar date
     and the run time, "Add to watchlist", and "Run backtest on this screen
     result". When the user selects rows, the toolbar changes to the batch
     actions "Add to watchlist" and "Run backtest on selected".
  4. Result table, or the excluded table.
- The HK survivorship bias warning (section 24.2) is a Carbon warning
  notification: an icon, the text, and the warning color.

Behavior:

- A change of a condition runs the screen again at once.
- A change overwrites the saved screen only after "Save screen".

### 24.10.1 Condition bar

- 4 groups in a fixed order: start instruments › filters › indicator
  conditions and "Add condition" › order.
- Each group is on a rounded strip with the color `$background`. A chevron
  icon separates 2 groups. There are no step labels.
- The end of each group shows the count of instruments that remain after
  that group (the funnel count). The count of the last group is bold.
- Each condition is a tag. A click opens its edit popover. The × button
  deletes it.
- The text of a tag has 3 parts in 3 colors:

  | Part | Example | Color |
  |---|---|---|
  | Subject (indicator or field) | `RSI(14)` | `$text-primary` |
  | Operation | `≥`, `top`, `above` | `$text-helper` |
  | Value | `30` | `$link-primary` (decided #207, see section 24.13) |

- When there are many conditions, the bar has 2 or 3 lines.
- Filters and indicator conditions are told apart by their order and the
  group strips, not by color.

### 24.10.2 Result table

- Default columns: #, Symbol, Name, Exchange, Close, Avg trading value
  (20).
- Each indicator of a condition or of the order adds one column. Each rank
  condition adds a "Percentile" column.
- Number columns are right-aligned with tabular numbers.
- The user can sort the columns.
- The excluded table lists each excluded instrument and its reason: the
  condition, or "No value: <indicator>".
- The table scrolls in its own `ScrollRegion` with a visible scroll track
  (`AGENTS.md` guardrail).

## 24.11 Module

- Path: `backend/src/atrade/screen/`. One public entry file.
- Imports: `indicator`, `market_data`, `watchlist`, `foundation`.
- `backtest` imports `screen` for the point-in-time runs of section 24.9.
- HTTP routes: `screen/http_routes.py` with `create_screen_router(...)`.
- Frontend: `frontend/src/lib/screen/` has the HTTP client and the screen
  page parts. `src/routes/screens/[[screenId]]/` is the page.

## 24.12 Phase

| Part | Phase of map #129 |
|---|---|
| Daily bar summary, daily bar update, HK instrument list (`market_data.md`) | Phase 3 |
| `screen` module, tables, routes, screen page | Phase 3 |
| Screen as a backtest universe (section 24.9) | Phase 3, with the multi-instrument backtest |
| AI assistant screen tools (section 24.8) | After phase 2 and the `screen` module of phase 3 |

## 24.13 Left to the implementation

- Decided (#205): the final route paths and the field names (section
  24.7).
- Decided (#205): the form of the problem location in the `422` list
  (section 24.6).
- The route for Keep. Discard can use `DELETE /api/screens/{id}` on the Web
  port.
- How a run of a screen with unsaved changes works: the run route takes a
  saved screen only.
- How the user runs a screen again after new daily bars. The final title row
  of #145 has no "Run screen" button.
- Decided (#206): what the result does when more than 500 instruments
  pass (section 24.5).
- Decided (#206): the rank method for ties in a percentile (section 24.5).
- Decided (#205): the operators of a comparison are `<`, `<=`, `>`, and
  `>=` (section 24.4.1).
- The default order of a new screen.
- Decided (#207): `/screens` stores the id of the last opened screen in the
  browser storage (key `atrade.screen-page.last-screen`). The choice belongs
  to the browser. Without a stored id, or when that screen does not exist,
  `/screens` opens the first screen of the list.
- Decided (#207): the side column shows the recent runs of
  `GET /api/screens/{id}` (the last 10). `?result=<id>` opens one run.
  Without it, the page opens the last run.
- Decided (#207): the tag value color is `$link-primary`: blue 60 in g10 and
  blue 40 in g100. Blue 70 (`#0043ce`) is not a Carbon token and has no g100
  value.
- Decided (#207): the result table has no "Name" column yet. The result rows
  have no instrument name, and no source for the name is decided (#206).
- Decided (#205): a delete of a screen deletes its screen results (section
  24.4).
- Decided (#205): `GET /api/screens/{id}` shows the last 10 runs. The side
  column is left to the screen page.
- Decided (#206): `screen` saves the full excluded list of a run with all
  US instruments (section 24.5).
- Decided (#206): `screen` sets "Still trading" from `last_day_start_utc`
  of the daily bar summary (section 24.5). Decided (#195): `market_data`
  stores no status ([`market_data.md`](market_data.md) section 8.14).
- How the point-in-time run of a backtest uses the source order: the global
  source order or the source order of the backtest.
- The survivorship bias warning of a point-in-time backtest whose screen
  starts from the watchlist or the HK instrument list.
- Decided (#207): "Add to watchlist" adds many instruments with one
  `POST /api/watchlist` for each instrument, one after the other. The route
  checks each instrument with IBKR ([`market_data.md`](market_data.md)
  section 8.3), so 500 instruments take about 500 seconds. The page then
  shows how many instruments it added, and the last refusal (for example an
  instrument that is in the watchlist already). Without selected rows, it
  adds all rows of the screen result.
- The Carbon token for blue 70 in the g100 theme (Dark).
- How the API reports the AI assistant caller and the conversation ID to the
  screen routes (the AI assistant section).
