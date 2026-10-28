# Forward test

This document is section 12 of the architecture specification
([`docs/architecture.md`](../architecture.md)). It was moved to its own file
to keep the specification shorter than 1000 lines (section 18). Terms have
the meaning that [`GLOSSARY.md`](../../GLOSSARY.md) gives them.

Sources: [Forward test design](https://github.com/Mano-Liaoyan/ATrade/issues/41),
[Start and stop forward tests](https://github.com/Mano-Liaoyan/ATrade/issues/76),
[Forward test recovery and end time](https://github.com/Mano-Liaoyan/ATrade/issues/77),
[Forward test records and the comparison with a backtest](https://github.com/Mano-Liaoyan/ATrade/issues/78).

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
- Implementation (#77): `POST /api/forward-tests` takes `end_time_utc`, a
  time with a time zone. The browser converts the local time of its
  `datetime-local` input to UTC. An end time that is not later than now is
  refused with `422`. No route changes the end time. The worker treats
  `now >= end_time_utc` like `desired_state = stopped`
  (`ForwardTestRow.is_stop_wanted()`). It does not write `desired_state`.
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
- Implementation (#77): "not reachable" is a `GatewayRequestError` during
  the connection or the paper account check. The child writes the status
  `waiting_for_gateway`, opens a `gateway` interruption, and waits 30 seconds
  or until the stop request. A stop request during the wait runs the stop
  steps. Without IB Gateway they fail, so the status becomes `stop_failed`
  and the worker retries the cancel.

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

Implementation (#77):

- A crash is the end of a `run` child without a stop request, with an exit
  code other than 3 (paper account check) or 4 (IB Gateway). The worker adds
  1 to `crash_count`, opens a `crash` interruption, and writes `starting`.
  The next comparison starts a new `run` child. At `crash_count = 3` the
  status is `failed`, the client ID stays taken, and there is no restart.
  The Stop button then runs a `cancel_orders` child.
- "In a row": a child that ran 10 minutes or more before its crash starts a
  new count (`crash_count = 1`). The worker keeps the child start time in
  memory.
- Each `run` child cancels the open orders of its client ID after the paper
  account check and before the `LiveNode` start (step 1), on the same
  connection. A failed cancel there ends the child with exit code 1, which
  is a crash.
- IB Gateway lost: the child opens a TCP connection to the Gateway port every
  30 seconds while the `LiveNode` runs. After 5 minutes without a
  connection, it stops the `LiveNode` and exits with code 4
  (`GATEWAY_UNREACHABLE_EXIT_CODE`) without the stop steps. The NautilusTrader
  2.0.0rc7 `LiveNode` does not show the connection state of its IB execution
  client to Python, so the probe is the replacement. The worker writes
  `waiting_for_gateway`, opens a `gateway` interruption, and starts a new
  `run` child, which waits for IB Gateway (section 12.5). `crash_count` does
  not change.
- A new worker (a restart of the `forward-test` service or of the server)
  finds rows with `status = running` and no child. It opens a
  `worker_restart` interruption and starts a `run` child. The interruption
  starts at the time the new worker sees the row, because the time of the
  old worker end is not known.
- The child ends the open interruption and writes `running` when it starts
  the `LiveNode`. A stop (`write_end`) also ends it.
- A crash message in `error_message` is the current state only until the
  forward test runs again or stops. The child clears `error_message` when it
  starts the `LiveNode`, and a stop that ends with the status `stopped`
  clears it. The `crash` interruptions keep the history. The list and the
  forward test page show the crash count only when the status is not
  `stopped`.

## 12.8 Records

- A platform `DataActor` subscribes to the same bar type.
- At the end of each bar, the actor first saves the bar in the bar store of
  `market_data` (`save_received_bars_blocking()`), with the bar range as a
  saved range. Thus a same-period backtest (section 12.10) finds the bars of
  the forward test period. The save is idempotent: a restart or a bar that
  the bar chart saved before adds no row. A bar whose start is not a bar
  period start is not saved. A failed save logs a warning and does not stop
  the forward test or the records.
- Then the actor reads `self.cache`. It appends new fills
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
- Implementation (#78): `forward_test_recorder.py` (`ForwardTestRecorder`,
  1 level of `DataActor`, the C3 exception). `run_live_node` adds it with
  `LiveNode.add_actor` next to the strategy, on the bar type of the strategy.
  - `on_start` reads the fills that earlier runs recorded, so a restart
    continues with them. Then it subscribes to the bars.
  - `on_bar` reads the fills of the instrument from
    `self.cache.orders(instrument_id=...)` (each `OrderFilled` event) and
    keeps the ones with a new `trade_id`. Then it calculates one equity point
    with `calculate_equity_curve` of `backtest` for this one bar: the start
    balance, plus the cash of all recorded fills up to the bar end, plus the
    position at the bar close. It writes the new fills and the point in one
    transaction (synchronous `psycopg`, one connection for each bar).
  - The bar end is the bar `ts_event`. The backtest engine gives the actor a
    bar before the strategy, so a fill at a bar close counts in the equity
    from the next bar on.
  - The equity starts at `start_balance_usd`, not at the paper account
    balance. Other positions of the paper account do not change it. The
    start balance is `NetLiquidation` converted to USD (section 11.9 of
    `paper_trading.md`). A child that has no `NetLiquidation` value in USD at
    the first start, for example a EUR account without an exchange rate,
    writes "The paper account has no NetLiquidation value in USD." and the
    reason of the balance, and ends with exit code 3 before the `LiveNode`
    starts.
- Tables (migration `3e7a1c5d9b78_forward_test_create_record_tables.py`,
  `ON DELETE CASCADE` from `forward_test`). Each insert has
  `ON CONFLICT DO NOTHING`, so a restart that reads a fill or a bar again
  adds no row.

| Table | Columns |
|---|---|
| `forward_test_fill` | `forward_test_id`, `trade_id` (NautilusTrader `TradeId`), `time_utc`, `side`, `quantity_shares`, `price_usd`, `commission_usd`. Primary key `(forward_test_id, trade_id)`. |
| `forward_test_equity_point` | `forward_test_id`, `time_utc` (bar end), `equity_usd`. Primary key `(forward_test_id, time_utc)`. |

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
- Implementation (#78):
  - `POST /api/forward-tests/{id}/same-period-backtests` queues the backtest
    with `queue_backtest` of `backtest` (section 10.4). It records the
    backtest ID in `forward_test_same_period_backtest`, so the forward test
    page links to the comparison with each backtest of the same period. The period starts at
    `created_at_utc` and ends at `stopped_at_utc`, or now. The paper capital
    is `start_balance_usd`. `422` without a start balance, and for each
    refusal of `check_backtest_request` (not USD, an empty period). The
    backtest reads only saved bars: without saved bars of the period it
    fails with the message of section 10.
  - The comparison page `/forward-tests/{id}/comparison/{backtest_id}` reads
    `GET /api/forward-tests/{id}/comparison/{backtest_id}` every 2 seconds
    until the backtest has a final status. It shows the backtest status, the
    `ComparisonView` of `#lib/backtest` (no code diff: the same strategy
    version), and the fill table.
  - Metrics: `calculate_metrics` with `start_balance_usd`, the recorded
    equity points, and the number of recorded fills.
  - Fill table: a fill belongs to the last bar end (of both equity curves) at
    or before its time, so a live fill just after a bar close and the
    backtest fill at that bar close are in one row. One row for each bar end
    and side. More fills in one row give the total quantity and the average
    price weighted by quantity (4 decimal places). The difference is the
    forward test price minus the backtest price, only when both sides have a
    fill. A limit order that fills inside the next bar in the backtest can
    be one row later than the live fill.
  - Grey marks: the interruptions of `forward_test_interruption` (section
    12.7, #77). An interruption that still lasts ends at the stop, or now.
    `EquityChart` draws a grey column (a `HistogramSeries` on a hidden price
    scale, below the curves) at each bar end after the interruption start
    up to its end, and lists each interruption as text under the chart.

## 12.11 The `forward_test` module (#76)

The public entry `atrade.forward_test` exports:

| Name | Purpose |
|---|---|
| `create_forward_test_router(*, database_url, clock, client_ids)` | The routes of section 12.13 and `/ws/forward-tests`. `client_ids` is the range from `settings`. |
| `find_forward_test_on_instrument(*, database_url, instrument)` | The forward test that holds a client ID on the instrument, with a label like `Forward test 3 (Trend v2)`, or `None`. `app/web.py` gives it to `paper_trading` (section 6.2). |
| `ForwardTestWorker(*, database_url, clock, start_child)` | The worker loop of section 12.14. `compare_states()` is one comparison. `keep_comparing()` runs it every 2 seconds. |
| `ChildMode`, `ForwardTestChild`, `StartForwardTestChild` | The child modes `run` and `cancel_orders`, the child protocol (`read_exit_code()`, `request_stop()`), and the start function type `(forward_test_id, mode) -> child`. Tests and the e2e server pass a fake. |
| `run_forward_test_child(*, settings, forward_test_id, mode, ibkr_access, stop_requested)` | The body of the child process (section 12.15). Returns the exit code. |
| `IbkrAccess`, `LiveNodeInput`, `LiveNodeEnd`, `run_live_node`, `GatewayWatch` | `IbkrAccess` holds `open_gateway_connection(client_id)`, `run_live_node(input, stop_requested)`, `clock` (default the system clock), and `gateway_retry_seconds` (default 30). `run_live_node` is the real LiveNode run. It takes an optional `gateway_watch` (`GatewayWatch(check_interval_seconds=30, lost_after_seconds=300)`). |
| `PAPER_CHECK_FAILED_EXIT_CODE`, `GATEWAY_UNREACHABLE_EXIT_CODE` | `3`: the paper account check failed. `4`: IB Gateway was lost for more than 5 minutes (section 12.7). |
| `FORWARD_TEST_SOCKET_MESSAGE_MODELS` | The models of `/ws/forward-tests` for the OpenAPI document. |
| `create_forward_test_comparison_router(*, database_url, clock)` | The two comparison routes of section 12.13 (#78). `app/web.py` adds it after `create_forward_test_router`. |
| `ForwardTestRecorder`, `RecorderInput` | The records DataActor of section 12.8 (#78). `RecorderInput` has `database_url`, `forward_test_id`, `instrument` (the key of the saved bars), `instrument_id`, `bar_type`, `bar_period`, and `start_balance_usd`. `LiveNodeInput` has `database_url` and `start_balance_usd` for it. |

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
`stopped_at_utc`, `end_time_utc` (null when there is no end time),
`crash_count` (the crashes in a row, default 0). Migrations
`3e7a1c5d9b76_forward_test_create_table.py` and
`3e7a1c5d9b77_forward_test_recovery_and_end_time.py`.

`forward_test_same_period_backtest`: `forward_test_id`, `backtest_id`
(both foreign keys with `ON DELETE CASCADE`, primary key on both). One row
for each "Backtest the same period". Migration
`3e7a1c5d9b79_forward_test_create_same_period_backtest.py`.

`forward_test_interruption` (#77): `id`, `forward_test_id`, `reason`
(`crash`, `gateway`, `worker_restart`), `started_at_utc`, `ended_at_utc`
(null while the interruption lasts). A partial unique index allows only one
open interruption for each forward test. A second start of an open
interruption does nothing.

| Status | Meaning |
|---|---|
| `starting` | The Web process inserted the row, or a crash happened. The worker did not start a child yet. |
| `running` | A `run` child runs. |
| `waiting_for_gateway` | IB Gateway is not reachable. The child retries every 30 seconds, or the worker starts a new child after a lost Gateway. The client ID stays taken. |
| `stopping` | The worker sent the stop request, or a `cancel_orders` child runs. |
| `stopped` | The orders are cancelled and the child ended. The client ID is free. |
| `stop_failed` | A cancel failed. The client ID stays taken. The next comparison starts a `cancel_orders` child again. |
| `failed` | The paper account check failed (client ID free, no retry), or 3 crashes in a row (client ID taken until a stop cancels the orders). |

- Writers: the Web process inserts the row (`desired_state = running`,
  `status = starting`, the client ID, `end_time_utc`) and after that writes
  only `desired_state`. The worker writes `status`, `client_id`,
  `crash_count`, `stopped_at_utc`, and the `crash` and `worker_restart`
  interruptions. The child writes `start_balance_usd` (the
  `NetLiquidation` converted to USD after the paper account check, only the first
  value), `error_message`, the `gateway` interruptions, and two statuses:
  `waiting_for_gateway` (only from `starting`, `running`, or
  `waiting_for_gateway`) and `running` at the `LiveNode` start (only from
  `starting`, `running`, or `waiting_for_gateway`; it also clears
  `error_message`, section 12.7). The conditions keep a stop status of
  the worker.
- The start takes the client ID in one transaction:
  `LOCK TABLE forward_test IN SHARE ROW EXCLUSIVE MODE`, then the instrument
  check, then the lowest ID of the range that no row holds.

## 12.13 Routes and `/ws/forward-tests`

| Route | Behavior |
|---|---|
| `POST /api/forward-tests` | Body `StartForwardTestRequest`: `strategy_version_id`, `symbol`, `exchange`, `currency`, `bar_period`, optional `end_time_utc` (with a time zone, later than now). `201` with `ForwardTestResponse`. `409` with `StartRefusedResponse` (`detail`, `forward_test_id`): `"limit of running forward tests reached"` (`forward_test_id` null), or `"Forward test 3 (Trend v2) already runs on AAPL / NASDAQ."`. `422` for a missing strategy version, a bar period that IB live bars do not support, or an end time that is not later than now or has no time zone. |
| `GET /api/forward-tests` | `200` with the list of `ForwardTestResponse`, newest first: the row of section 12.12 plus `strategy_id`, `strategy_name`, `version_number`, and `interruptions` (`reason`, `started_at_utc`, `ended_at_utc`, oldest first). |
| `GET /api/forward-tests/{id}` | `200` with `ForwardTestDetailResponse`, for the forward test page: `forward_test` (`ForwardTestResponse`), `metrics` (null without a start balance), `equity_curve`, `fills` (`time_utc`, `side`, `quantity_shares`, `price_usd`, `commission_usd`, oldest first), and `same_period_backtests` (the backtest summary of the comparison route, newest first). `404` for an unknown ID. |
| `POST /api/forward-tests/{id}/stop` | `202`. Writes `desired_state = stopped`. `404` for an unknown ID. |
| `POST /api/forward-tests/{id}/same-period-backtests` | `201` with `{"backtest_id"}`: a queued backtest of the same period (section 12.10). `404` for an unknown ID. `422` without a start balance (`"The forward test has no start balance yet. The backtest uses it as the paper capital."`), for a currency that is not USD, or for an empty period. |
| `GET /api/forward-tests/{id}/comparison/{backtest_id}` | `200` with `ForwardTestComparisonResponse`: `forward_test`, `backtest` (`id`, `status`, `error_message`, `start_utc`, `end_utc`, `paper_capital_usd`, `metrics` or null), `forward_test_metrics` (null without a start balance), `forward_test_equity_curve`, `backtest_equity_curve`, `fills` (`bar_end_utc`, `side`, quantity and price of each side or null, `price_difference_usd` or null), and `interruptions` (`start_utc`, `end_utc`). `404` for an unknown forward test or backtest. `422` when the backtest has another strategy version, instrument, or bar period. |
| `/ws/forward-tests` | `{"type": "forward_tests", "forward_tests": [...]}` at once and after each change. The server reads the table every 2 seconds. `{"type": "heartbeat"}` after 10 seconds without a change. The browser sends nothing. |

- All periods of `BarPeriod` (1, 5, 15, 30 minutes, 1 hour, 1 day) are IB
  live bar periods. `LIVE_BAR_PERIODS` in `http_routes.py` and
  `isLiveBarPeriod()` in the frontend hold the rule of section 12.1.

## 12.14 Worker comparison

Each comparison reads the rows that are not done. A row is done when it is
`stopped`, or `failed` without a client ID. For each row:

"Stop wanted" is `desired_state = stopped`, or an end time that is not later
than the worker clock.

1. A child of the row ended: the worker writes the result. A stop (a
   `cancel_orders` child, or a `run` child after the stop request) with exit
   code 0 is `stopped`, frees the client ID, and ends an open interruption.
   A stop with another exit code is `stop_failed`. Exit code 3 of a `run`
   child is `failed` and frees the client ID. Exit code 4 is
   `waiting_for_gateway`. Each other end of a `run` child is a crash
   (section 12.7).
2. No child, stop wanted, a client ID: the worker starts a `cancel_orders`
   child and writes `stopping`.
3. No child, stop not wanted, status `starting`, `running`, or
   `waiting_for_gateway`: the worker starts a `run` child. For `running` it
   first opens a `worker_restart` interruption. It writes `running`, except
   for `waiting_for_gateway`, which stays until the child starts the
   `LiveNode`.
4. A `run` child, stop wanted: the worker sends the stop request one time
   and writes `stopping`.

## 12.15 Child process

- `run`: connect with `ib_async` and the client ID of the row, call
  `require_paper_account()`, read the balance, cancel the open orders of the
  client ID, disconnect, then `run_live_node()` with the same client ID until
  `SIGTERM`. Then the stop steps of section 12.6 and exit code 0. When IB
  Gateway is not reachable, it waits (section 12.5). `run_live_node()`
  returns `"ended"` or `"gateway_lost"` (`LiveNodeEnd`). `"gateway_lost"`
  without a stop request gives exit code 4.
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
- Warm-up bars: after the cancel of the old orders, on the same connection,
  the child reads the bars of `find_look_back_length(bar_period)` of
  `backtest` (the backtest look-back, 7 days at least) before the start of
  the current bar, with `GatewayConnection.read_historical_bars()`. That
  function splits the range into requests of the IBKR step size of the bar
  period (1 day for 1-minute bars, `ibkr/historical_bars.py`). A failed read
  logs a warning and gives no warm-up bars. The forward test still starts.
- The child saves the warm-up bars and their range in the bar store with
  `save_received_bars()` of `market_data`, so a same-period backtest can use
  them. A failed save logs a warning. The forward test still starts.
- `run_live_node()` writes the warm-up bars to a catalog with
  `write_look_back_catalog()` of `backtest` and builds the node with
  `LiveNodeBuilder.from_config()` and `LiveNodeConfig(catalogs=[...])`. The
  catalog says that it holds all times, so the data engine answers each
  `request_bars` of the strategy from the catalog, as in a backtest
  (section 10.3.1 of `backtest.md`). A request that starts earlier gets only
  the warm-up bars. The reason: the IB data client of NautilusTrader
  2.0.0rc7 splits a long request into a part in whole days and a rest in
  seconds (`calculate_duration_segments`). For `now - 7 days` with 1-minute
  bars, IBKR refuses the request (error 321), and the strategy gets no bars.
  The live bars of `subscribe_bars` still come from the IB data client.
- The stop request stops the LiveNode with `LiveNode.handle().stop()`. A CI
  test runs the real LiveNode without IB Gateway and stops it while it waits
  for the connection (`tests/forward_test/test_live_node_run.py`).

## 12.16 Frontend and tests

- `#lib/forward_test`: the HTTP calls, `readForwardTestsMessage()`,
  `ForwardTestsOnInstrumentsFeed` (the one `/ws/forward-tests` feed of a page:
  `forwardTests`, `onInstruments`, `isConnected`), and
  `listForwardTestEvents()` (the events of the Logs tab).
  `routes/forward-tests/ForwardTestList.svelte` (`ScrollRegion` "Forward test
  list": number, strategy version, symbol, and status; the open forward test
  is the selected row) is the list of the page. `FillComparisonTable.svelte` (`ScrollRegion` "Compared fills") is the
  fill table of section 12.10 (#78). `ForwardTestFillTable.svelte`
  (`ScrollRegion` "Fills") is the Fills tab of the forward test page.
- The forward test page `/forward-tests/{id}` is a workbench like the
  backtest page (spec #99, #105). `/forward-tests` opens the newest forward
  test. The side column "Forward tests" has the list from `/ws/forward-tests`
  and the "New forward test" button. The dialog has the start form (strategy,
  strategy version, symbol, exchange, currency, a bar period from the IB live
  bar periods, an optional end time in the local time zone) and the metrics of
  the latest finished backtest of the selected strategy version or "no
  backtest result". A refused start shows the `detail` text. A started
  forward test opens at once.
- The page reads `GET /api/forward-tests/{id}` every 2 seconds. The header
  line shows the number, the strategy version (link to the strategy page),
  the symbol (link to the instrument page), the bar period, the status, the
  crash count when it is not 0 and the status is not `stopped`, the red
  "Stop forward test" button while `canStop()`, and the "Backtest the same
  period" button (disabled without a start balance; the page starts the
  backtest and opens the comparison page). Below: `KeyMetricRow` and
  `EquityDrawdownChart` of `backtest` (the same metrics and chart as the
  backtest page; the start balance is the start capital, the fills are the
  trades). The chart lists the interruptions under it and marks grey only the
  recorded bar ends inside one: a forward test has no bar end in an
  interruption, so the grey is mostly absent. An interruption that still lasts
  ends at the stop, or now. Without metrics, the panel shows the
  status. The Fills / Comparison / Logs panel: the fills; each backtest of the
  same period with its number (a link with the name "Compare with backtest
  #N"), status, period, and return; the current error and the events (start, interruptions and
  their ends, stop, or the planned stop at the end time) in UTC.
- Tables show a bar period as "1 min" or "1 day", an amount with thousands
  separators ("98,765.40"), and a UTC time as "2026-01-02 03:04:05 UTC"
  (`#lib/foundation/value_format`, `#lib/foundation/time_format`). A column
  name breaks only between words. A long cell value ends with an ellipsis in
  the list.
- Backend tests (`backend/tests/forward_test/`): the routes, the worker with
  real PostgreSQL, the fixed clock, and the fake start function
  (`tests/fakes/forward_test_child.py`) (restarts, the 3-crash limit, the end
  time, `stop_failed` retries, interruptions), the child body with the IBKR
  fake and a fake LiveNode run (the wait for IB Gateway, the cancel before
  the restart), and the real LiveNode without a Gateway (the stop request,
  and `"gateway_lost"` with a short `GatewayWatch`).
- The list shows the status ("Waiting for IB Gateway", "Stop failed",
  "Failed").
- `test_forward_test_paper_contract.py` (`ibkr_paper`, by hand): a real
  LiveNode sends a buy limit order for 1 AAPL at 1.00 USD. The Web side
  (`reqAllOpenOrders`, client ID 98) sees it with the forward test ID from
  `orderRef`. After the stop, the order is cancelled. It needs
  `ATRADE_TEST_DATABASE_URL`, `.env`, and a reachable Gateway. It skips
  without them. A second contract test (#77) runs the worker with real child
  processes, kills the first child with `SIGKILL`, and checks that the
  restart keeps client ID 10 and cancels the old order, and that the stop
  cancels the new one.
- `backend/tests/e2e_server.py` runs the worker in the same process with
  fake children that stop at once, and adds 30 stopped forward tests. The
  Playwright test `frontend/e2e/forward_test.spec.ts` starts a forward test
  in the dialog, sees "Running", sees the refusal of a paper order by hand on
  its instrument, stops it from the header line, and checks the scroll track
  of the list.
- #78: `test_forward_test_recorder.py` runs `ForwardTestRecorder` in the
  NautilusTrader backtest engine with the bar count test strategy and 10
  bars of `tests/backtest/bars/`, and asserts the exact rows of both record
  tables (and no new row after a second run).
  `test_forward_test_comparison.py` covers both routes. The e2e server adds
  the stopped forward test "E2E compared forward test" (FTCMP / ARCA,
  1-DAY) with a start balance, 40 fills, equity points, 1 interruption, and
  the saved bars of its period. `frontend/e2e/forward_test_comparison.spec.ts`
  clicks "Backtest the same period", waits for the real backtest child, and
  checks the metric table, the interruption text, the fill table, and its
  scroll track. It also checks the key metrics, the chart, the Fills tab, and
  the Logs tab of the forward test page.

