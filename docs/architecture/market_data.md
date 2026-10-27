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
  page (`src/routes/+page.svelte`) shows it. Each result is written as
  `symbol / exchange / currency`, for example `700 / SEHK / HKD`. On `502` or
  `503`, the panel shows the `detail` text of the backend.
- The result list is in a `ScrollRegion` (section 13), so a long list has a
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
- Before it saves an instrument, the add route checks it with
  `InstrumentLookup`. Thus the watchlist holds only instruments that IBKR
  knows. Listing and deleting do not need IB Gateway.

| Route | Behavior |
|---|---|
| `GET /api/watchlist` | `200` with `{"instruments": [{"id", "symbol", "exchange", "currency", "added_at_utc"}, ...]}` in the order of adding. |
| `POST /api/watchlist` with `{"symbol", "exchange", "currency"}` | `201` with the new watchlist instrument. |
| | `404` with `{"detail": "IBKR has no instrument <symbol> / <exchange> / <currency>. Add an instrument from the instrument search."}`. |
| | `409` with `{"detail": "This instrument is already in the watchlist."}`. |
| | `422` when a field is empty or too long (symbol 32, exchange 32, currency 8 characters). |
| | `503` with `{"detail": "IB Gateway is not reachable at <host>:<port>. The instrument check needs IB Gateway."}`. |
| | `502` with `{"detail": "The instrument check failed: <reason>"}`. |
| `DELETE /api/watchlist/{id}` | `204`. `404` with `{"detail": "This instrument is not in the watchlist."}` when the ID is not in the watchlist. |

- Frontend: `#lib/watchlist` has the HTTP client and the `Watchlist` panel.
  The home page owns the list. It gives `InstrumentSearch` a `resultAction`
  snippet: an "Add" button for each result, or "In watchlist" when the
  instrument is in the list. A capability does not import another
  capability, so the page combines them.
- The watchlist list is in a `ScrollRegion` named `Watchlist instruments`.
- Each watchlist instrument is a link to
  `/instruments/<exchange>/<symbol>?currency=<currency>`. This page is a
  placeholder that shows the instrument name. The bar chart ticket
  ([#65](https://github.com/Mano-Liaoyan/ATrade/issues/65)) replaces it with
  the chart.
