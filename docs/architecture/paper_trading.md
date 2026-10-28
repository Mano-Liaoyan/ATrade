# Paper trading

This document is section 11 of the architecture specification
([`docs/architecture.md`](../architecture.md)). It was moved to its own file
to keep the specification shorter than 1000 lines (section 18). Terms have
the meaning that [`GLOSSARY.md`](../../GLOSSARY.md) gives them.

Sources: [Order module design](https://github.com/Mano-Liaoyan/ATrade/issues/40),
[Paper account check and account panel](https://github.com/Mano-Liaoyan/ATrade/issues/74),
[Paper orders sent by hand](https://github.com/Mano-Liaoyan/ATrade/issues/75),
[Start and stop forward tests](https://github.com/Mano-Liaoyan/ATrade/issues/76).

## 11.1 Live order switch

- `settings.trading_mode` is `paper` or `live`.
- `settings.ibkr_account_id` is the expected IBKR account number. Its value is
  in `.env`, not in git.
- In this stage, when `trading_mode` is `live`, the program does not start. It
  writes the reason. The structure has a place for live orders, but no
  implementation.

## 11.2 Paper account check

`paper_trading` exports `require_paper_account()`. ATrade calls it before each
paper order sent by hand and before each forward test start. ATrade sends
orders only when all 4 conditions are true:

| Condition | Source |
|---|---|
| a. `trading_mode == "paper"` | ATrade setting |
| b. `managedAccounts` returns exactly 1 account, and it equals `settings.ibkr_account_id` | IB Gateway |
| c. The account number starts with `DU` | Protects against a live account number in `.env`. The user checked it on the paper account. |
| d. The Gateway runs with `TRADING_MODE=paper`, and ATrade connects to the paper port from `settings` | The only official IBKR method to tell paper from live |

- The Web process runs the check once after each connection and reconnection.
  It keeps the result in memory. Each order reads that result.
- When the connection drops, the result is cleared. Orders are refused.
- When the check fails:
  - ATrade does not send the order.
  - The HTTP response is an error. The UI shows the reason, with the actual
    and the expected account number.
  - A forward test does not start, and its status is "failed".
  - The log gets one error line.
  - ATrade does not retry.

## 11.3 Paper orders sent by hand

- Order types: market and limit. Time in force: DAY and GTC. No stop orders.
- The user can cancel an order. There is no order change. To change an order,
  cancel it and send a new one.
- Before sending, a confirmation dialog shows the instrument, side, quantity,
  order type, price, account number, and a clear `PAPER` mark.
- When a forward test runs on an instrument, the Web process refuses paper
  orders by hand for that instrument. It shows which forward test blocks it
  (#76). "Runs" means that the forward test holds a client ID
  ([`forward_test.md`](forward_test.md) section 12.2). The refusal is `409`
  with `OrderBlockedResponse` (`detail`, `forward_test_id`), for example
  "Forward test 3 (Trend v2) trades AAPL / NASDAQ. ATrade refuses orders by
  hand for this instrument until the forward test stops." It comes after the
  paper account check. ATrade sends nothing and stores nothing. Cancels of
  orders by hand are not blocked.
- Positions, balance, and order status go to the browser on
  `/ws/paper-trading`.
- Each order and each cancel calls `require_checked_paper_account()` first
  (section 11.5). When the check did not pass, or the connection is not
  there, ATrade does not send the order. The HTTP response is `403` with the
  reason, the actual accounts, and the expected account.
- The quantity is a whole number larger than 0. A limit order needs a limit
  price larger than 0. A market order has no limit price.
- ATrade sends each order to `SMART` routing with the primary exchange of the
  instrument, to the checked account, with the `orderRef` `ATRADE-BY-HAND`
  (section 12.9).

## 11.4 Order records and order list

- IBKR is the only source of order status.
- `paper_trading` stores only the paper orders that ATrade sent by hand: time,
  instrument, side, quantity, order type, price, IBKR order ID. It does not
  store status.
- The order list uses `reqAllOpenOrders`. It shows all open orders, including
  forward test orders.
- The list marks the source of each order: "by hand" or "forward test 42". The
  source comes from `orderRef` (section 12.9).
- Only orders sent by hand can be cancelled in the order list. To cancel
  forward test orders, stop the forward test.
- An order can be cancelled (`can_cancel`) when its source is "by hand" and
  its client ID is `settings.ibkr_web_client_id`. IBKR lets a client cancel
  only its own orders. The cancel route also requires a row in the local
  table.
- Filled orders sent by hand show data from the local table and from IBKR
  (#76). `GET /api/paper-trading/manual-orders` returns the local rows with
  `filled_quantity` and `average_fill_price` from `reqExecutions`
  (`GatewayConnection.read_executions()`): the executions with the IBKR order
  ID of the row, the Web client ID, and the account of the row. Both values
  are `null` when the check did not pass or IB Gateway does not answer.
  `reqExecutions` returns only the executions of the current day (section
  21), so an older fill shows `filled_quantity` `"0"`.
- The "Filled today" tab of the home page and the instrument page shows the
  list "Filled orders by hand"
  (`FilledManualOrderList.svelte`, `ScrollRegion` with the same label): the
  rows with `filled_quantity` larger than 0, newest first. It reads the route
  again after each "orders" message, because a fill changes the open orders.
- The local table is `manual_order`: `created_at_utc`, `account`, `symbol`,
  `exchange`, `currency`, `side`, `quantity`, `order_type`, `limit_price`,
  `time_in_force`, `ibkr_order_id`. It has no status column. ATrade writes
  the row after IB Gateway accepts the order request.
- The list has only the orders of the checked paper account. It is empty when
  the check did not pass.
- Positions and balance belong to the account, not to a client ID.

## 11.5 The `paper_trading` module

The public entry `atrade.paper_trading` exports:

| Name | Purpose |
|---|---|
| `require_paper_account(*, settings, gateway_connection)` | Runs the 4 conditions of section 11.2 on the given connection. Returns the paper account number. Raises `PaperAccountCheckError` (a `PermissionError`) when a condition fails or the connection is not there. A forward test child passes its own connection. |
| `PaperAccountCheck` | The result: `status` (`disconnected`, `passed`, `failed`), `message` (the reason of the failure), `actual_accounts`, `expected_account`. |
| `PaperAccountMonitor` | The check result of the Web process in memory, the balance, and the positions. |
| `PaperAccountBalance` | The balance of `read_balance()` (section 11.9): `net_liquidation_usd`, `cash_usd`, `base_currency`, `net_liquidation_base`, `cash_base`, `usd_per_base_unit`, `exchange_rate_source`, `message`. |
| `fetch_paper_capital_usd(paper_account_monitor)` | Async. The `NetLiquidation` value of the paper account in USD (section 11.9) after a passed check. Otherwise, and when no exchange rate is available, `settings.local_paper_capital_usd`. |
| `create_paper_trading_router(*, paper_account_monitor, database_url, clock, find_blocking_forward_test)` | The router of the order routes (section 11.8), of `GET /api/paper-trading/paper-capital`, and of `/ws/paper-trading`. `find_blocking_forward_test(instrument)` returns a `BlockingForwardTest` (`forward_test_id`, `label`) or `None`. `app/web.py` makes it from `forward_test.find_forward_test_on_instrument()`, because `paper_trading` does not import `forward_test`. |
| `PAPER_TRADING_SOCKET_MESSAGE_MODELS` | The models of `/ws/paper-trading` (`PaperAccountMessage`, `OpenOrdersMessage`, `HeartbeatMessage`) for the OpenAPI document. The frontend uses their generated types. |

`GET /api/paper-trading/paper-capital` returns `200` with
`{"paper_capital_usd": "<amount>"}`, the value of
`fetch_paper_capital_usd()`. The backtest form uses it as the default paper
capital (section 10). The frontend reads it with `readPaperCapital()` of
`#lib/paper_trading`.

- The check fails closed. A condition that ATrade cannot confirm is a failure,
  for example an empty `ATRADE_IBKR_ACCOUNT_ID`.
- `PaperAccountMonitor` runs the check when it sees a new connection number
  from `GatewayConnection.read_connection_number()` (section 7.2). Each
  successful connection gets a new number, so a reconnection runs the check
  again, also when it happens between 2 reads.
- When the connection is not there, the monitor clears the result. The status
  is `disconnected`.
- A failed check writes one error line to the logger `atrade.paper_trading`,
  with the reason, the actual accounts, and the expected account. The monitor
  does not check again until the next connection.
- `require_checked_paper_account()` returns the account number for an order.
  It raises `PaperAccountCheckError` when the result is not `passed`.
- The balance and the positions come only after a passed check, and only for
  the checked account. The balance is the `NetLiquidation` and the
  `TotalCashValue` account values, converted to USD (section 11.9).
  `read_balance()` is async, because the conversion can read a rate from
  IBKR. ib_async keeps the account values and the portfolio up to date,
  because it subscribes to the account updates of the only managed account.
- `app/web.py` creates one monitor. The FastAPI lifespan runs
  `keep_checking()` every 0.5 seconds, so that a failed check reaches the log
  also when no browser is open. Each read also runs the check when needed.

## 11.6 `/ws/paper-trading`

| Message | When |
|---|---|
| `{"type": "account", "check": {...}, "balance": {...} \| null, "positions": [...]}` | At once after the socket opens, and after each change. The server compares the state every 0.25 seconds. |
| `{"type": "orders", "orders": [...]}` | At once after the socket opens, and after each change. The server reads the open orders (`reqAllOpenOrders`) every 1 second. |
| `{"type": "heartbeat"}` | After 10 seconds without another message. |

- `check` has the fields of `PaperAccountCheck`.
- `balance` has the fields of `PaperAccountBalance` (section 11.9). It is
  `null` when the check did not pass.
- Each position has `symbol`, `security_type`, `exchange`, `currency`,
  `quantity`, `average_cost`, `market_price`, `market_value`,
  `unrealized_pnl`. The list is empty when the check did not pass.
- Each order has the fields of `OpenOrderResponse` (section 11.8). When IB
  Gateway does not answer, the server keeps the last list and tries again.
- Amounts and quantities are decimal text, for example `"101234.50"`.
- The browser sends nothing. The server reads the socket only to see when the
  browser leaves.
- The route and its message models are in `paper_trading/account_socket.py`.
  `create_paper_trading_router` includes it. `paper_trading` exports the
  message models in `PAPER_TRADING_SOCKET_MESSAGE_MODELS`;
  `app/openapi_document.py` adds their JSON Schema to the OpenAPI document
  (section 13). The order routes and the paper capital route are in
  `paper_trading/http_routes.py`.

## 11.7 Account overview and paper order form

- The home page is the account overview workbench (section 13): the key
  numbers of the paper account in one line, the Positions panel, and the
  Orders panel (Open orders and Filled today). It has no paper order form.
  The header shows the `PAPER` tag with the checked account.
- When the check does not pass, the key numbers line shows the check status.
  When the check fails, it also shows the reason, the actual account, and
  the expected account.
- The key numbers (`listBalanceMetrics`) are "Net liquidation (USD)" and
  "Cash (USD)". For a base currency that is not USD, they also have the net
  liquidation in the base currency and the rate, for example
  "USD per EUR 1.1139". Without a rate, the line shows the `message` of the
  balance as an error status, and the USD values show `–`.
- The page uses `PaperAccountFeed` (`foundation/live_socket` for
  reconnection and heartbeat) and `foundation/scroll_region` for the tables
  (section 13). The tables have 32px rows.
- The "Paper order" column of the instrument page has the paper order panel
  (`InstrumentOrderPanel.svelte`, section 13): the order is for the instrument
  of the page. "Review buy order" or "Review sell order" opens the Carbon
  modal. The modal label is the paper account number, and the modal title is
  the full order, for example "Buy 50 AAPL". The body has the `PAPER` mark,
  the instrument, the order type, and the price. Only "Send paper order" in
  the modal sends the order. "Cancel", the close button, a click outside, and
  Escape send nothing. Focus stays in the modal while it is open, and goes
  back to the review button when it closes.
- The instrument page reads `/ws/forward-tests`
  (`ForwardTestsOnInstrumentsFeed`) and gives the panel the forward tests that
  hold a client ID (`listForwardTestsOnInstruments` of `forward_test`, type
  `BlockingForwardTest` of `paper_trading`). When the instrument matches one
  of them, the review button is disabled and the panel says why, for example
  "Forward test 3 (Trend v2) trades AAPL / NASDAQ. Stop the forward test to
  send an order by hand." (`findInstrumentOrderBlock`). The backend still
  refuses the order with `409` (section 11.3).
- The open order list (`OpenOrderList.svelte`) comes from the "orders"
  message. It shows the source of each order ("by hand" or "forward test
  42"). Each row has an overflow menu "Actions for order N". Its cancel item
  is enabled only when `can_cancel` is true. A disabled item says why, for
  example "Stop forward test 42 to cancel". It uses
  `foundation/scroll_region` with the label "Open orders".
- The result of the order and cancel routes shows in the form or the order
  list as an inline
  notification that the user can close: "Order N sent", "Cancel request sent
  for order N", or an error (an alert) with the actual and the expected
  account for a `403`.

## 11.8 Order routes

| Route | Behavior |
|---|---|
| `POST /api/paper-trading/orders` | Body `SendOrderRequest`: `symbol`, `exchange`, `currency`, `side` (`BUY`, `SELL`), `quantity`, `order_type` (`MKT`, `LMT`), `limit_price`, `time_in_force` (`DAY`, `GTC`). `201` with the stored row (`ManualOrderResponse`, with `ibkr_order_id`). `403` (`OrderRefusedResponse`: `detail`, `actual_accounts`, `expected_account`) when the paper account check did not pass or the connection is not there. `409` (`OrderBlockedResponse`: `detail`, `forward_test_id`) when a forward test runs on the instrument (section 11.3). `422` for a body that is not valid. `502` when IB Gateway refuses the request. |
| `GET /api/paper-trading/orders` | `200` with `{"orders": [OpenOrderResponse]}`: the open orders of the checked account. Each order has `order_id`, `account`, `symbol`, `exchange`, `currency`, `side`, `quantity`, `order_type`, `limit_price`, `time_in_force`, `status` (IBKR text), `filled_quantity`, `source` (`kind`: `by_hand` or `forward_test`, `forward_test_id`), `can_cancel`. `502` when IB Gateway does not answer. |
| `DELETE /api/paper-trading/orders/{order_id}` | `202` after ATrade sends the cancel request. IBKR confirms it later in the order list. `403` as for `POST`. `404` when no open order of the account has this ID, or when ATrade did not send it by hand. `409` for an order of a forward test or of another client. `502` when IB Gateway does not answer. |
| `GET /api/paper-trading/manual-orders` | `200` with `{"manual_orders": [ManualOrderWithFillsResponse]}`: the rows of `manual_order`, oldest first, each with `filled_quantity` and `average_fill_price` (section 11.4). |

- The backend tests (`backend/tests/paper_trading/test_paper_orders.py`) go
  through these routes with the IBKR fake and real PostgreSQL.
- The Playwright test `frontend/e2e/paper_orders.spec.ts` sends an order
  through the modal, cancels it, checks the focus trap, Escape, and the focus
  return of the modal, checks the keyboard control of the side, order type,
  and time in force, and checks the scroll track of the order list. The e2e server has 30 open orders of forward test 42.

## 11.9 Balance in USD for any base currency

ATrade keeps money in USD (section 10). The paper account of the owner has
the base currency EUR, and IBKR does not let the owner change it. IBKR sends
`NetLiquidation` and `TotalCashValue` only in the base currency.
`PaperAccountMonitor.read_balance()` therefore converts them:

1. The base currency is the currency of `NetLiquidation` (not `BASE` and
   not empty). When IBKR also sends a USD value, ATrade uses USD.
2. Base currency USD: no conversion. `exchange_rate_source` is
   `base_currency_is_usd` and `usd_per_base_unit` is `1`.
3. Else, when the account values have `ExchangeRate` or
   `$LEDGER-ExchangeRate` for `USD` (base currency units for 1 USD; IBKR
   sends it only when the ledger has USD), the rate is `1 / value`.
   `exchange_rate_source` is `account`. Not seen on the real account yet
   (section 21.1).
4. Else, the IBKR forex rate `GatewayConnection.read_exchange_rate(base,
   "USD")` (section 7.2). `exchange_rate_source` is `ibkr_forex`. The monitor
   keeps the rate for 60 seconds, and reads it again after a new connection
   or for a new base currency. A failed read is also kept for 60 seconds.
5. Without a rate, the USD values are `None` and `message` says why, for
   example "The paper account has the base currency EUR and IBKR sent no EUR
   to USD exchange rate: ...".

- A converted amount is rounded to the cent. A USD amount stays as IBKR sent
  it.
- Fail closed: without a USD value, a forward test does not start (exit code
  3, "The paper account has no NetLiquidation value in USD." and the
  `message`, section 12.8), and `fetch_paper_capital_usd()` returns the local
  value. Orders by hand do not use the balance, so a missing rate does not
  block them.
- The balance shows the base currency values and the rate, so the user sees
  what ATrade converted (section 11.7).
