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
- Before it saves an instrument, the add route checks it with
  `InstrumentLookup`. Thus the watchlist holds only instruments that IBKR
  knows. Listing and deleting do not need IB Gateway.

| Route | Behavior |
|---|---|
| `GET /api/watchlist` | `200` with `{"instruments": [{"id", "symbol", "exchange", "currency", "added_at_utc", "saved_bars"}, ...]}` in the order of adding. `saved_bars` is `[{"bar_period", "first_start_utc", "last_start_utc"}, ...]`: only the bar periods with saved bars, in the order of the bar periods (1 minute first). |
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
- Tables (migration `5b2d8e7f4a61`):
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
- The public entry exports `read_saved_bars(*, database_url, bar_request)`
  with `BarRequest(instrument, bar_period, time_range)`. It reads only the
  bars in PostgreSQL and never calls IBKR. Backtests use it (section 10).
- The public entry exports `save_received_bars(*, database_url, bar_request,
  bars)` (async) and `save_received_bars_blocking(...)` (the same, for
  synchronous callers). They save complete bars that a caller received from
  IBKR for `bar_request.time_range`, and record that range as saved, in one
  transaction. They use the same SQL as the bars route. A bar that is
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
