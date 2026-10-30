# Market data and watchlist

This document is section 8 of the architecture specification
([`docs/architecture.md`](../architecture.md)). It was moved to its own file
to keep the specification shorter than 1000 lines (section 18). Terms have
the meaning that [`GLOSSARY.md`](../../GLOSSARY.md) gives them.

## 8.1 Decisions

- `market_data` reads bars from IBKR with `ib_async` and saves them in
  PostgreSQL.
- `market_data` requests only the time ranges that are not in PostgreSQL. This
  keeps ATrade below the IBKR historical data rate limit.
- Backtests read bars only from PostgreSQL.
- The bar table key is the instrument, the bar period, and the bar start time.
- Start with no partitions, no BRIN index, and no compression. Add native
  PostgreSQL range partitions only when a measurement shows the need.
- Data is always called a bar. "Candlestick" means only the chart drawing
  (`CandlestickSeries` in `lightweight-charts`).
- `watchlist` stores the instruments that the user saves. It uses
  `market_data` to find instruments.
- Phase 3: each bar source has its own bar table and its own saved-range
  table. The bar sources are `ibkr` and `databento`. ATrade reads bars through
  a source order (section 8.7,
  [ADR 0002](../adr/0002-one-bar-table-per-bar-source.md)).
- Phase 3: US bars before the IBKR bars come from a one-time Databento
  purchase (section 8.8). Hong Kong bars come only from IBKR (section 8.10).
- Phase 3: all stored bars have the IBKR `TRADES` form: adjusted for stock
  splits, not adjusted for dividends. At a stock split, ATrade changes the
  stored bars of all bar sources in place (section 8.13).

## 8.2 Instrument search

Source: [Instrument search](https://github.com/Mano-Liaoyan/ATrade/issues/64).

- `foundation/instrument.py` has `Instrument`: `symbol`, `exchange`, and
  `currency`.
- `GatewayConnection.search_instruments(query)` in `ibkr` calls
  `reqMatchingSymbols`. It keeps only stocks (`secType` `STK`), in the IBKR
  order, without duplicates. The exchange is the primary exchange of the
  contract. A missing connection, a timeout (4 seconds in `ib_async`), or an
  IBKR API error raises `GatewayRequestError`.
- IBKR allows about 1 `reqMatchingSymbols` request per second. The UI sends
  one request for each form submit, not for each key press.
- `market_data` exports `create_market_data_router(gateway_connection, host,
  port)`. The route calls IBKR only through the `ibkr` public entry.

| Route | Behavior |
|---|---|
| `GET /api/market-data/instrument-search?query=<text>` | `200` with `{"instruments": [{"symbol", "exchange", "currency"}, ...]}`. The list can be empty. The backend removes spaces at the start and the end of `query`. |
| | `422` when `query` is empty, has only spaces, or is longer than 32 characters. |
| | `503` with `{"detail": "IB Gateway is not reachable at <host>:<port>. Instrument search needs IB Gateway."}` when the Web process is not connected. |
| | `502` with `{"detail": "The instrument search failed: <reason>"}` when IB Gateway does not answer or answers with an error. |

- The frontend panel is `InstrumentSearch` in `lib/market_data/`. The home
  page (`src/routes/+page.svelte`) shows it. It is a Carbon combo box
  (`Combobox` of `foundation/carbon`). The search starts 500 ms after the
  user stops typing, because IBKR allows about 1 symbol search per second.
  There is no Search button. Each result is a candidate written as
  `symbol / exchange / currency`, for example `700 / SEHK / HKD`. ArrowUp
  and ArrowDown choose a candidate, Enter confirms it, and Escape closes the
  list. On `502` or `503`, the combo box shows the `detail` text of the
  backend as its error message.
- The candidate list is in a `ScrollRegion` (section 13), so a long list has a
  visible scroll track in all browsers.
- The IBKR fake (`tests/fakes/ibkr.py`) finds instruments whose symbol starts
  with the query, without regard to letter case. Its default list has
  `700 / SEHK / HKD`, `9988 / SEHK / HKD`, and 21 NASDAQ symbols that start
  with `A`. Tests can set `instruments` and `search_error_message`.
- The contract test (`docs/architecture/ibkr.md` section 7.5) asserts that a
  search for `AAPL` finds `AAPL / NASDAQ / USD`, that a search for `700`
  finds `700 / SEHK / HKD`, and that a search without a connection raises
  `GatewayRequestError`.

## 8.3 Watchlist

Source: [Watchlist](https://github.com/Mano-Liaoyan/ATrade/issues/67).

- The table `watchlist_instrument` belongs to `watchlist`. Columns: `id`,
  `symbol`, `exchange`, `currency`, `added_at_utc`. One instrument
  (`symbol`, `exchange`, `currency`) is in the watchlist at most once. The
  migration is `04f7d8d54c2b_watchlist_create_table.py`.
- `market_data` exports `InstrumentLookup(gateway_connection, host, port)`.
  `find_instrument(instrument)` searches IBKR for the symbol and returns the
  instrument only when the symbol, the exchange, and the currency are the
  same. It raises `GatewayNotReachableError` or `InstrumentLookupFailedError`
  (both are `InstrumentLookupError`).
- `watchlist` exports `create_watchlist_router(database_url, clock,
  instrument_lookup)`. `watchlist` imports `market_data` and `foundation`
  only. An import-linter contract forbids a direct import of `ibkr`.
- `market_data` exports `read_saved_bar_coverage(database_url, instruments)`
  (one query; for each instrument a list of `SavedBarCoverage`: bar period,
  first and last bar start) and
  `has_saved_bars(database_url, bar_request)`. Both read PostgreSQL only.
  The watchlist routes add `saved_bars` to each instrument with the first.
  The backtest start route uses the second (`docs/architecture/backtest.md`
  section 10.1).
- Phase 3 (#188): `SavedBarCoverage` also has the bar source.
  `read_saved_bar_coverage` reads the bar tables of all bar sources, and
  orders the items of one bar period by the global source order.
  `has_saved_bars(database_url, bar_request, source_order)` is true when
  `read_saved_bars` with the same source order returns at least one bar.
- Before it saves an instrument, the add route checks it with
  `InstrumentLookup`. Thus the watchlist holds only instruments that IBKR
  knows. Listing and deleting do not need IB Gateway.

| Route | Behavior |
|---|---|
| `GET /api/watchlist` | `200` with `{"instruments": [{"id", "symbol", "exchange", "currency", "added_at_utc", "saved_bars"}, ...]}` in the order of adding. |
| | `saved_bars` is `[{"bar_source", "bar_period", "first_start_utc", "last_start_utc"}, ...]`: one item for each bar source and bar period with saved bars, in the order of the bar periods, then in the global source order. |
| `POST /api/watchlist` with `{"symbol", "exchange", "currency"}` | `201` with the new watchlist instrument. |
| | `404` with `{"detail": "IBKR has no instrument <symbol> / <exchange> / <currency>. Add an instrument from the instrument search."}`. |
| | `409` with `{"detail": "This instrument is already in the watchlist."}`. |
| | `422` when a field is empty or too long (symbol 32, exchange 32, currency 8 characters). |
| | `503` with `{"detail": "IB Gateway is not reachable at <host>:<port>. The instrument check needs IB Gateway."}`. |
| | `502` with `{"detail": "The instrument check failed: <reason>"}`. |
| `DELETE /api/watchlist/{id}` | `204`. `404` with `{"detail": "This instrument is not in the watchlist."}` when the ID is not in the watchlist. |

- Frontend: `#lib/watchlist` has the HTTP client. The watchlist column of
  the workbench pages is `src/routes/InstrumentWatchlist.svelte`: a Carbon
  `sm` data table in a `ScrollRegion` named `Watchlist table`. A capability
  does not import another capability, so the route file combines them.
- On the home page the column is `editable`. The `InstrumentSearch` above
  the table (a 32px combo box with the label "Symbol" for screen readers only)
  adds a confirmed candidate (`onSelect`) to the watchlist. The column gives a
  `marker`: a candidate that is in the watchlist has an "In watchlist" tag and
  cannot be chosen. Each row has a Delete icon button named
  "Delete <instrument> from the watchlist".
- Each watchlist instrument is a link to
  `/instruments/<exchange>/<symbol>?currency=<currency>`. This page shows
  the bar chart (section 8.4).

## 8.4 Bars and the bar chart

Source: [Bars and the bar chart](https://github.com/Mano-Liaoyan/ATrade/issues/65).

- `foundation/bar.py` has `Bar` (`start_utc`, `open`, `high`, `low`,
  `close`, `volume`, all prices and the volume as `Decimal`), `BarPeriod`,
  and `TimeRange` (start included, end not included). The `BarPeriod`
  values use the NautilusTrader bar specification format: `1-MINUTE`,
  `5-MINUTE`, `15-MINUTE`, `30-MINUTE`, `1-HOUR`, `1-DAY`. Bar periods
  start at the UNIX epoch in UTC. A daily bar starts at 00:00 UTC of its
  trading date.
- Tables (migration `5b2d8e7f4a61`). Phase 3 renames `bar` to `ibkr_bar`
  and `bar_saved_range` to `ibkr_bar_saved_range` (section 8.7.1):
  - `bar`: primary key `(symbol, exchange, currency, bar_period,
    start_utc)`, `numeric` prices and volume. No partitions, no BRIN index,
    no compression.
  - `bar_saved_range`: the time ranges that ATrade read from IBKR for one
    instrument and bar period. A saved range can have no bars, for example a
    weekend or a holiday. The store joins ranges that overlap or touch, so
    the table stays small.
- The bars route widens the requested range to whole bar periods. It cuts
  the range at the start of the current bar, because a bar that is not
  complete changes later. It reads the saved ranges, asks IBKR only for the
  missing parts, saves the bars and the range in one transaction for each
  missing part, and then reads the bars from PostgreSQL. One lock for each
  instrument and bar period in the Web process lets only one fill of that
  instrument and bar period run at a time. Fills of other instruments do not
  wait. The store saves all bars of a range with one SQL statement.
- When no part is missing, the route does not call IBKR. Saved bars are
  returned also when IB Gateway is not reachable.
- Phase 3 (#188): the route reads through the global source order (section
  8.7.2). A part is missing only when no bar source in the source order saved
  it. The route asks IBKR for the missing parts and saves them in `ibkr_bar`.
- The public entry exports `read_saved_bars(*, database_url, bar_request,
  source_order)` with `BarRequest(instrument, bar_period, time_range)`. It
  reads only the bars in PostgreSQL and never calls IBKR. It returns
  `SavedBars(bars, bar_counts)`: the merged bars, oldest first, and the bar
  count of each bar source in the source order. Backtests use it (section
  10) with the global source order from `read_source_order(database_url)`.
- The public entry exports `save_received_bars(*, database_url, bar_request,
  bars)` (async) and `save_received_bars_blocking(...)` (the same, for
  synchronous callers). They save complete bars that a caller received from
  IBKR for `bar_request.time_range` in `ibkr_bar`, and record that range as
  saved in `ibkr_bar_saved_range`, in one transaction. They use the same SQL as the bars route. A bar that is
  already saved gets the new values, so a second save adds no row. A forward
  test uses them for its warm-up bars and its live bars
  (`docs/architecture/forward_test.md` sections 12.8 and 12.15).
- `GatewayConnection.read_historical_bars(instrument, bar_period,
  time_range)` in `ibkr` calls `reqHistoricalData` with `TRADES`, regular
  trading hours only (`useRTH`), `formatDate=2` (UTC), and the contract
  `STK`, `SMART`, primary exchange, currency.
  - Paging (`ibkr/historical_bars.py`): the range is split, newest first,
    into requests of at most the IBKR step size of the bar period: 1 day
    (1 minute), 7 days (5 minutes), 14 days (15 minutes), 28 days (30
    minutes and 1 hour), 364 days (1 day). The duration is in whole days
    (`"<n> D"`). Bars outside each request range are dropped. The requests
    are 0.5 seconds apart, because IBKR refuses 6 or more requests for the
    same contract in 2 seconds.
  - `ib.RaiseRequestErrors` is on, so an API error is not read as "no
    bars". Error 162 "query returned no data" is an empty list. A timeout
    (60 seconds) or another error raises `GatewayRequestError`. A failed
    part is not saved, so the next request asks IBKR again.

| Route | Behavior |
|---|---|
| `GET /api/market-data/bars?symbol=&exchange=&currency=&bar_period=&start_utc=&end_utc=` | `200` with `{"bars": [{"time", "open", "high", "low", "close", "volume"}, ...]}`, oldest first. `time` is the bar start in UNIX seconds. |
| | Without `end_utc`, the range ends now (the clock of `foundation`). Without `start_utc`, it starts a default length before the end: 3 days (1 minute), 10 days (5 minutes), 30 days (15 minutes), 60 days (30 minutes), 90 days (1 hour), 1096 days (1 day). |
| | `422` when a time has no time zone, the bar period is unknown, the start is not before the end, or the range has more than 20000 bars. |
| | `503` with `{"detail": "IB Gateway is not reachable at <host>:<port>. Bars that are not saved need IB Gateway."}` when a part is missing and the Web process is not connected. |
| | `502` with `{"detail": "Reading bars from IB Gateway failed: <reason>"}` when IB Gateway answers with an error or does not answer. |

- Frontend: `#lib/market_data` has `readBars`, `readChartRequest`,
  `formatChartSearch`, `BAR_PERIODS`, and the `BarChart` component.
  `BarChart` uses `createChart` and `addSeries(CandlestickSeries)` of
  `lightweight-charts` 5.2.1 with `autoSize`. The times are UNIX timestamps.
- The instrument page `/instruments/<exchange>/<symbol>?currency=<currency>&bar_period=<bar period>`
  shows the chart. Without `bar_period`, it shows daily bars. The bar period
  list changes `bar_period` in the page address. The page shows the bar
  count (`role="status"`, name `Bar count`) or the `detail` text of the
  backend.
- TradingView attribution: the chart shows the TradingView logo link
  (`attributionLogo`), the text under the chart links to
  `https://www.tradingview.com/`, and `BarChart.svelte` holds the
  attribution notice.
- The IBKR fake returns one sample bar for each bar period in the range
  (its market never closes) and records each call in
  `historical_bar_requests`. Tests set `historical_bars_error_message`.
- Tests: `tests/market_data/test_bars_route.py` (HTTP, assert the ranges
  that the fake receives), `tests/ibkr/test_historical_bar_pages.py`
  (internal paging test, the allowed exception of section 17), the contract
  test (section 7.5), and `e2e/bar_chart.spec.ts`.
- Live bars: section 8.5.

## 8.5 Live bars

Source: [Live bars on the chart](https://github.com/Mano-Liaoyan/ATrade/issues/66).

- `GatewayConnection.stream_live_bars(instrument, bar_period)` in `ibkr` is
  an async generator. It yields the current bar at once and after each IBKR
  update. The real connection calls `reqHistoricalData` with `keepUpToDate`,
  an empty end time, `TRADES`, regular trading hours only, `formatDate=2`, and
  a duration of `2 D` (intraday) or `1 W` (daily). It uses only the last bar
  of the list. IBKR sends an update about every 5 seconds. Updates that come
  at the same time are one update.
- The generator raises `GatewayRequestError` when the request fails or when
  the connection is lost (checked each second while no update comes). When
  the generator closes, it cancels the IBKR subscription
  (`cancelHistoricalData`). Use `contextlib.aclosing`.
- The live bars of `/ws/market-data` are not saved in PostgreSQL. The bars
  route saves only complete bars (section 8.4). A forward test saves each
  complete bar that its LiveNode receives (`docs/architecture/forward_test.md`
  section 12.8).

| `/ws/market-data?symbol=&exchange=&currency=&bar_period=` message | When |
|---|---|
| `{"type": "bar", "bar": {"time", "open", "high", "low", "close", "volume"}}` | At once after the IBKR subscription starts, and after each update. The `bar` fields are the fields of the bars route. A bar with the time of the last bar replaces it. A later time adds a bar. |
| `{"type": "heartbeat"}` | After 10 seconds without another message. |
| `{"type": "error", "detail": "IB Gateway is not reachable at <host>:<port>. Live bars need IB Gateway."}` | When the Web process is not connected. The server then closes the socket with code 1011. |
| `{"type": "error", "detail": "Reading live bars from IB Gateway failed: <reason>"}` | When the subscription fails or the connection is lost. The server then closes the socket with code 1011. |

- The server refuses an unknown bar period or an empty or too long instrument
  field before it accepts the socket (code 1008).
- The browser sends nothing. When the browser leaves, the server closes the
  generator, so the IBKR subscription ends.
- The route is in `market_data/live_bar_socket.py`.
  `create_market_data_router` includes it. `market_data` exports the message
  models in `MARKET_DATA_SOCKET_MESSAGE_MODELS`; `app/openapi_document.py`
  adds their JSON Schema to the OpenAPI document (section 13), so the
  frontend types `LiveBarMessage`, `LiveBarErrorMessage`, and
  `HeartbeatMessage` come from `#lib/api`.
- Frontend: the instrument page opens the socket with
  `foundation/live_socket` and gives the live bar to `BarChart` (prop
  `liveBar`). `BarChart` calls `series.update()`: the view does not fit
  again. A live bar older than the last bar is not drawn. The page shows the
  live bar (`role="status"`, name `Live bar`), for example
  `Live bar 2026-01-02 03:00 UTC: close 123.25`, or the `detail` text of the
  error message. After an error, `live_socket` connects again with its
  delay, so the chart continues when IB Gateway comes back.
- The IBKR fake updates the bar that contains `live_bar_now_utc`
  (2026-01-02 03:04:05 UTC, the time of the test clocks) every
  `live_bar_interval_seconds` (0.2): the close moves up 0.25 from the open
  to the open + 1.75 and starts again, and the volume grows by 10. It records
  `live_bar_subscriptions` and `active_live_bar_stream_count`. Tests set
  `live_bars_error_message`.
- Tests: `tests/market_data/test_live_bar_socket.py` (through the WebSocket
  route with the fake), the contract test (section 7.5), the Vitest tests of
  `live_socket` and `live_bars`, and the last test of `e2e/bar_chart.spec.ts`.

## 8.6 Daily exchange rates

Source: [Backtests of instruments that are not in USD](https://github.com/Mano-Liaoyan/ATrade/issues/80).
A backtest of an instrument that is not in USD converts its results with
these rates ([`backtest.md`](backtest.md) section 10.8).

- Tables (migration `6c3e9a1f2b80`):
  - `exchange_rate`: primary key `(currency, day_start_utc)`,
    `usd_per_unit` (`numeric`, above 0): the USD for 1 currency unit at the
    close of the day.
  - `exchange_rate_saved_range`: the time ranges that ATrade read from IBKR
    for one currency. A range can have no rates, for example a weekend. The
    store joins ranges that overlap or touch, as for `bar_saved_range`.
- `ExchangeRateReader(*, database_url, clock, gateway_connection)` of the
  public entry has `save_daily_rates(currency, time_range)`. It widens the
  range to whole days and cuts it at the start of yesterday
  (`PUBLICATION_DELAY`): the rate of a day is complete only at its close,
  and IBKR can publish it some hours later. A day without a rate in a saved
  range is not read again, so the delay keeps a late rate from a permanent
  gap. It reads the saved
  ranges, asks IBKR (`read_daily_exchange_rates(currency, "USD", ...)`,
  [`ibkr.md`](ibkr.md) section 7.2) only for the missing parts, and saves
  the rates and the range in one transaction for each part. One lock for
  each currency lets only one fill of that currency run at a time. Without
  a connection, or when IBKR does not answer, it raises
  `ExchangeRatesNotReadError` with the reason for the user. Saved rates need
  no IB Gateway.
- `read_saved_exchange_rates(*, database_url, currency, time_range)` of the
  public entry returns the saved rates of the days that start in the range
  (`SavedExchangeRate`: `day_start_utc`, `usd_per_unit`), oldest first. It
  never calls IBKR. The backtest child uses it.
- The Web app makes one `ExchangeRateReader` and gives it to
  `create_backtest_router`. This stage has no HTTP route for the rates.
- Tests: `tests/backtest/test_backtest_exchange_rates.py` (through
  `POST /api/backtests` with the IBKR fake).

## 8.7 Bar sources and the source order

Phase 3. Source: [Screen data source decision](https://github.com/Mano-Liaoyan/ATrade/issues/141).
Decision record: [ADR 0002](../adr/0002-one-bar-table-per-bar-source.md).

- A bar source is a value of the enum `BarSource`: `ibkr` and `databento`.
- Each bar source has its own bar table and its own saved-range table. Bars
  of 2 bar sources are never in the same table.
- A new bar source needs a new `BarSource` value, a new bar table, and a new
  saved-range table.
- The precedence of the bar sources is not in the code. The source order
  sets it.
- Code (#188): `market_data/bar_source.py` (`BarSource`, the source order
  store), `market_data/source_order_routes.py`, and the merge rule in
  `market_data/bar_reading.py`. Tests: `tests/market_data/test_bar_sources.py`.

### 8.7.1 Tables

| Table | Columns | Written by |
|---|---|---|
| `ibkr_bar` | The columns and the primary key of `bar` (section 8.4). | The bars route, `save_received_bars`, the daily bar update (section 8.11), the bar fetcher (section 8.12). |
| `ibkr_bar_saved_range` | The columns of `bar_saved_range` (section 8.4). | The same writers, when they read a range from IBKR. |
| `databento_bar` | The columns and the primary key of `ibkr_bar`. | The Databento import (section 8.8) and the quarterly universe update (section 8.9). |
| `databento_bar_saved_range` | The columns of `ibkr_bar_saved_range`. | The Databento import writes the time range that it bought for each instrument and bar period. |
| `source_order` | 1 row: `bar_sources` (ordered list of `BarSource` values), `changed_at_utc`. | `PUT /api/market-data/source-order`. |

- One migration (`b7e3c9a4d158`) renames `bar` to `ibkr_bar` and
  `bar_saved_range` to `ibkr_bar_saved_range`. The data does not change. All
  SQL that uses the old names changes in the same PR.
- The default source order is `ibkr`, then `databento`. The migration writes
  the default row.
- The source order is in PostgreSQL. It is not in `.env`.
- The source order holds each bar source exactly 1 time (section 8.14).

### 8.7.2 Reading through the source order

- Each function that reads bars or saved ranges takes a source order:
  `read_saved_bars`, `has_saved_bars`, the bars route, the daily bar summary
  (section 8.11), and the warm-up reads of backtests and forward tests.
- Merge rule. For each time range, the first bar source in the source order
  that saved the range gives all bars of the range. When that bar source has
  no bar in the range (for example a holiday), the next bar source does not
  fill it. Thus the bars of one time range come from one bar source only.
- `read_saved_bars` returns the bars and the bar count of each bar source.
  A backtest records the source order that it used and these bar counts
  ([`backtest.md`](backtest.md) section 10).
- These reads use the global source order:
  - the bars route and the bar chart,
  - screens and the daily bar summary,
  - the warm-up bars of forward tests.
- A backtest uses the global source order by default. The backtest form can
  change it for one backtest.

### 8.7.3 Source order route and settings page

| Route | Behavior |
|---|---|
| `GET /api/market-data/source-order` | `200` with `{"source_order": ["ibkr", "databento"]}`. |
| `PUT /api/market-data/source-order` with `{"source_order": [...]}` | `200` with the saved source order. |
| | `422` when the list is empty, has a value 2 times, has a value that is not a `BarSource`, or leaves out a bar source. |

- The settings page `/settings` shows the source order. The header link
  "Settings" opens it. The page has a Carbon structured list with one row
  for each bar source, in the source order.
- Each row has 2 icon buttons: "Move <bar source> up" and "Move <bar source>
  down". The first row has no up button. The last row has no down button.
- A move saves the new source order at once with `PUT`. On an error, the
  list shows the `detail` text of the backend.
- The section has the heading "Source order" and no description.

## 8.8 Databento history import

Phase 3. Sources:
[Screen data sources (US and HK stocks)](https://github.com/Mano-Liaoyan/ATrade/issues/134),
[Free and low-cost data sources for the trial period](https://github.com/Mano-Liaoyan/ATrade/issues/143),
[One-time or usage-based historical data vendors](https://github.com/Mano-Liaoyan/ATrade/issues/144),
[Screen data source decision](https://github.com/Mano-Liaoyan/ATrade/issues/141).

- The trial budget accepts no monthly fee. The purchase uses the Databento
  new user credit (125 USD, it expires 6 months after sign-up). The cash cost
  is 0.
- IBKR gives the recent and the current bars. ATrade does not use IBKR to
  fill historical hourly bars.
- Databento has only US stocks. Databento US data starts on 2018-05-01.
- Databento has only prices that are not adjusted. The import adjusts them
  for stock splits before it saves them (section 8.8.3).
- Code (#190): `market_data/databento_client.py` (`DatabentoClient`, it
  downloads a bought batch job), `market_data/databento_import.py`
  (`import_databento_files`), and the program `app/databento_import.py`
  (`docs/architecture.md` section 6.4). Tests:
  `tests/market_data/test_databento_import.py`,
  `tests/app/test_databento_import_program.py`, and the fake
  `tests/fakes/databento.py`, which writes small DBN files.
- For each instrument with a daily bar in a bought time range, the import
  writes that time range to `databento_bar_saved_range`. The daily bars
  before 2024-07-01 use the time range that all 4 history files cover. The
  import refuses history files without all 4 file kinds, because the high,
  the low, and the volume need both exchanges. A second import of the same
  files adds no row.
- The import logs the symbols without `stat_type` 11 (they get no bar) and
  the EQUS.SUMMARY symbols without a listing exchange (section 8.14).

### 8.8.1 Purchase list

Prices were read with `metadata.get_cost` (`ALL_SYMBOLS`) on 2026-10-29.

| Dataset | Schema | Time range | Instruments | Cost |
|---|---|---|---|---|
| XNAS.ITCH | `ohlcv-1d` | 2018-05-01 to 2024-07-01 | All | 21.19 USD |
| XNYS.PILLAR | `ohlcv-1d` | 2018-05-01 to 2024-07-01 | All | 15.49 USD |
| XNAS.ITCH | `statistics` | 2018-05-01 to 2024-07-01 | All | 30.49 USD |
| XNYS.PILLAR | `statistics` | 2018-05-01 to 2024-07-01 | All | 8.12 USD |
| EQUS.SUMMARY | `ohlcv-1d` | 2024-07-01 to the purchase day | All | 10.87 USD (to 2026-10-28) |
| XNAS.ITCH | `ohlcv-1h` | For each instrument, only the quarters in which it is in the universe | Universe (section 8.9) | About 24 USD (estimate) |
| Total | | | | About 110 USD |

- Purchase order:
  1. Buy the daily bars and the `statistics`.
  2. Import them and calculate the quarterly universe (section 8.9).
  3. Run `get_cost` on the list of universe instruments and quarters.
  4. Buy the hourly bars.
- Do not buy: XNYS.PILLAR hourly bars, `definition`, `ohlcv-1m`, corporate
  action data.
- A Databento batch download costs one time. The user can download it again
  for 30 days.

### 8.8.2 Price rules

Daily bars before 2024-07-01:

| Field | Value |
|---|---|
| Open | The official open of the listing exchange: `statistics` `stat_type` 1. |
| Close | The official close of the listing exchange: `statistics` `stat_type` 11. |
| High | The higher of the XNAS.ITCH and the XNYS.PILLAR high. |
| Low | The lower of the XNAS.ITCH and the XNYS.PILLAR low. |
| Volume | The XNAS.ITCH volume plus the XNYS.PILLAR volume. |

- Do not use the `ohlcv-1d` close as the close. It includes trades after the
  close (to 20:00 ET). It differs from the official close by 0.14% on
  average, and by about 1% at most.
- Each exchange gives `statistics` prices only for the instruments that it
  lists. The listing exchange of an instrument is the exchange whose
  `statistics` has its prices.
- The instrument is `symbol / <listing exchange> / USD`. The listing exchange
  is `NASDAQ` or `NYSE`.
- The volume sum does not include other exchanges and trades off exchange.
  Use it only to rank instruments. It is not the trading value of the full
  market.

Daily bars from 2024-07-01: the EQUS.SUMMARY `ohlcv-1d` bar. Its close is the
official close. Its volume is the volume of the full market.
Its listing exchange is the exchange of the latest earlier Databento daily
bar of the same symbol (section 8.14).

Hourly bars:

- Use XNAS.ITCH `ohlcv-1h` only.
- Keep only the 7 bars that start from 9:00 to 15:00 ET. Delete all other
  bars.
- Save the 9:00 ET bar with the start 9:30 ET, the same start as the first
  IBKR regular-hours bar. Its open is the official open. Its high and low
  include the trades from 9:00 to 9:30 ET.
- Store the start in UTC (section 8.4).

### 8.8.3 Stock split adjustment at save time

The import saves Databento bars in the IBKR `TRADES` form. For each bar
before the ex-date of a stock split, it divides the prices by the split
ratio and multiplies the volume by the split ratio.

| Instruments | How the import finds the stock splits |
|---|---|
| Still trading | The ratio of the IBKR daily close to the Databento daily close on each day of the overlap. A constant ratio means no stock split. A step in the ratio gives the ex-date and the split ratio. |
| Stopped trading | The detection rule. The ratio of the close of one day to the open of the next day is near a common split ratio, for example 2, 3, 3/2, 1/2, or 1/10. The volume changes in the opposite direction. |

- The import writes each stock split that it finds to `stock_split`
  (section 8.13.1).
- The user checks all detected stock splits of instruments that stopped
  trading one time.
- An instrument still trades when it has a bar on the last day of the
  import. The import reads its IBKR daily bars for the days of its
  Databento bars. A ratio step is a change of more than 3% from one day to
  the next. The split ratio is the nearest fraction with a small
  denominator (2 for 2.004, 11/10 for 1.098). When IBKR has no bars of the
  instrument, the detection rule finds its stock splits.
- The detection rule accepts the split ratios 3/2, 2, 3, 4, 5, 10, 1/2,
  1/3, 1/4, 1/5, 1/10, and 1/20, each with a tolerance of 3%. A forward
  split needs a higher volume on the ex-date, a reverse split a lower
  volume.
- A stock split from the IBKR closes has the confirmation `bar_evidence`.
  The import adjusts the bars at once. A stock split of the detection rule
  has no confirmation: it waits for the user check, and the bars do not
  change until the user confirms it (section 8.14).
- A second import adjusts its bars with all confirmed stock splits of the
  instrument. A stock split that is in `stock_split` keeps its row and its
  confirmation.
- Code (#191): `market_data/stock_split_detection.py` (the 2 rules),
  `market_data/databento_import_adjustment.py` (links and adjustment in
  the import), `market_data/import_check.py` (the user check), and the
  program `app/databento_check.py`. Tests:
  `tests/market_data/test_stock_split_import.py` and
  `tests/app/test_databento_check_program.py`.

### 8.8.4 Symbol change links

- The Databento symbol is the symbol of that day. Databento does not link an
  old symbol to a new symbol, for example `SQ` to `XYZ`.
- Detection rule. The import links an old symbol to a new symbol when all
  these conditions are true:
  1. The last day of the old symbol and the first day of the new symbol are
     adjacent trading days.
  2. The last close of the old symbol and the first open of the new symbol
     differ by 1% or less.
  3. The listing exchange is the same.
- The import saves all history of a linked old symbol under the new symbol,
  the same as IBKR does.
- The import writes each link to `databento_symbol_link`: `old_symbol`,
  `new_symbol`, `exchange`, `change_day`, `checked_at_utc` (empty until the
  user checks it). `(old_symbol, new_symbol, exchange, change_day)` is
  unique.
- Adjacent trading days: no day of the import with a bar of any symbol is
  between the 2 days. A symbol with more than 1 candidate link gets no link.
  Links of 2 changes in a row go in the order of their change days, so the
  history ends under the last symbol.
- The import links the symbols before it finds the stock splits, so the
  stock splits use the full history under the new symbol.
- The user checks all detected links one time.
- Thus a backtest does not see a symbol change as a stop of trading. The
  new symbol has the history that the universe ranking needs.

## 8.9 Quarterly US universe

Phase 3. Sources:
[Screen data source decision](https://github.com/Mano-Liaoyan/ATrade/issues/141),
[Forward tests of multi-instrument strategies](https://github.com/Mano-Liaoyan/ATrade/issues/146).

- Rule. The universe changes on the first trading day of each quarter. It
  is the 500 common stocks with the highest average daily trading value in
  the previous 63 trading days. ETFs are not included.
- Trading value = close × volume of the daily bar.
- Before 2024-07-01, the volume is the XNAS.ITCH plus XNYS.PILLAR volume
  (section 8.8.2). From 2024-07-01, it is the EQUS.SUMMARY volume.
- The rule uses only data known on that day. Thus the universe includes
  instruments that stopped trading later.
- Backtests and forward tests use the same rule and the same data. A forward
  test does not calculate the universe from IBKR bars.
- The universe calculation reads `databento_bar` only. The source order does
  not apply to it.

Table `us_universe_member`:

| Column | Meaning |
|---|---|
| `quarter_start_utc` | 00:00 UTC of the first trading day of the quarter. |
| `rank` | 1 to 500, by average trading value. |
| `symbol`, `exchange`, `currency` | The instrument. |
| `average_trading_value` | The average daily trading value in USD. |
| `last_ranking_day_utc` | The last trading day of the 63-day window that was used. |

- The primary key is `(quarter_start_utc, rank)`. An instrument is in one
  quarter at most one time.
- A backtest with a top-N universe (N 500 at most) uses the members with
  `rank` ≤ N.

Quarterly update in the `forward-test` worker:

1. At 06:00 ET on the first trading day of the quarter, download the
   EQUS.SUMMARY `ohlcv-1d` bars of the 100 calendar days to the previous
   trading day (`ALL_SYMBOLS`). 100 days always hold 63 trading days, also
   when the previous quarter has fewer.
2. Calculate the members and save them in one transaction.
3. When the bar of the previous trading day is not available, try again each
   15 minutes until 09:00 ET.
4. When the bar is still not available at 09:00 ET, use the 63 trading days
   that end 1 trading day earlier. Record the actual last day in
   `last_ranking_day_utc`.
5. The strategies get the new members before the market opens.

- The cost is about 1.3 USD each quarter (`get_cost`: 1.23 to 1.36 USD).
- The update needs the setting `DATABENTO_API_KEY`. Without it, the update
  does not run, and the `forward-test` log tells why.
- Code (#192): `market_data/us_universe.py` (`save_us_universe`,
  `calculate_us_universe_history`, `read_us_universe_members`),
  `market_data/us_universe_update.py` (`UsUniverseUpdate`),
  `market_data/us_trading_days.py`, and `market_data/us_etf_symbols.py`.
  The Databento client gets `read_daily_summary_end_utc()`
  (`metadata.get_dataset_range`) and `download_daily_summary()`
  (`timeseries.get_range`). Tests: `tests/market_data/test_us_universe.py`
  and `tests/market_data/test_us_universe_update.py`.
- The average trading value is the sum of close × volume in the window
  divided by 63. A day without a bar of the instrument counts as 0. The
  same value gives the lower rank to the symbol later in alphabetical order.
- A day of the 63-day window is a day with Databento daily bars in
  `databento_bar`. `last_ranking_day_utc` is the last day with bars that the
  window used. The calculation refuses a window with less than 63 days, or
  a window that starts more than 100 calendar days before the last ranking
  day (a gap in `databento_bar`), and saves nothing.
- A saved quarter does not change. The history calculation adds only the
  quarters without members, so a quarter that the update calculated with the
  earlier window keeps it.

## 8.10 HK instrument list

Phase 3. Sources:
[Screen data source decision](https://github.com/Mano-Liaoyan/ATrade/issues/141),
[Screen page prototype](https://github.com/Mano-Liaoyan/ATrade/issues/145).

- Hong Kong bars come only from IBKR. No one-time purchase gives Hong Kong
  bars. Hong Kong has no financial data in ATrade.
- IBKR has no data for instruments that stopped trading. Thus each Hong Kong
  universe has survivorship bias.
- The HK instrument list is the default universe of an HK screen.
- Table `hk_instrument_list_member`: `id`, `symbol`, `exchange` (`SEHK`),
  `currency` (`HKD`), `added_at_utc`. An instrument is in the list at most
  one time.
- The user pastes symbols into the list. Before it saves an instrument, the
  add route checks it with `InstrumentLookup` (section 8.3).
- The daily bar update keeps the daily bars of the list up to date
  (section 8.11).

| Route | Behavior |
|---|---|
| `GET /api/market-data/hk-instrument-list` | `200` with `{"instruments": [{"id", "symbol", "exchange", "currency", "added_at_utc"}, ...]}` in the order of adding. |
| `POST /api/market-data/hk-instrument-list` with `{"symbols": ["700", "9988"]}` | `200` with `{"added": [...], "not_found": [...], "already_in_list": [...]}`. Each list has symbols. |
| | `422` when the list is empty, or a symbol is empty or longer than 32 characters. |
| | `503` with `{"detail": "IB Gateway is not reachable at <host>:<port>. The instrument check needs IB Gateway."}`. |
| | `502` with `{"detail": "The instrument check failed: <reason>"}`. |
| `DELETE /api/market-data/hk-instrument-list/{id}` | `204`. `404` with `{"detail": "This instrument is not in the HK instrument list."}`. |

- The table is in the migration
  `8d4b1e7c2a90_market_data_create_hk_instrument_list.py`. The routes are in
  `market_data/hk_instrument_list_routes.py`. `create_market_data_router`
  includes them. Listing and deleting do not need IB Gateway.
- The add route checks each new symbol as `<symbol> / SEHK / HKD` before
  it saves one. On `502` or `503`, the list does not change. A symbol that is
  already in the list is not checked again. A symbol that the request has 2
  times is in `already_in_list` the second time.
- Frontend: `#lib/market_data` has the HTTP client (`hk_instrument_list.ts`)
  and `HkInstrumentListEditor.svelte`. The editor is the section "HK
  instrument list" of the settings page `/settings` (`docs/architecture.md`
  section 13). It has the text input "Symbols" (spaces, tabs, commas, and
  line ends separate the symbols) and the button "Add to HK instrument
  list". After an add, the list "Add results" shows each symbol with a
  `StatusIndicator`: "<symbol> added" (success), "<symbol> not found"
  (error), and "<symbol> already in list" (warning). On `502` or `503`, an
  error notification shows the `detail` text. The table (Symbol, Added,
  Delete) is a Carbon `sm` data table in a `ScrollRegion` named "HK
  instrument list table". Each row has the Delete icon button "Delete
  <symbol> from the HK instrument list".

- Some pages show a survivorship bias warning with an icon, a word, and the
  warning color. The warning says that the universe has no instruments that
  stopped trading. It does not stop the run. These pages show it:
  - an HK screen,
  - the result page of an HK backtest,
  - the result page of a US backtest that starts before 2018-05-01.

## 8.11 Daily bar update and the daily bar summary

Phase 3. Sources:
[Screen page prototype](https://github.com/Mano-Liaoyan/ATrade/issues/145),
[Indicator library scope and calculation place](https://github.com/Mano-Liaoyan/ATrade/issues/136).

- The `web` process runs the daily bar update 1 time after the close of each
  trading day.
- The update reads daily bars from IBKR for these instruments:
  - the members of the current quarter of `us_universe_member`,
  - the HK instrument list,
  - the watchlist.
- It saves the bars in `ibkr_bar` and updates the daily bar summary.
- When IB Gateway is not reachable, the update does not run that day. The
  screen page shows the last daily bar date, so the user sees old data.
- Each read of bars from IBKR also reads 1 stored daily bar again (stock
  split evidence, section 8.13).

Table `daily_bar_summary`: one row for each instrument.

| Column | Meaning |
|---|---|
| `symbol`, `exchange`, `currency` | The instrument. Primary key. |
| `last_day_start_utc` | The start of the last daily bar. |
| `last_close` | The close of the last daily bar. |
| `average_trading_value_20` | The average close × volume of the last 20 daily bars. |

- Each save of daily bars updates the rows of its instruments: the bars
  route, `save_received_bars`, the daily bar update, the bar fetcher, the
  Databento import, and the stock split change of section 8.13.
- The summary reads the daily bars through the global source order.
- Screens use the summary for step 1 (still trading, last price, average
  trading value (20), exchange).

## 8.12 Bar fetcher of multi-instrument forward tests

Phase 3. Source: [Forward tests of multi-instrument strategies](https://github.com/Mano-Liaoyan/ATrade/issues/146).
This section has only the market data part. The forward test part is in
[`forward_test.md`](forward_test.md).

- The bar fetcher runs in the `forward-test` worker. It uses its own fixed
  client ID `ATRADE_IBKR_BAR_FETCHER_CLIENT_ID` (default `20`).
- After each daily close, it reads the daily bars of the members of all
  running multi-instrument forward tests from IBKR. It saves them with
  `save_received_bars` in `ibkr_bar`. It does not use `keepUpToDate`.
- Before a multi-instrument forward test starts, the fetcher reads the
  missing parts of the 1-year warm-up from IBKR.
- The warm-up bars come from the stored bars through the global source order
  (`ibkr_bar` and `databento_bar`). A warm-up does not send a request to IBKR
  for each member.
- Multi-instrument forward tests support only daily bars, with 500
  instruments at most.
- Implemented (#216): the fetcher gets the ranges to read from
  `read_unsaved_ranges(*, database_url, bar_request)` of the public entry.
  It returns the parts of the range that no bar source in the global source
  order saved, oldest first, and never calls IBKR. The bars route uses the
  same rule for its missing parts. The fetcher saves with
  `save_received_bars`.

## 8.13 Stock splits in the stored bars

Phase 3. Source: [Owner ledger change at a stock split](https://github.com/Mano-Liaoyan/ATrade/issues/149).
Decision record: [ADR 0008](../adr/0008-stock-splits-from-ibkr-evidence.md).
The owner ledger part is in [`paper_trading.md`](paper_trading.md) and
[`forward_test.md`](forward_test.md)
([ADR 0007](../adr/0007-owner-ledger-for-shared-paper-account.md)).

- A stock split is a forward split, a reverse split, or a bonus issue, of US
  and Hong Kong instruments. A bonus issue uses the split ratio, for example
  `1.1` for 1 new share for 10 shares.
- IBKR adjusts `TRADES` bars for stock splits. `market_data` reads only the
  missing ranges from IBKR. Thus after a stock split, the stored bars before
  the ex-date have the old prices.
- ATrade does not buy corporate action data.

### 8.13.1 Table `stock_split`

| Column | Meaning |
|---|---|
| `id` | |
| `symbol`, `exchange`, `currency` | The instrument. |
| `ex_date_utc` | 00:00 UTC of the ex-date. |
| `split_ratio` | `numeric`, above 0. New shares for 1 old share. |
| `source` | How ATrade found it: `ibkr_evidence` (section 8.13.2), or `databento_import` (section 8.8.3). |
| `confirmation` | How it was confirmed: `both_evidences` (both IBKR evidences), `bar_evidence` (the bar evidence only: no owner holds the instrument, or the IBKR closes of the Databento import), `user_apply` (the user, "Apply split"), or `import_check` (the user check of the import). `import_rejected`: the user rejected a detection of the import. Empty: the stock split waits for the user check. |
| `recorded_at_utc` | |

- One instrument has at most one stock split on one ex-date:
  `(symbol, exchange, currency, ex_date_utc)` is unique. Migration
  `20a1ab3c3c30` creates `stock_split` and `databento_symbol_link`.
- Only a stock split with the confirmation `both_evidences`,
  `bar_evidence`, `user_apply`, or `import_check` changes the bars.

### 8.13.2 Evidence from the stored bars

- Evidence A: each read of bars from IBKR also reads the daily bar of 1
  stored day again. The ratio of the stored close to the new IBKR close is
  the split ratio. A ratio of 1 means no stock split.
- Evidence B is the paper account position divided by the sum of the owner
  positions. Evidence B is part of the owner ledger.
- The owner ledger runs the check before the market opens: 08:00 ET for US
  and 08:30 HKT for Hong Kong.
- For an instrument that no owner holds, evidence A alone confirms the stock
  split.
- Some instruments are not in a universe and have no position, for example
  an instrument that the user only opened on a chart. Such an instrument
  gets evidence A when a bar read uses IBKR. The same rules apply to it.

### 8.13.3 Change of the stored bars

- When a stock split is confirmed, `market_data` changes the stored bars in
  one transaction:
  1. Write the `stock_split` row.
  2. In `ibkr_bar` and `databento_bar`, for all bar periods, for each bar
     that starts before the ex-date: divide the open, high, low, and close by
     the split ratio. Multiply the volume by the split ratio.
  3. Update the `daily_bar_summary` row of the instrument.
- The change sends no request to IBKR. It does not delete bars or saved
  ranges.
- The `databento_bar` bars of instruments that stopped trading cannot be read
  again.
  Thus a change in place is the only method for them.
- The saved results of earlier backtests do not change.

## 8.14 Left to the implementation

- Decided (#191): the enum values of `stock_split.source` and
  `stock_split.confirmation` are in section 8.13.1.
- Decided (#191): the user checks the detections with the command
  `python -m atrade.app.databento_check` (README.md). Without options, it
  lists the stock splits that wait for the check (with their IDs) and the
  symbol links that are not checked. `--accept` confirms all listed stock
  splits, changes the stored bars before their ex-dates in all bar tables
  (section 8.13.3), and records `checked_at_utc` on all listed links.
  `--reject-split <ID>` (with `--accept`) rejects one stock split: its row
  stays with `import_rejected`, so the next import does not find it again,
  and the bars do not change.
- Decided (#191): the import saves the bars before the check. It applies
  the symbol links and the stock splits from the IBKR closes at once. The
  stock splits of the detection rule change the bars only after the check.
- Not done (#191): a command that undoes a wrong symbol link. The import
  log and the check list show each link.
- Decided (#191): symbol reuse (a different company uses the symbol later)
  is not detected. The bars of both companies are under the same
  instrument. The link rule does not link them, because there is a gap of
  trading days between the 2 companies. The detection rule can see the
  price gap as a stock split; the user rejects it in the check.
- Decided (#190): the program `app/databento_import.py` runs the Databento
  import in the `web` image with `docker compose run`. The downloaded files
  are in `data/databento/` of the repository (in `.gitignore`), one
  directory for each batch job (`docs/architecture.md` section 22).
- Decided (#190): the listing exchange of an EQUS.SUMMARY bar is the
  exchange of the latest earlier Databento daily bar of the same symbol. A
  symbol without an earlier bar gets no bar, and the import names it.
- Decided (#190): the trading day of an official open or close is the New
  York date of its `ts_event`. The import uses the latest new value
  (`update_action` 1) of each day.
- Decided (#188): the source order must hold all bar sources, each 1 time.
  The order cannot leave out `ibkr`, so the bars route always reads the IBKR
  bars that it saves for the missing parts.
- Decided (#188): bars are read only inside the saved ranges of their bar
  source. A bar outside every saved range of its bar source is not read.
- How the stored day of evidence A is chosen, the tolerance for "ratio is
  1", and how ATrade finds the ex-date when evidence A comes days after the
  ex-date.
- Decided (#192): the universe rule leaves out the symbols of
  `market_data/us_etf_symbols.py`, a list of ETFs and ETNs with a high
  trading value. Only the instruments with the highest trading values can be
  members, so the list does not need all ETFs. Add a symbol when an ETF shows
  in `us_universe_member`.
- Decided (#192): the first quarter of `us_universe_member` starts on
  2018-10-01, the first quarter with a full 63-day window after 2018-05-01.
  The Databento import program calculates each quarter from 2018-10-01 that
  has no members and a Databento bar on its previous trading day.
- The official open of the hourly 9:30 ET bar from 2024-07-01, because the
  purchase has no `statistics` from that day.
- Decided (#192): the quarterly update saves the downloaded EQUS.SUMMARY
  bars in `databento_bar` with the Databento import, because the calculation
  reads only `databento_bar`.
- Decided (#192): the trading calendar of "first trading day of the
  quarter" and "previous trading day" is weekdays without New Year's Day
  (Monday 2 January when 1 January is a Sunday) and Good Friday. These are
  the only US exchange holidays near a quarter start. "Before the market
  opens" is 06:00 to 09:00 ET (`America/New_York`).
- Decided (#192): no table records each calculation. The `forward-test` log
  has the tries, the 09:00 ET fallback, and the errors. After an error, the
  update tries again after 15 minutes.
- The time of the daily bar update after the US close and after the Hong
  Kong close, and the trading calendars that it uses.
- How `daily_bar_summary` decides "still trading", and how it is calculated
  again after a change of the global source order.
- Decided (#216): the daily bar update (`web`, client ID of the Web
  process) and the bar fetcher (`forward-test`, client ID 20) can save the
  same instrument at the same time. The fill lock of section 8.4 is only in
  the Web process. Both saves use the same SQL (`save_received_bars`), so a
  second save adds no row. A test of the bar fetcher saves the same bars a
  second time and finds the same bar count.
- How symbol reuse is handled: a symbol that a different company uses later.
- The bar start of the hourly 9:30 ET bar is not on a whole hour from the
  UNIX epoch (section 8.4). The bars route widens a range to whole bar
  periods. The implementation decides how hourly ranges are widened.
