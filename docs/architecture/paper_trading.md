# Paper trading

This document is section 11 of the architecture specification
([`docs/architecture.md`](../architecture.md)). It was moved to its own file
to keep the specification shorter than 1000 lines (section 18). Terms have
the meaning that [`GLOSSARY.md`](../../GLOSSARY.md) gives them.

Sources: [Order module design](https://github.com/Mano-Liaoyan/ATrade/issues/40),
[Paper account check and account panel](https://github.com/Mano-Liaoyan/ATrade/issues/74),
[Paper orders sent by hand](https://github.com/Mano-Liaoyan/ATrade/issues/75),
[Start and stop forward tests](https://github.com/Mano-Liaoyan/ATrade/issues/76),
[Forward tests of multi-instrument strategies](https://github.com/Mano-Liaoyan/ATrade/issues/146),
[How the owner ledger changes at a stock split](https://github.com/Mano-Liaoyan/ATrade/issues/149).
ADRs: [0007 owner ledger](../adr/0007-owner-ledger-for-shared-paper-account.md),
[0008 stock splits](../adr/0008-stock-splits-from-ibkr-evidence.md).

### Implementation phases of this section

The planning map [Wayfinder: indicators, screens, and strategy help](https://github.com/Mano-Liaoyan/ATrade/issues/129)
adds work to this section. A part without a phase mark is the current
implementation and stays true.

| Phase | Parts of this section |
|---|---|
| Phase 1 | No change. |
| Phase 2 | No change. The AI assistant never sends a paper order (section 11.5). |
| Phase 3 | The owner ledger (section 11.10), the stock split changes of the ledger (section 11.11), the Owner column and the "Unattributed" difference (section 11.7), the new refusals of orders by hand (sections 11.3, 11.8), and the limits (section 11.12). |

Until Phase 3 is done, the rules marked "until Phase 3" stay in force.

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
- Until Phase 3: when a forward test runs on an instrument, the Web process
  refuses paper orders by hand for that instrument. It shows which forward test blocks it
  (#76). "Runs" means that the forward test holds a client ID
  ([`forward_test.md`](forward_test.md) section 12.2). The refusal is `409`
  with `OrderBlockedResponse` (`detail`, `forward_test_id`), for example
  "Forward test 3 (Trend v2) trades AAPL / NASDAQ. ATrade refuses orders by
  hand for this instrument until the forward test stops." It comes after the
  paper account check. ATrade sends nothing and stores nothing. Cancels of
  orders by hand are not blocked.
- Phase 3 (#146, [ADR 0007](../adr/0007-owner-ledger-for-shared-paper-account.md)):
  the refusal above goes away. A paper order by hand belongs to the owner
  "By hand". Before it sends the order, the Web process checks the order
  rules of the owner ledger (section 11.10) for "By hand". When a rule
  fails, the response is `409` with the reason. ATrade sends nothing and
  stores nothing.
- Implemented (#214): the ledger rules for orders by hand run after the
  paper account check.
- Implemented (#215): the forward test refusal and `OrderBlockedResponse`
  are gone. An order by hand on the instrument of a running forward test
  goes to IBKR when the ledger rules of "By hand" pass.
- Phase 3 (#149): an order by hand on an instrument in the
  "Split check needed" state is refused with `409` and the reason
  (section 11.11). Cancels are not blocked.
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
- Phase 3 (#146): the source of an order is also its owner. "by hand" is the
  owner "By hand". "forward test 42" is the owner "Forward test 42".
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
- Phase 3 (#149): a stock split adjustment is not a fill. "Filled today" does
  not show it.
- The local table is `manual_order`: `created_at_utc`, `account`, `symbol`,
  `exchange`, `currency`, `side`, `quantity`, `order_type`, `limit_price`,
  `time_in_force`, `ibkr_order_id`. It has no status column. ATrade writes
  the row after IB Gateway accepts the order request.
- The list has only the orders of the checked paper account. It is empty when
  the check did not pass.
- Positions and balance belong to the account, not to a client ID.
- Phase 3 (#146): each position and each cash amount of the account also
  belongs to owners in the owner ledger (section 11.10). The IBKR position
  stays the source of the account position.

## 11.5 The `paper_trading` module

The public entry `atrade.paper_trading` exports:

| Name | Purpose |
|---|---|
| `require_paper_account(*, settings, gateway_connection)` | Runs the 4 conditions of section 11.2 on the given connection. Returns the paper account number. Raises `PaperAccountCheckError` (a `PermissionError`) when a condition fails or the connection is not there. A forward test child passes its own connection. |
| `PaperAccountCheck` | The result: `status` (`disconnected`, `passed`, `failed`), `message` (the reason of the failure), `actual_accounts`, `expected_account`. |
| `PaperAccountMonitor` | The check result of the Web process in memory, the balance, and the positions. |
| `PaperAccountBalance` | The balance of `read_balance()` (section 11.9): `net_liquidation_usd`, `cash_usd`, `base_currency`, `net_liquidation_base`, `cash_base`, `usd_per_base_unit`, `exchange_rate_source`, `message`. |
| `fetch_paper_capital_usd(paper_account_monitor)` | Async. The `NetLiquidation` value of the paper account in USD (section 11.9) after a passed check. Otherwise, and when no exchange rate is available, `settings.local_paper_capital_usd`. |
| `create_paper_trading_router(*, paper_account_monitor, database_url, clock)` | The router of the order routes (section 11.8), of `GET /api/paper-trading/paper-capital`, and of `/ws/paper-trading`. `find_blocking_forward_test` is gone (#215). |
| `ManualOrderLedger`, `ForwardTestLedger`, `OwnerOrder`, `OwnerFill`, `OwnerPosition`, `LedgerFill` | The owner ledger (#214, #215). `ManualOrderLedger.read_entries(account)` starts the ledger when needed. `ForwardTestLedger(*, database_url, account, forward_test_id, gateway_connection, clock)` is the `OwnerLedger` of the ATrade execution client (`check_order`, `save_fill`, `read_positions`, `read_cash_usd`). |
| `write_capital_allocation(connection, *, account, forward_test_id, allocated_capital_usd, time_utc)`, `transfer_to_by_hand(connection, *, forward_test_id, time_utc)` | The `transfer` rows at the start and at the stop of a forward test (section 11.13). The caller commits. |
| `read_forward_test_fills(connection, forward_test_id)`, `read_forward_test_fills_blocking(connection, forward_test_id)` | The fills of a forward test in the owner ledger, oldest first, for the routes and the recorder of `forward_test`. |
| `PAPER_TRADING_SOCKET_MESSAGE_MODELS` | The models of `/ws/paper-trading` (`PaperAccountMessage`, `OpenOrdersMessage`, `HeartbeatMessage`) for the OpenAPI document. The frontend uses their generated types. |

Phase 3 changes of the public entry (#146, #149). The names are choices of
this document. The implementation can change them.

| Name | Purpose |
|---|---|
| `check_owner_order(*, database_url, owner, order)` | Checks the order rules of section 11.10 and the "Split check needed" state of section 11.11 for one owner. Returns `None` or the reason of the refusal. The Web process uses it for orders by hand. The ATrade execution client of `forward_test` uses it for each forward test order. |
| `record_owner_fill(*, database_url, owner, fill)` | Writes one fill into the owner ledger. Idempotent on the IBKR execution ID. |
| `read_owner_positions(*, database_url, owner)` | The positions and the cash of one owner, for the reconciliation reports of the ATrade execution client. |
| `transfer_owner_to_by_hand(*, database_url, forward_test_id)` | Moves the positions and the remaining cash of a stopped forward test to "By hand" (section 11.10). |
| `apply_stock_split(*, database_url, stock_split)` | Changes the owner ledger for a stock split in one transaction (section 11.11). |
| `Owner` | `kind` (`by_hand`, `forward_test`) and `forward_test_id` (null for `by_hand`). |

- Implemented (#214): the ledger of "By hand" is in
  `paper_trading/manual_order_ledger.py` (`ManualOrderLedger`: the ledger
  start, the fills of orders by hand, and the 3 order rules) and
  `paper_trading/owner_ledger_store.py` (the SQL and the sums).
- Implemented (#215): `forward_test` uses `ForwardTestLedger`,
  `write_capital_allocation`, `transfer_to_by_hand`, and
  `read_forward_test_fills` of the first table
  (`paper_trading/forward_test_ledger.py`), not the planned names
  `check_owner_order`, `record_owner_fill`, `read_owner_positions`, and
  `transfer_owner_to_by_hand`. `apply_stock_split` comes with the split
  check.
- Phase 3: `create_paper_trading_router` loses `find_blocking_forward_test`,
  because the refusal of section 11.3 goes away. It gets
  `read_allocated_capital` from `app/web.py`, which calls
  `forward_test.read_allocated_capital()`. `paper_trading` still does not
  import `forward_test`.
- Phase 2 (#140, #150): the AI assistant has no tool that sends or cancels a
  paper order. Its tool allow list has no paper order route.

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
- Phase 3 (#146, #149): each position also has `owners` (a list of `owner`,
  `quantity`, `average_cost` from the owner ledger), `unattributed_quantity`
  (the IBKR quantity minus the sum of the owner quantities), and
  `split_check` (null, or `stock_split_id`, `split_ratio`,
  `account_quantity_before`, `account_quantity_after`). The `account`
  message also gets `unattributed_cash_usd` (section 11.12). The field names
  are choices of this document.
- Implemented (#214): `owners` and `unattributed_quantity` on each
  position, and `unattributed_cash_usd` on the `account` message. `owner` is
  `{kind, forward_test_id}`. `average_cost` of an owner is `null` when the
  owner holds no shares. Without a ledger start (section 11.10), `owners` is
  empty, `unattributed_quantity` is the IBKR quantity, and
  `unattributed_cash_usd` is `null`. `unattributed_cash_usd` is
  `balance.cash_usd` minus the sum of the cash of all owners.
- Implemented (#220): `split_check` is `null`, or `id` (the ID of the
  stock split routes of section 11.8), `stock_split_id` (`null` when only
  the position shows the stock split), `split_ratio`,
  `account_quantity_before`, and `account_quantity_after`.
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
- Implemented (#215): the instrument page does not read `/ws/forward-tests`.
  `findInstrumentOrderBlock(account)` blocks the review button only while
  the paper account is not read or its check did not pass.
- The open order list (`OpenOrderList.svelte`) comes from the "orders"
  message. It shows the source of each order ("by hand" or "forward test
  42"). Each row has an overflow menu "Actions for order N". Its cancel item
  is enabled only when `can_cancel` is true. A disabled item says why, for
  example "Stop forward test 42 to cancel". It uses
  `foundation/scroll_region` with the label "Open orders".
- Phase 3 (#146): the Positions table gets an "Owner" column. Each owner of
  an instrument has its own row, for example "By hand" or "Forward test 3".
  The frontend changes the forward test ID into "Forward test <ID>" in
  `routes/`.
- Phase 3 (#146): when the IBKR position of an instrument is not the sum of
  the owner positions, the row of that instrument shows a warning icon and
  the difference, for example "Unattributed: 50". The icon and the word
  together show the state, not only the color.
- Implemented (#214): `PositionTable.svelte` shows one row for each owner
  (`listPositionRows` of `paper_account.ts`): the owner quantity and
  average cost, the market value and the unrealized P&L at the IBKR market
  price. The difference is one more row of the instrument with the warning
  status "Unattributed: 50" in the Owner column and empty number cells. A
  position without owners and without a difference has one row with the
  IBKR values and an empty Owner cell. The compact table of the instrument
  page also has the Owner column.
- Phase 3 (#149): an instrument in the "Split check needed" state has a row
  with a warning icon, "Split check needed", the detected ratio, and the
  IBKR share count before and after. The row has 2 buttons:
  "Apply split 4:1" (the ratio of the row) and "Keep ledger". Each button
  says what it does. The row has no other help text.
  Implemented (#220): the row is one more row of the instrument in
  `PositionTable.svelte`: the warning status "Split check needed: 4:1" in
  the Owner column, "10 → 40" in the Quantity column, and the 2 buttons in
  the other cells. The compact table of the instrument page shows the row
  without the buttons. A failed button shows the error notification "Split
  check not changed". `frontend/e2e/stock_split.spec.ts` checks the row,
  the order panel, the forward test header, "Apply split 4:1", and the
  "Fills" row.
- Phase 3 (#146): when the ledger refuses an order by hand, the review button
  stays enabled, and the `409` reason shows as an inline error notification.
  Implemented (#214): the notification "Order not sent" with the `detail`.
  When the instrument is in the "Split check needed" state, the review button
  is disabled and the panel says why, for example "AAPL needs a split check.
  Apply the split or keep the ledger on the paper trading page.".
  Implemented (#220): `findInstrumentOrderBlock(account, instrument)` reads
  the `split_check` of the position of the instrument.
- Phase 3: the review button no longer depends on `/ws/forward-tests`, because
  the forward test block of section 11.3 goes away. Implemented (#215).
- The result of the order and cancel routes shows in the form or the order
  list as an inline
  notification that the user can close: "Order N sent", "Cancel request sent
  for order N", or an error (an alert) with the actual and the expected
  account for a `403`.

## 11.8 Order routes

| Route | Behavior |
|---|---|
| `POST /api/paper-trading/orders` | Body `SendOrderRequest`: `symbol`, `exchange`, `currency`, `side` (`BUY`, `SELL`), `quantity`, `order_type` (`MKT`, `LMT`), `limit_price`, `time_in_force` (`DAY`, `GTC`). `201` with the stored row (`ManualOrderResponse`, with `ibkr_order_id`). `403` (`OrderRefusedResponse`: `detail`, `actual_accounts`, `expected_account`) when the paper account check did not pass or the connection is not there. `409` (`OrderRefusedByLedgerResponse`: `detail`, `rule`) when a ledger rule fails (section 11.10). `422` for a body that is not valid. `502` when IB Gateway refuses the request. |
| `GET /api/paper-trading/orders` | `200` with `{"orders": [OpenOrderResponse]}`: the open orders of the checked account. Each order has `order_id`, `account`, `symbol`, `exchange`, `currency`, `side`, `quantity`, `order_type`, `limit_price`, `time_in_force`, `status` (IBKR text), `filled_quantity`, `source` (`kind`: `by_hand` or `forward_test`, `forward_test_id`), `can_cancel`. `502` when IB Gateway does not answer. |
| `DELETE /api/paper-trading/orders/{order_id}` | `202` after ATrade sends the cancel request. IBKR confirms it later in the order list. `403` as for `POST`. `404` when no open order of the account has this ID, or when ATrade did not send it by hand. `409` for an order of a forward test or of another client. `502` when IB Gateway does not answer. |
| Phase 3: `POST /api/paper-trading/orders` | The `409` with `OrderBlockedResponse` for a forward test goes away (implemented, #215). New `409` (`OrderRefusedByLedgerResponse`: `detail`, `rule`) when an order rule of section 11.10 fails (`rule`: `sell_more_than_position`, `buy_more_than_cash`) or the instrument is in the "Split check needed" state (`rule`: `split_check_needed`). Example `detail`: "By hand holds 40 AAPL and has open sell orders for 10. ATrade refuses a sell order for 50.". |
| Phase 3: `POST /api/paper-trading/stock-splits/{id}/apply` (new) | Applies the stock split of the "Split check needed" state to the owner ledger (section 11.11). `200` with the changed owner positions. `404` for an unknown ID. `409` when the instrument is not in the "Split check needed" state for this stock split. |
| Phase 3: `POST /api/paper-trading/stock-splits/{id}/keep-ledger` (new) | Ends the "Split check needed" state without a ledger change. The difference stays as "Unattributed". `200`. `404` and `409` as for `apply`. |
| `GET /api/paper-trading/manual-orders` | `200` with `{"manual_orders": [ManualOrderWithFillsResponse]}`: the rows of `manual_order`, oldest first, each with `filled_quantity` and `average_fill_price` (section 11.4). |

- The Phase 3 route names, the response names, and the `rule` values are
  choices of this document.
- Implemented (#220): the `{id}` of the 2 stock split routes is the
  `split_check` ID, because a `position_only` check has no stock split row.
  `apply` returns `StockSplitAppliedResponse` (`split_check`, and `owners`:
  the owner positions of the instrument after the change). `keep-ledger`
  returns `SplitCheckResolvedResponse` (`id`, `symbol`, `exchange`,
  `currency`, `status`). Both give `404` for an unknown ID and `409` when
  the split check is not `needed`. `apply` also gives `409` when
  `market_data` confirmed the stock split already, and `502` when IBKR does
  not answer for the last close or the forex rate. An order by hand on an
  instrument in the state gets `409` with the `rule` `split_check_needed`
  and the `detail` "AAPL needs a split check. Apply the split or keep the
  ledger on the paper trading page.". A cancel is not blocked. The tests are
  in `backend/tests/paper_trading/test_stock_split_routes.py`.
- Implemented (#214): `OrderRefusedByLedgerResponse` with `rule`
  `sell_more_than_position`, `buy_more_than_cash`, or `ledger_not_started`
  (the ledger has no start yet, section 11.10). Buy example `detail`: "By
  hand has 10000.00 USD cash and open buy orders for 5000.00 USD. ATrade
  refuses a buy order for 5100.00 USD.". An IBKR error during the rule check
  (open orders, the last close, or the forex rate) is `502`. The `409` of
  `POST /api/paper-trading/orders` documents both response models.
- The backend tests of the owner ledger are in
  `backend/tests/paper_trading/test_owner_ledger.py`.
- The backend tests (`backend/tests/paper_trading/test_paper_orders.py`) go
  through these routes with the IBKR fake and real PostgreSQL.
- The Playwright test `frontend/e2e/paper_orders.spec.ts` sends an order
  through the modal, cancels it, checks the focus trap, Escape, and the focus
  return of the modal, checks the keyboard control of the side, order type,
  and time in force, and checks the scroll track of the order list. The e2e server has 30 open orders of forward test 42.
  `frontend/e2e/home_overview.spec.ts` checks the Owner column and the
  "Unattributed: 5" row of TEST05 (the e2e server starts the ledger with 5
  of the 10 shares). `frontend/e2e/instrument_order_panel.spec.ts` checks
  the ledger refusal notification.

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
  block them after the owner ledger started. The ledger start needs the cash
  in USD (section 11.10).
- The balance shows the base currency values and the rate, so the user sees
  what ATrade converted (section 11.7).

## 11.10 Owner ledger (Phase 3)

Sources: [Forward tests of multi-instrument strategies](https://github.com/Mano-Liaoyan/ATrade/issues/146),
[ADR 0007](../adr/0007-owner-ledger-for-shared-paper-account.md).

- Single-instrument forward tests, multi-instrument forward tests, and paper
  orders by hand run at the same time on the one paper account. They can
  trade the same instruments. They do not change the records of each other.
- An owner is a forward test, or "By hand". Each order, fill, position, and
  cash amount of the paper account belongs to one owner.
- The owner ledger is the record of the fills, positions, and cash of each
  owner in PostgreSQL. `paper_trading` owns its tables.
- For each instrument, the IBKR position minus the sum of the owner
  positions must be 0. When it is not 0, the paper trading page shows the
  difference as "Unattributed" (section 11.7).

Owners and their cash:

| Owner | Position | Cash |
|---|---|---|
| Forward test | The sum of its fills and its stock split adjustments. | Its allocated capital ([`forward_test.md`](forward_test.md) section 12.18), plus the cash of its fills, plus its cash in lieu. |
| "By hand" | The sum of the orders sent by hand, the positions at the ledger start, the transfers from stopped forward tests, and its stock split adjustments. | The capital of "By hand" is `NetLiquidation` (USD) minus the sum of the allocated capital of the running forward tests. |

Order rules. Version 1 is long only. Each order of each owner must pass all
3 rules:

1. A sell order must not be larger than the owner position minus the open
   sell orders of the owner on the instrument.
2. The amount of a buy order must not be larger than the owner cash minus
   the amount of the open buy orders of the owner.
3. An owner cannot sell short.

- When a rule fails, the strategy of a forward test gets `OrderDenied`
  ([`forward_test.md`](forward_test.md) section 12.19). An order by hand gets
  `409` with the reason (section 11.8).
- No owner uses margin. So the shared buying power of the paper account
  cannot go to one owner.

Records:

- The ATrade execution client writes each fill of a forward test, with the
  forward test as the owner.
- The fills of orders sent by hand belong to "By hand".
- Orders from outside ATrade (TWS, the IBKR website, the phone app) belong to
  "By hand". ATrade cannot refuse them.
- The positions of the paper account at the ledger start belong to
  "By hand".
- When a forward test stops, its positions and its remaining cash go to
  "By hand" ([`forward_test.md`](forward_test.md) section 12.6). The
  records of the forward test do not change.
- A stock split adds 1 "split adjustment" record for each owner that holds
  the instrument (section 11.11). It is not a fill.

Table (the names are choices of this document):

| Table | Columns |
|---|---|
| `owner_ledger_entry` | `id`, `owner_kind` (`by_hand`, `forward_test`), `forward_test_id` (null for `by_hand`), `entry_kind` (`fill`, `split_adjustment`, `transfer`, `ledger_start`), `time_utc`, `account`, `symbol`, `exchange`, `currency`, `quantity_change` (signed shares), `price` (null for `split_adjustment` and `transfer` of cash), `commission`, `cash_change`, `ibkr_execution_id` (unique when not null), `ibkr_order_id`, `stock_split_id` (null unless `split_adjustment`). |

- An insert of a fill has `ON CONFLICT DO NOTHING` on `ibkr_execution_id`, so
  a fill that ATrade reads again adds no row.
- Implemented (#214, migration `8d4f2a6c1e93`): `cash_change` is USD.
  `commission` is in the currency of the instrument. A cash row (the start
  cash) has `symbol` and `exchange` `null` and `quantity_change` `0`.
  `ibkr_execution_id` has a partial unique index (not null rows).
- Ledger start (#214): a migration cannot read IBKR. So the Web process
  writes the `ledger_start` rows of an account when it first reads the
  ledger after a passed check and the ledger of the account has no row: one
  row for each IBKR position (`quantity_change` is the position, `price` is
  the IBKR average cost) and one cash row with `balance.cash_usd`. All rows
  belong to "By hand". An advisory lock stops a second start. Without a USD
  cash value, the ledger does not start. Orders by hand then get `409` with
  the `rule` `ledger_not_started`.
- The average cost of an owner: a buy adds quantity times price to the
  cost, a sell takes away the same part of the cost as of the quantity.
- The position of an owner is the sum of `quantity_change`. The cost of the
  position follows from the fills and the stock split adjustments.

## 11.11 Stock splits in the owner ledger (Phase 3)

Sources: [How the owner ledger changes at a stock split](https://github.com/Mano-Liaoyan/ATrade/issues/149),
[ADR 0008](../adr/0008-stock-splits-from-ibkr-evidence.md).

[`forward_test.md`](forward_test.md) section 12.22 has the daily check and
the restart of the forward tests. [`market_data.md`](market_data.md)
section 8.13 has the stock split table and the change of the stored bars.

The ledger change. For each owner that holds the instrument:

1. New shares = old shares times the split ratio, rounded down to a whole
   number.
2. The total cost does not change. The new average cost is the old average
   cost divided by the split ratio.
3. Cash in lieu = the part of a new share below 1, times the last close
   before the ex-date, divided by the split ratio. It goes to the cash of the
   owner and to its realized profit.
4. The difference between the IBKR position and the sum of the owner
   positions goes to "By hand". The difference between the IBKR cash in lieu
   and the sum of the owner cash in lieu also goes to "By hand".

- So the sum of the owner positions always equals the IBKR position.
- A strategy never gets shares that it did not buy.
- "By hand" can get 1 more share, and its cash then goes down by the same
  value.
- One transaction writes all records of one stock split.

Examples:

| Stock split | Before | After |
|---|---|---|
| 3-for-2 (split ratio 1.5) | Forward test A 3 shares, forward test B 5 shares. Account 8 shares. | Account 12 shares. A 4 shares and cash in lieu for 0.5 share. B 7 shares and cash in lieu for 0.5 share. "By hand" 1 share. |
| 1-for-10 (split ratio 0.1) | A 15 shares, B 7 shares. Account 22 shares. | Account 2 shares and cash in lieu for 0.2 share. A 1 share and cash in lieu for 0.5 share. B 0 shares and cash in lieu for 0.7 share. "By hand" 1 share. |

The "Split check needed" state:

- An instrument goes to this state when:
  - only evidence A shows a ratio, and the IBKR position did not change
  - the IBKR position changed, and evidence A shows no ratio
  - the 2 ratios are not the same
  - the IBKR share count is not the share count of the ledger change above
  - the ratio is not a usual split ratio (a whole number, 1 divided by a
    whole number, or a ratio like 3/2)
- While an instrument is in this state, no owner can send an order on it.
  The strategy of a forward test gets `OrderDenied`. An order by hand gets
  `409` with the reason. Other instruments trade as usual.
- The paper trading page shows the state in the Positions table
  (section 11.7). The forward test page shows it in the header line
  ([`forward_test.md`](forward_test.md) section 12.16).
- "Apply split 4:1" writes the ledger change above
  (`POST /api/paper-trading/stock-splits/{id}/apply`).
- "Keep ledger" makes no ledger change
  (`POST /api/paper-trading/stock-splits/{id}/keep-ledger`). The difference
  stays as "Unattributed".
- Each button ends the state.

Table (the names are choices of this document):

| Table | Columns |
|---|---|
| `split_check` | `id`, `stock_split_id` (the stock split event of `market_data`), `symbol`, `exchange`, `currency`, `detected_ratio`, `evidence` (`bar_ratio_only`, `position_only`, `ratios_differ`, `share_count_differs`, `unusual_ratio`), `account_quantity_before`, `account_quantity_after`, `status` (`needed`, `applied`, `kept`), `created_at_utc`, `resolved_at_utc`. |

Implemented (#220, migration `f66ac656f66b`):

- `split_check` also has `account`, `ex_date_utc`, and `restarted_at_utc`.
  `stock_split_id` is `null` for a `position_only` check: no stock split row
  exists until "Apply split" writes one with the ex-date of the check (the
  check day). A partial unique index allows 1 `needed` row for each
  instrument of an account.
- The rules are in `paper_trading/stock_split_rules.py`
  (`calculate_split_adjustments()`, `find_split_evidence()`), the check of
  one instrument and the 2 buttons in `paper_trading/stock_split_ledger.py`
  (`StockSplitLedger`). The tests with the 2 examples above are in
  `backend/tests/paper_trading/test_stock_split_ledger.py` and
  `test_stock_split_check.py`.
- `account_quantity_before` is the sum of the owner positions (the ledger),
  `account_quantity_after` is the IBKR position of the check.
- The order of the rules: no evidence A and a changed position gives
  `position_only`. Evidence A and an unchanged position gives
  `bar_ratio_only`. An unusual ratio gives `unusual_ratio`. The IBKR position
  equal to the old shares times the ratio, rounded down, confirms the stock
  split. Else evidence B within 3% of evidence A gives
  `share_count_differs`, and any other value gives `ratios_differ`.
- A usual ratio, as a fraction with a denominator of at most 1000: the
  numerator is 1, or the denominator is 1, or the numerator is at most 20
  and the denominator at most 10 (for example 3/2 and 11/10).
- An instrument that no owner holds has no evidence B. Evidence A alone
  confirms its stock split (`bar_evidence`). The ledger does not change.
- The difference row of "By hand" (step 4) is a second `split_adjustment`
  row of "By hand", with the cash-in-lieu share price as `price`, so its
  average cost includes the shares it gets. The other split adjustment rows
  have no price and keep the total cost. A position of 0 shares has no cost.
- "Apply split" on a `ratios_differ` row with a smaller IBKR position can
  give "By hand" a negative position: the formula of step 4.

## 11.12 Limits of the owner ledger (Phase 3)

- Version 1 does not handle cash dividends. A cash dividend changes the
  paper account cash without a fill. The paper trading page shows it as an
  "Unattributed" difference. Cash dividends are in the "Not yet specified"
  list of the planning map.
- Spin-offs, mergers, symbol changes, and delistings are not handled. The
  page shows the difference as "Unattributed".
- Version 1 is long only. No owner sells short or uses margin.
- Nobody checked if IBKR refuses opposite orders of 2 owners on one
  instrument (self-trade prevention).

## 11.13 Left to the implementation

The decisions do not name these details. The implementation picks the
simplest option and records it in this document.

Decided (#214):

- The cash of "By hand" for rule 2 is the sum of its `cash_change` in USD:
  the account cash in USD at the ledger start, plus the cash of its fills
  (with the commission). A cash dividend changes the account cash, not the
  ledger, so it shows in `unattributed_cash_usd`. #215 adds the allocated
  capital (in this slice it is 0).
- The page gets the "Unattributed" cash as `unattributed_cash_usd`:
  `balance.cash_usd` (section 11.9) minus the sum of the cash of all owners.
  The page does not show it yet.
- The amount of a buy order for rule 2 is the quantity times the limit
  price. For a market order, the price is the close of the last daily bar of
  IBKR in the last 10 days. Open buy orders by hand count with their
  remaining quantity in the same way. Rule 2 does not include the
  commission.
- An instrument that is not in USD: the amount of rule 2 and the cash of a
  fill are converted to USD with the IBKR forex rate
  (`read_exchange_rate(currency, "USD")`). Without a rate, the order gets
  `502`, and the fill is written at a later read.
- The Web process records the fills of orders by hand from `reqExecutions`
  before each order by hand and each second while `/ws/paper-trading` is
  open (with the order list). A fill counts when it has the Web client ID,
  the checked account, and an IBKR order ID of a `manual_order` row, and
  its time is not before the ledger start (the positions at the ledger start
  have the older fills). `reqExecutions` returns only the fills of the
  current day (section 21), so a fill is lost when no page and no order by
  hand reads it on its day. It then shows as "Unattributed".
- Fills from outside ATrade are not written into the ledger. They show as
  "Unattributed". Whether `reqExecutions` returns the fills of other client
  IDs is not checked (section 21).
- Rule 3 (no short sale) is part of rule 1: the position of "By hand" is
  never below 0, so a sell larger than the position fails rule 1 with
  `sell_more_than_position`.

Decided (#220):

- ATrade does not read the IBKR cash in lieu. The IBKR cash in lieu of step 4
  is the part below 1 share of the old account position (the sum of the
  owner positions) times the split ratio, at the same share price as the
  owners. The share price is the last stored daily close before the ex-date
  divided by the split ratio. Without a stored daily bar, it is the last
  IBKR daily close, which IBKR adjusted already. The cash in lieu is
  converted to USD with the IBKR forex rate.
- The tolerance of the 2 ratios: the IBKR position must be the old position
  times the ratio, rounded down (the share count of the ledger change). A
  ratio of evidence B within 3% of evidence A (the step tolerance of
  evidence A, [`market_data.md`](market_data.md) section 8.14) that does not
  give this count is `share_count_differs`.
- "Apply split" writes the stock split with the confirmation `user_apply`
  and changes the stored bars in the same transaction as the ledger rows
  (`apply_stock_split_in_transaction()` of `market_data`). The worker sees
  the applied split check without `restarted_at_utc` at its next check
  (each minute), restarts the forward tests that got a split adjustment,
  and writes `restarted_at_utc`.
- "Keep ledger" changes neither the ledger nor the stored bars, and does not
  restart a forward test. A candidate of evidence A stays without a
  confirmation. The check does not check a stock split again that has a
  split check, and does not check an instrument again whose last kept split
  check has the same 2 quantities.

Decided (#215):

- The allocated capital is a ledger `transfer`. The start of a forward test
  writes 2 cash rows in the same transaction as the `forward_test` row:
  "By hand" `-allocated_capital_usd`, the forward test
  `+allocated_capital_usd`. So the cash of "By hand" for rule 2 is its
  ledger cash, which no longer holds the allocated capital, and the cash of
  a forward test is its allocated capital plus the cash of its fills. This
  is the simplest form of "the capital of By hand is `NetLiquidation` minus
  the allocated capital" (section 11.10) that keeps rule 2 a cash rule: the
  positions of "By hand" do not become buying power. The start runs the
  ledger start first. Without a ledger start, the start gets `409`.
- The stop transfer: when the worker writes `stopped` (or `failed` after a
  failed paper account check), it writes `transfer` rows in the same
  transaction. Each position of the forward test goes to "By hand" with its
  average cost as `price`, and the remaining cash goes to "By hand". The
  fills of the forward test stay. A second transfer moves nothing.
- Rules 1 and 2 of a forward test use the open orders of its client ID with
  the `orderRef` `FT<ID>`, the same amount rules as "By hand", and the
  label "Forward test <ID>" in the reason, for example "Forward test 7 has
  1001.00 USD cash and open buy orders for 0.00 USD. ATrade refuses a buy
  order for 1010.00 USD.".
- A forward test fill: `cash_change` is the signed amount with the
  commission, converted to USD with the IBKR forex rate. Without a rate,
  the fill is saved at a later read.

Still open:

- How ATrade gets the IBKR cash in lieu of a stock split.
- The tolerance when ATrade compares the 2 ratios of a stock split.
- Whether "Apply split" and "Keep ledger" also change the stored bars and
  restart the forward tests, and how the worker sees the result.
