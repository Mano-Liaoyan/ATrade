# IBKR access

This document is section 7 of the architecture specification
([`docs/architecture.md`](../architecture.md)). It was moved to its own file
when the specification became longer than 1000 lines (section 18). Terms have
the meaning that [`GLOSSARY.md`](../../GLOSSARY.md) gives them.

Sources: [IBKR access research](https://github.com/Mano-Liaoyan/ATrade/issues/30),
[Broker and data source research](https://github.com/Mano-Liaoyan/ATrade/issues/43),
[ib_async compared with nautilus-ibapi](https://github.com/Mano-Liaoyan/ATrade/issues/54),
[Can the Web process use only NautilusTrader 2.0 for IBKR](https://github.com/Mano-Liaoyan/ATrade/issues/55),
[IB Gateway paper account check](https://github.com/Mano-Liaoyan/ATrade/issues/50),
[IBKR connection and Gateway status](https://github.com/Mano-Liaoyan/ATrade/issues/63).

## 7.1 Decisions

- IBKR is the only broker. Bars come from IBKR historical data first. When
  IBKR limits block backtests, add one US data vendor (Tiingo or Massive).
- One IB Gateway container runs and logs in to the paper account.
- The Web process uses `ib_async` for all IBKR access:
  - bars
  - instrument search
  - paper orders sent by hand, and order cancellation
  - the order list
  - `managedAccounts`
  - account balance and positions
- The Web process uses 1 fixed client ID (default `1`), set in `settings`.
- Forward test orders go from the NautilusTrader IB execution client inside a
  `LiveNode`. They do not go through `paper_trading`.
- Do not use client ID 0.
- Many client IDs can connect to one paper account Gateway at the same time.
  `reqAllOpenOrders` reads the open orders of other client IDs.
- One IBKR user name can have only one session. Set
  `EXISTING_SESSION_DETECTED_ACTION: primary` on the Gateway. A login on the
  IBKR website or phone app then competes with the Gateway session.
- The first login of the paper account did not ask for IB Key. Do not set
  `TWOFA_TIMEOUT_ACTION` or `RELOGIN_AFTER_TWOFA_TIMEOUT`.
- IBC in the Gateway image does the automatic login and the daily restart.
- Other containers connect to the paper API at `ib-gateway:4004` (socat in the
  gnzsnz image). The Gateway API port is not published outside the Compose
  network.
- Do not call `ib_async.util.patchAsyncio()` or `startLoop()`. `nest_asyncio`
  must not patch the uvicorn event loop.

## 7.2 The `ibkr` module

The public entry `atrade.ibkr` exports:

| Name | Purpose |
|---|---|
| `GatewayConnection` | A `Protocol` with the functions that other modules use: `keep_connected()`, `is_connected()`, `read_port()`, `read_connection_number()`, `read_managed_accounts()`, `read_account_values()`, `read_portfolio()`, `search_instruments(query)`, `disconnect()`. |
| `GatewayRequestError` | IB Gateway did not answer a request: no connection, a timeout, or an IBKR API error. |
| `AccountValue` | One account value from IBKR: `account`, `tag` (for example `NetLiquidation`), `value` (text), `currency`. |
| `PortfolioPosition` | One position of the account: symbol, security type, exchange, currency, quantity, average cost, market price, market value, unrealized P&L. |
| `IbAsyncGatewayConnection` | The real connection. It uses one `ib_async.IB` object, on the event loop of the caller. |
| `create_ibkr_router(...)` | The router of `GET /api/ibkr/gateway`. |

- `keep_connected()` runs until the caller cancels it. When the connection is
  not there, it tries to connect. It then waits `retry_seconds` (default 10)
  and checks again. A lost connection thus comes back without a restart. A
  failed attempt writes a warning with the Gateway address to the log.
- `read_connection_number()` counts the successful connections. A new
  number tells `paper_trading` to run the paper account check again
  (section 11.5).
- `read_account_values()` and `read_portfolio()` return the values that
  ib_async keeps up to date after the connection. They return an empty list
  when the connection is not there. They add no business rules.
- The constructor refuses client ID 0 and multiples of 1000, with the same
  check as `foundation/settings`.
- `app/web.py` gets a `GatewayConnection` as an argument of
  `create_web_app(...)`. The FastAPI lifespan starts `keep_connected()` as a
  task and cancels it at shutdown. The Web process starts and serves the UI
  when the Gateway is not reachable.
- The hand-written fake `tests/fakes/ibkr.py` (`FakeGatewayConnection`) has
  the same functions. Its data stays in memory. Tests set
  `is_gateway_reachable`, `connected`, `port`, `managed_accounts`,
  `account_values`, `portfolio`, `instruments`, and `search_error_message`
  directly. Each change of `connected` from false to true gives a new
  connection number.
- `search_instruments(query)` is the instrument search of
  [`docs/architecture/market_data.md`](market_data.md) section 8.2.

## 7.3 Gateway status route

| Route | Behavior |
|---|---|
| `GET /api/ibkr/gateway` | `200` with `{"status": "connected" \| "unreachable", "host": ..., "port": ...}`. `host` and `port` are `settings.ibkr_host` and `settings.ibkr_paper_port`. |

The app shell header shows the status and reads it again every 10 seconds.
When the Gateway is not reachable, it shows the address and asks the user to
make sure that the `ib-gateway` service runs and is logged in.

## 7.4 The `ib-gateway` Compose service

- Image: `ghcr.io/gnzsnz/ib-gateway:stable`, pinned by the digest of the
  multi-platform index (IB Gateway 10.50.1f on 2026-10-27).
- `TRADING_MODE=paper`, `EXISTING_SESSION_DETECTED_ACTION: primary`.
  `TWS_USERID` and `TWS_PASSWORD` come from `ATRADE_IBKR_USERNAME` and
  `ATRADE_IBKR_PASSWORD`. Only `ib-gateway` gets these values.
- The service has no `ports`. The API stays inside the Compose network.
- The service is in the Compose profile `ibkr`. `./start run` without the
  profile starts `postgres` and `web` only, so the local start does not need
  IBKR credentials. Set `COMPOSE_PROFILES=ibkr` in `.env` to start the
  Gateway.

## 7.5 Contract tests

- `backend/tests/ibkr/test_gateway_connection_contract.py` runs the same
  assertions against the fake and against the real paper account. It covers
  the connection, `managedAccounts`, and the instrument search.
- The real case has the mark `ibkr_paper`. The default pytest options
  (`-m "not ibkr_paper"`) leave it out, so CI runs only the fake. Run it by
  hand with `uv run pytest -m ibkr_paper` in `backend/`.
- The real case reads the repository `.env` file and the environment. It
  skips when `.env` or `ATRADE_IBKR_ACCOUNT_ID` is not there, or when no
  Gateway listens at `ATRADE_IBKR_HOST:ATRADE_IBKR_PAPER_PORT`. The Gateway
  port is not published, so set these 2 variables to an address that the
  test machine can reach, for example an SSH tunnel to the server.
- The assertions cover the connection, `managedAccounts` (exactly the paper
  account), the `NetLiquidation` balance in USD, and the positions of the
  account.
- The real case uses client ID `99`. It does not compete with the Web client
  ID or the forward test range.
