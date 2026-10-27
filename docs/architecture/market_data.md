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
