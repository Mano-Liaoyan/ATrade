# Paper trading

This document is section 11 of the architecture specification
([`docs/architecture.md`](../architecture.md)). It was moved to its own file
to keep the specification shorter than 1000 lines (section 18). Terms have
the meaning that [`GLOSSARY.md`](../../GLOSSARY.md) gives them.

Sources: [Order module design](https://github.com/Mano-Liaoyan/ATrade/issues/40),
[Paper account check and account panel](https://github.com/Mano-Liaoyan/ATrade/issues/74).

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
  orders by hand for that instrument. It shows which forward test blocks it.
- Positions, balance, and order status go to the browser on
  `/ws/paper-trading`.

## 11.4 Order records and order list

- IBKR is the only source of order status.
- `paper_trading` stores only the paper orders that ATrade sent by hand: time,
  instrument, side, quantity, order type, price, IBKR order ID. It does not
  store status.
- The order list uses `reqAllOpenOrders`. It shows all open orders, including
  forward test orders.
- The list marks the source of each order: "by hand" or "forward test 42". The
  source comes from `orderRef` (section 12.9).
- Only orders sent by hand have a cancel button. To cancel forward test orders,
  stop the forward test.
- Filled orders sent by hand show data from the local table and from IBKR.
- Positions and balance belong to the account, not to a client ID.

## 11.5 The `paper_trading` module

The public entry `atrade.paper_trading` exports:

| Name | Purpose |
|---|---|
| `require_paper_account(*, settings, gateway_connection)` | Runs the 4 conditions of section 11.2 on the given connection. Returns the paper account number. Raises `PaperAccountCheckError` (a `PermissionError`) when a condition fails or the connection is not there. A forward test child passes its own connection. |
| `PaperAccountCheck` | The result: `status` (`disconnected`, `passed`, `failed`), `message` (the reason of the failure), `actual_accounts`, `expected_account`. |
| `PaperAccountMonitor` | The check result of the Web process in memory, the balance, and the positions. |
| `fetch_paper_capital_usd(paper_account_monitor)` | The `NetLiquidation` value in USD of the paper account after a passed check. Otherwise `settings.local_paper_capital_usd`. |
| `create_paper_trading_router(*, paper_account_monitor)` | The router of `/ws/paper-trading` and `GET /api/paper-trading/paper-capital`. |

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
  `TotalCashValue` account values in USD. ib_async keeps them and the
  portfolio up to date, because it subscribes to the account updates of the
  only managed account.
- `app/web.py` creates one monitor. The FastAPI lifespan runs
  `keep_checking()` every 0.5 seconds, so that a failed check reaches the log
  also when no browser is open. Each read also runs the check when needed.

## 11.6 `/ws/paper-trading`

| Message | When |
|---|---|
| `{"type": "account", "check": {...}, "balance": {...} \| null, "positions": [...]}` | At once after the socket opens, and after each change. The server compares the state every 0.25 seconds. |
| `{"type": "heartbeat"}` | After 10 seconds without another message. |

- `check` has the fields of `PaperAccountCheck`.
- `balance` has `net_liquidation_usd` and `cash_usd`. It is `null` when the
  check did not pass.
- Each position has `symbol`, `security_type`, `exchange`, `currency`,
  `quantity`, `average_cost`, `market_price`, `market_value`,
  `unrealized_pnl`. The list is empty when the check did not pass.
- Amounts and quantities are decimal text, for example `"101234.50"`.
- The browser sends nothing. The server reads the socket only to see when the
  browser leaves.

## 11.7 Account panel

- The home page shows the account panel (`lib/paper_trading/`) with a
  `PAPER` mark, the check result, the balance, and the positions.
- When the check fails, the panel shows the reason, the actual account, and
  the expected account.
- The panel uses `foundation/live_socket` for reconnection and heartbeat, and
  `foundation/scroll_region` for the position table (section 13). The table
  text wraps, so the table does not overflow to the side.
