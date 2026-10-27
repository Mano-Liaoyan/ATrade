# Forward test

This document is section 12 of the architecture specification
([`docs/architecture.md`](../architecture.md)). It was moved to its own file
to keep the specification shorter than 1000 lines (section 18). Terms have
the meaning that [`GLOSSARY.md`](../../GLOSSARY.md) gives them.

Sources: [Forward test design](https://github.com/Mano-Liaoyan/ATrade/issues/41),
[Start and stop forward tests](https://github.com/Mano-Liaoyan/ATrade/issues/76).

The NautilusTrader facts in this section come from the `v2.0.0rc7` source and
documents. Nobody ran them.

## 12.1 Input and process

- Each forward test has 1 child process. The process has 1 `LiveNode`,
  1 user `Strategy`, and 1 client ID.
- Input: a strategy version, 1 instrument, 1 bar type, and an optional end
  time. The start time is always "now".
- Without an end time, the forward test runs until the user stops it.
- The end time is a date and a time. The browser shows it in the local time
  zone. The database stores UTC. The end time cannot change while the forward
  test runs.
- At the end time, the worker stops the forward test with the steps of
  section 12.6.
- The bar type must use a period that IB live bars support. Backtests do not
  have this limit. The supported periods are:
  - 1, 5, 15, or 30 seconds
  - 1, 2, 3, 5, 10, 15, 20, or 30 minutes
  - 1, 2, 3, 4, or 8 hours
  - 1 day, 1 week, or 1 month
- A forward test does not use paper capital. It uses the real paper account
  balance and records the balance at start.
- A forward test does not need a backtest first. The start form shows the
  metrics of the latest backtest of the strategy version, or "no backtest
  result".
- The strategy version is fixed at start. To use a new version, stop the
  forward test and start a new one.

## 12.2 One forward test per instrument

- NautilusTrader reconciles by account, not by client ID. With two position
  sources on one instrument, NautilusTrader generates synthetic fills to align
  the positions. When it cannot align them, the start fails.
- So only 1 forward test can run on one instrument at a time.
- Paper orders by hand on that instrument are refused (section 11.3, [`paper_trading.md`](paper_trading.md)).
- Implementation (#76): a forward test "runs on" an instrument while it holds
  a client ID (`client_id IS NOT NULL`), because then it can have open orders
  and a position there. The instrument is `symbol` and `exchange`. A partial
  unique index (`forward_test_one_per_instrument`) is the second guard.

## 12.3 Web and worker

- The forward test table has a `desired_state` column (`running` or
  `stopped`). The Web process writes only this column.
- Every 2 seconds, the worker compares `desired_state` with the actual state.
  It starts or stops child processes and writes the actual state back.
- Every 2 seconds, the Web process reads the actual state and pushes it on
  `/ws/forward-tests`.

## 12.4 Client IDs

- The forward test client ID range is in `settings`. The default is `10–13`.
- The range size is the limit of forward tests that run at the same time
  (default 4). There is no other limit.
- At start, one transaction takes the lowest free ID in the range. A unique
  constraint prevents two forward tests from getting the same ID.
- A forward test keeps its ID while it runs, restarts, or has the status "stop
  failed". The ID becomes free after the orders are cancelled and the process
  ends.
- When no ID is free, the start is refused. The UI shows "limit of running
  forward tests reached".

## 12.5 Paper account check

- Before each `LiveNode` start, including automatic restarts, the child
  process:
  1. Connects with `ib_async` and its own client ID.
  2. Calls `require_paper_account()`.
  3. Disconnects.
  4. Starts the `LiveNode` with the same client ID.
- The Web process does not repeat the check.
- The child passes `settings.ibkr_account_id` to the IB execution client
  `account_id`.
- When the check fails, the status is "failed". There is no retry.
- When the Gateway is not reachable, the child retries every 30 seconds. The
  UI shows "waiting for IB Gateway". This does not count toward the 3-crash
  limit (section 12.7).

## 12.6 Stop

1. The child stops the `LiveNode`.
2. The child connects with `ib_async` and the same client ID.
3. The child reads the open orders of this client ID with `reqOpenOrders`.
4. The child cancels each order and waits for the confirmation.
5. The child exits.

- Positions stay open. The user handles them by hand.
- Do not use `manage_stop`. It closes positions. `LiveNode.stop()` does not
  cancel orders.
- When a cancellation fails, the status is "stop failed". The client ID stays
  taken. The worker retries the cancellation.

## 12.7 Recovery after restart

- Daily IB Gateway restart: NautilusTrader reconnects and subscribes to bars
  again. When the IB execution client is disconnected for more than 5 minutes,
  the child exits. The worker waits for the Gateway (section 12.5) and starts
  it again. This does not count toward the 3-crash limit.
- Other stops are a restart of the `forward-test` service, a server restart,
  or a child crash. After each of them, the worker restarts the forward test.
  It uses the same client ID and the same strategy version.
- After 3 crashes in a row, the status is "failed". The worker stops the
  restarts.
- Restart steps:
  1. Cancel all open orders of this client ID (section 12.6). This prevents
     duplicate orders.
  2. Start the `LiveNode`. Set `external_order_instrument_ids` and
     `reconciliation_instrument_ids` to the instrument. The account position
     on this instrument belongs to this strategy (section 12.2).
  3. The strategy indicators start from zero. NautilusTrader does not save
     strategy state without Redis.
- An event table records the start and the end of each interruption.

## 12.8 Records

- A platform `DataActor` subscribes to the same bar type.
- At the end of each bar, the actor reads `self.cache`. It appends new fills
  (unique by `trade_id`) and one equity snapshot row to the forward test
  tables.
- Reasons:
  - A Python `DataActor` cannot subscribe to order and fill events. Only a
    `Strategy` gets them.
  - Do not use `PostgresCacheConfig`. Its tables belong to NautilusTrader and
    can change in each release candidate.
  - Do not write a `Strategy` base class. The readability rules forbid our own
    inheritance.
- The current state of open orders still comes from IBKR.

## 12.9 Order source

- The forward test sets `order_id_tag` to `FT<forward test ID>`.
- The IB execution client writes the `ClientOrderId` into `orderRef`. User code
  cannot change it.
- `foundation/order_ref.py` holds the format rule. `forward_test` writes it.
  `paper_trading` reads it.
  - `format_forward_test_order_tag(forward_test_id)` returns `FT<ID>`.
  - `read_order_source(order_ref)` splits the `orderRef` at `-`. A part
    `FT<digits>` gives the source "forward test <digits>". Each other
    `orderRef` gives the source "by hand".
  - Orders by hand from ATrade have the `orderRef` `ATRADE-BY-HAND`
    (`MANUAL_ORDER_REF`) (#75).
- The frontend changes the ID into the forward test name in `routes/`.

## 12.10 Comparison with a backtest

- The forward test page has a "backtest the same period" button. It creates a
  normal backtest with:
  - the same strategy version, instrument, and bar type
  - the period from the forward test start to its end, or to now while it runs
  - `paper_capital_usd` equal to the balance at forward test start
- The comparison page uses the comparison view of section 9.5 ([`strategy.md`](strategy.md)): the metric
  table and both equity curves on one chart.
- A fill table shows, for each bar, the fill price on each side and the
  difference.
- The chart marks interruptions in grey.
- Forward test metrics use the same metric functions that `backtest` exports.

## 12.11 The `forward_test` module (#76)

The public entry `atrade.forward_test` exports:

| Name | Purpose |
|---|---|
| `create_forward_test_router(*, database_url, clock, client_ids)` | The routes of section 12.13 and `/ws/forward-tests`. `client_ids` is the range from `settings`. |
| `find_forward_test_on_instrument(*, database_url, instrument)` | The forward test that holds a client ID on the instrument, with a label like `Forward test 3 (Trend v2)`, or `None`. `app/web.py` gives it to `paper_trading` (section 6.2). |
| `ForwardTestWorker(*, database_url, clock, start_child)` | The worker loop of section 12.14. `compare_states()` is one comparison. `keep_comparing()` runs it every 2 seconds. |
| `ChildMode`, `ForwardTestChild`, `StartForwardTestChild` | The child modes `run` and `cancel_orders`, the child protocol (`read_exit_code()`, `request_stop()`), and the start function type `(forward_test_id, mode) -> child`. Tests and the e2e server pass a fake. |
| `run_forward_test_child(*, settings, forward_test_id, mode, ibkr_access, stop_requested)` | The body of the child process (section 12.15). Returns the exit code. |
| `IbkrAccess`, `LiveNodeInput`, `run_live_node` | `IbkrAccess` holds `open_gateway_connection(client_id)` and `run_live_node(input, stop_requested)`. `run_live_node` is the real LiveNode run. |
| `PAPER_CHECK_FAILED_EXIT_CODE` | `3`. The exit code of a child whose paper account check failed. |
| `FORWARD_TEST_SOCKET_MESSAGE_MODELS` | The models of `/ws/forward-tests` for the OpenAPI document. |

- Entry points: `app/forward_test_worker.py` (Compose service
  `forward-test`) runs the worker with a start function that runs
  `python -m atrade.app.forward_test_process <ID> <run|cancel_orders>`. The
  stop request is `SIGTERM`. The child gets the environment of the worker.
  The `forward-test` service has no IBKR user name or password.
- The child loads the strategy code with `load_strategy_classes()` of
  `strategy` (section 9). `backtest` uses the same function.

## 12.12 Table

`forward_test`: `id`, `strategy_version_id` (not null, foreign key without
`ON DELETE`), `symbol`, `exchange`, `currency`, `bar_period`,
`desired_state` (`running`, `stopped`), `status`, `client_id` (`UNIQUE`,
null when free), `start_balance_usd`, `error_message`, `created_at_utc`,
`stopped_at_utc`. Migration `3e7a1c5d9b76_forward_test_create_table.py`.

| Status | Meaning |
|---|---|
| `starting` | The Web process inserted the row. The worker did not start a child yet. |
| `running` | A `run` child runs. |
| `stopping` | The worker sent the stop request, or a `cancel_orders` child runs. |
| `stopped` | The orders are cancelled and the child ended. The client ID is free. |
| `stop_failed` | A cancel failed. The client ID stays taken. The next comparison starts a `cancel_orders` child again. |
| `failed` | The paper account check failed (client ID free, no retry), or the child ended without a stop request (client ID taken until a stop cancels the orders). |

- Writers: the Web process inserts the row (`desired_state = running`,
  `status = starting`, the client ID) and after that writes only
  `desired_state`. The worker writes `status`, `client_id`, and
  `stopped_at_utc`. The child writes `start_balance_usd` (the
  `NetLiquidation` in USD after the paper account check, only the first
  value) and `error_message`.
- The start takes the client ID in one transaction:
  `LOCK TABLE forward_test IN SHARE ROW EXCLUSIVE MODE`, then the instrument
  check, then the lowest ID of the range that no row holds.
- Until #77, a child that ends without a stop request fails the forward test
  (no automatic restart). There is no "waiting for IB Gateway" status and no
  event table yet. When IB Gateway is not reachable at the start, the child
  writes "IB Gateway is not reachable: ..." and ends with exit code 3, like a
  failed paper account check: the connection is a condition of the check
  (section 11.2), and the child sent no order. A new worker (a restart of the `forward-test` service)
  starts a `run` child again for each row with `desired_state = running` and
  `status` `starting` or `running`, with the same client ID. The cancel of
  the old orders before that start is #77.

## 12.13 Routes and `/ws/forward-tests`

| Route | Behavior |
|---|---|
| `POST /api/forward-tests` | Body `StartForwardTestRequest`: `strategy_version_id`, `symbol`, `exchange`, `currency`, `bar_period`. `201` with `ForwardTestResponse`. `409` with `StartRefusedResponse` (`detail`, `forward_test_id`): `"limit of running forward tests reached"` (`forward_test_id` null), or `"Forward test 3 (Trend v2) already runs on AAPL / NASDAQ."`. `422` for a missing strategy version or a bar period that IB live bars do not support. |
| `GET /api/forward-tests` | `200` with the list of `ForwardTestResponse`, newest first: the row of section 12.12 plus `strategy_id`, `strategy_name`, `version_number`. |
| `POST /api/forward-tests/{id}/stop` | `202`. Writes `desired_state = stopped`. `404` for an unknown ID. |
| `/ws/forward-tests` | `{"type": "forward_tests", "forward_tests": [...]}` at once and after each change. The server reads the table every 2 seconds. `{"type": "heartbeat"}` after 10 seconds without a change. The browser sends nothing. |

- All periods of `BarPeriod` (1, 5, 15, 30 minutes, 1 hour, 1 day) are IB
  live bar periods. `LIVE_BAR_PERIODS` in `http_routes.py` and
  `isLiveBarPeriod()` in the frontend hold the rule of section 12.1.

## 12.14 Worker comparison

Each comparison reads the rows that are not done. A row is done when it is
`stopped`, or `failed` without a client ID. For each row:

1. A child of the row ended: the worker writes the result. A stop (a
   `cancel_orders` child, or a `run` child after the stop request) with exit
   code 0 is `stopped` and frees the client ID. A stop with another exit
   code is `stop_failed`. Exit code 3 of a `run` child is `failed` and frees
   the client ID. Each other end of a `run` child is `failed` and keeps the
   client ID.
2. No child, `desired_state = running`, status `starting` or `running`: the
   worker starts a `run` child and writes `running`.
3. No child, `desired_state = stopped`, a client ID: the worker starts a
   `cancel_orders` child and writes `stopping`.
4. A `run` child, `desired_state = stopped`: the worker sends the stop
   request one time and writes `stopping`.

## 12.15 Child process

- `run`: connect with `ib_async` and the client ID of the row, call
  `require_paper_account()`, read the balance, disconnect, then
  `run_live_node()` with the same client ID until `SIGTERM`. Then the stop
  steps of section 12.6 and exit code 0.
- `cancel_orders`: only the stop steps 2 to 5 of section 12.6.
- The stop steps use `GatewayConnection.read_own_open_orders()`
  (`reqOpenOrders`) and `cancel_order_and_wait(order_id)` (section 7). A
  missing confirmation after 10 seconds gives exit code 1, so the worker
  writes `stop_failed`.
- The LiveNode has 1 IB data client and 1 IB execution client. Both use the
  client ID of the forward test. The execution client gets
  `account_id = settings.ibkr_account_id` (the checked account). The
  instrument provider loads only `SYMBOL.EXCHANGE`, and
  `reconciliation_instrument_ids` is that instrument. The bar type is
  `SYMBOL.EXCHANGE-<bar period>-LAST-EXTERNAL`.
- The strategy config gets `order_id_tag = FT<ID>` and
  `external_order_instrument_ids = [instrument]` through
  `StrategyConfig.__new__`, and `instrument_id` and `bar_type` through the
  `__init__` of the user config class (section 9.2). The reason: the user
  `__init__` passes other keywords to `object.__init__`, which refuses them.
- The stop request stops the LiveNode with `LiveNode.handle().stop()`. A CI
  test runs the real LiveNode without IB Gateway and stops it while it waits
  for the connection (`tests/forward_test/test_live_node_run.py`).

## 12.16 Frontend and tests

- `#lib/forward_test`: the HTTP calls, `readForwardTestsMessage()`, and
  `ForwardTestList.svelte` (`ScrollRegion` "Forward tests", a "Stop" button
  while `desired_state` is `running` and the row holds a client ID).
- The page `/forward-tests` (nav link "Forward tests") has the start form
  (strategy, strategy version, symbol, exchange, currency, and a bar period
  from the IB live bar periods), the metrics of the latest finished backtest
  of the selected strategy version or "no backtest result", and the live
  list. A refused start shows the `detail` text.
- Backend tests (`backend/tests/forward_test/`): the routes, the worker with
  real PostgreSQL and the fake start function
  (`tests/fakes/forward_test_child.py`), the child body with the IBKR fake
  and a fake LiveNode run, and the real LiveNode stop without a Gateway.
- `test_forward_test_paper_contract.py` (`ibkr_paper`, by hand): a real
  LiveNode sends a buy limit order for 1 AAPL at 1.00 USD. The Web side
  (`reqAllOpenOrders`, client ID 98) sees it with the forward test ID from
  `orderRef`. After the stop, the order is cancelled. It needs
  `ATRADE_TEST_DATABASE_URL`, `.env`, and a reachable Gateway. It skips
  without them.
- `backend/tests/e2e_server.py` runs the worker in the same process with
  fake children that stop at once, and adds 30 stopped forward tests. The
  Playwright test `frontend/e2e/forward_test.spec.ts` starts a forward test,
  sees "Running", sees the refusal of a paper order by hand on its
  instrument, stops it, and checks the scroll track of the list.

