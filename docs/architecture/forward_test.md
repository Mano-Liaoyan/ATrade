# Forward test

This document is section 12 of the architecture specification
([`docs/architecture.md`](../architecture.md)). It was moved to its own file
to keep the specification shorter than 1000 lines (section 18). Terms have
the meaning that [`GLOSSARY.md`](../../GLOSSARY.md) gives them.

Sources: [Forward test design](https://github.com/Mano-Liaoyan/ATrade/issues/41),
[Start and stop forward tests](https://github.com/Mano-Liaoyan/ATrade/issues/76),
[Forward test recovery and end time](https://github.com/Mano-Liaoyan/ATrade/issues/77),
[Forward test records and the comparison with a backtest](https://github.com/Mano-Liaoyan/ATrade/issues/78),
[Forward tests of multi-instrument strategies](https://github.com/Mano-Liaoyan/ATrade/issues/146),
[How the owner ledger changes at a stock split](https://github.com/Mano-Liaoyan/ATrade/issues/149),
[Scope of metrics and robustness checks](https://github.com/Mano-Liaoyan/ATrade/issues/137),
[Merge the terms and ADRs of the second decision batch](https://github.com/Mano-Liaoyan/ATrade/issues/151)
(Net profit uses the allocated capital).
ADRs: [0007 owner ledger](../adr/0007-owner-ledger-for-shared-paper-account.md),
[0008 stock splits](../adr/0008-stock-splits-from-ibkr-evidence.md),
[0003 one simulated venue per currency](../adr/0003-one-simulated-venue-per-currency.md).

The NautilusTrader facts in this section come from the `v2.0.0rc7` source and
documents. Nobody ran them.

### Implementation phases of this section

The planning map [Wayfinder: indicators, screens, and strategy help](https://github.com/Mano-Liaoyan/ATrade/issues/129)
adds work to this section in 3 phases. A part without a phase mark is the
current implementation and stays true.

| Phase | Parts of this section |
|---|---|
| Phase 1 | The new metrics on the forward test page (section 12.16). Net profit of a forward test (section 12.10). |
| Phase 2 | No change. The AI assistant never starts a forward test (section 12.11). |
| Phase 3 | The multi-instrument forward test (section 12.17). The owner ledger and the allocated capital (sections 12.2, 12.18). The ATrade execution client and data client (section 12.19). The bar fetcher (section 12.20). The quarterly universe (section 12.21). The stock split check (section 12.22). |

Until Phase 3 is done, the rules marked "until Phase 3" stay in force.

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
- Until Phase 3: a forward test does not use paper capital. It uses the real
  paper account balance and records the balance at start
  (`start_balance_usd`).
- Phase 3 (#146): a forward test does not use paper capital. The user types
  its allocated capital in USD at start (section 12.18). The forward test
  trades only with this amount and its own fills. The allocated capital
  replaces the balance at start in all records, metrics, and comparisons.
- Phase 3 (#146): the input "1 instrument" becomes a universe with 3 kinds,
  the same as the backtest form ([`backtest.md`](backtest.md)):
  - one instrument (`single`)
  - the top N instruments by trading value (`rule`), N 500 at most
  - the watchlist (`list`)
  A forward test with the kind `rule` or `list` is a multi-instrument forward
  test (section 12.17). It uses only the bar period 1 day.
- A forward test does not need a backtest first. The start form shows the
  metrics of the latest backtest of the strategy version, or "no backtest
  result".
- The strategy version is fixed at start. To use a new version, stop the
  forward test and start a new one.

## 12.2 One forward test per instrument (until Phase 3), then shared instruments

Until Phase 3:

- NautilusTrader reconciles by account, not by client ID. With two position
  sources on one instrument, NautilusTrader generates synthetic fills to align
  the positions. When it cannot align them, the start fails.
- So only 1 forward test can run on one instrument at a time.
- Paper orders by hand on that instrument are refused (section 11.3, [`paper_trading.md`](paper_trading.md)).
- Implementation (#76): a forward test "runs on" an instrument while it holds
  a client ID (`client_id IS NOT NULL`), because then it can have open orders
  and a position there. The instrument is `symbol` and `exchange`. A partial
  unique index (`forward_test_one_per_instrument`) is the second guard.

Phase 3 (#146, [ADR 0007](../adr/0007-owner-ledger-for-shared-paper-account.md)).
This replaces the rules above:

- Single-instrument forward tests, multi-instrument forward tests, and paper
  orders by hand run at the same time on the one paper account. They can
  trade the same instruments.
- Each order, fill, position, and cash amount belongs to one owner: a forward
  test, or "By hand". The owner ledger records them
  ([`paper_trading.md`](paper_trading.md) section 11.10).
- The paper account position of an instrument is the sum of the owner
  positions.
- The old conflict has 2 causes in `live_node_run.py`:
  - `external_order_instrument_ids=[instrument]` claims all external orders
    on the instrument, also the orders by hand.
  - The reconciliation aligns the strategy position with the account
    position by synthetic fills (`crates/live/src/execution/manager.rs`,
    `handle_external_order`, `adjust_mass_status_fills`).
- The LiveNode of a forward test uses the ATrade execution client
  (section 12.19), not the IB execution client. The execution client reports
  the owner position and the owner cash for reconciliation, not the account
  values.
- The migration drops the partial unique index
  `forward_test_one_per_instrument`. `find_forward_test_on_instrument()` and
  the `409` "already runs on" refusal of `POST /api/forward-tests` go away.
- The order rules of the owner ledger (long only) protect each owner from the
  other owners ([`paper_trading.md`](paper_trading.md) section 11.10).

## 12.3 Web and worker

- The forward test table has a `desired_state` column (`running` or
  `stopped`). The Web process writes only this column.
- Every 2 seconds, the worker compares `desired_state` with the actual state.
  It starts or stops child processes and writes the actual state back.
- Every 2 seconds, the Web process reads the actual state and pushes it on
  `/ws/forward-tests`.
- Phase 3 (#146, #149): the worker also runs 3 jobs. They are not child
  processes of a forward test.
  - The bar fetcher (section 12.20).
  - The quarterly universe calculation (section 12.21).
  - The daily stock split check (section 12.22).

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
- Phase 3 (#146): a multi-instrument forward test takes 1 ID of the same
  range, as a single-instrument forward test does. It counts toward the
  same limit of 4.
- Phase 3 (#146): the bar fetcher has 1 fixed client ID,
  `ATRADE_IBKR_BAR_FETCHER_CLIENT_ID` (default `20`). At start, the worker
  checks that this ID is not in the forward test range and is not equal to
  the Web client ID. When the check fails, the worker does not start and
  writes the reason. Implemented (#216): `Settings` makes the check, and
  `app/forward_test_worker.py` logs "The forward-test worker does not start"
  with the reason and exits with code 1.
- The reason for a separate fetcher ID: one client ID cannot have 2
  connections. The LiveNode of a forward test child already holds its client
  ID (section 12.15).

| Client ID | User |
|---|---|
| `1` | Web process |
| `10`–`13` | Forward test children |
| `20` | Bar fetcher (Phase 3) |
| `98`, `99` | `ibkr_paper` contract tests |

## 12.5 Paper account check

- Before each `LiveNode` start, including automatic restarts, the child
  process:
  1. Connects with `ib_async` and its own client ID.
  2. Calls `require_paper_account()`.
  3. Disconnects.
  4. Starts the `LiveNode` with the same client ID.
- The Web process does not repeat the check.
- The child passes `settings.ibkr_account_id` to the IB execution client
  `account_id`. Phase 3: the child passes it to the ATrade execution client
  (section 12.19) instead.
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
- Phase 3 (#146): the stop steps do not change. After the stop ends with the
  status `stopped`, the worker transfers the positions and the remaining cash
  of the forward test to "By hand" in the owner ledger
  ([`paper_trading.md`](paper_trading.md) section 11.10). The records of the
  forward test (fills, equity points) do not change. The user can then sell
  the positions with paper orders by hand.
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
- Phase 3 (#146): restart step 2 changes. The child does not reconcile
  with the account position. The ATrade execution client reports the owner
  position of each instrument from the owner ledger. NautilusTrader restores
  the strategy position from these reports. The child sets
  `external_order_instrument_ids` to the instruments of the forward test.
  Without it, the restored position belongs to the strategy `EXTERNAL`, not
  to the strategy (#213, `docs/architecture.md` section 21.1).
- Phase 3 (#146): a multi-instrument forward test gets 1 year of warm-up
  daily bars from the bar store (section 12.17). When the quarter changed
  during an interruption, the restarted strategy gets the members of the
  current quarter.
- Phase 3 (#149): the stock split check restarts the forward tests that trade
  an instrument after it changes the owner ledger for a stock split
  (section 12.22). This restart does not count toward the 3-crash limit.
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

Phase 3 changes (#146, #149):

- The ATrade execution client writes each fill of the forward test into the
  owner ledger ([`paper_trading.md`](paper_trading.md) section 11.10). The
  recorder no longer reads fills from `self.cache`. It still writes 1 equity
  point at the end of each bar.
- The equity is the sum of 4 parts:
  - the allocated capital
  - the cash of all fills of the forward test
  - the cash in lieu of its stock split adjustments
  - each position at the close of the bar The recorder does not read the IBKR
  `NetLiquidation`. Other positions and other currencies of the paper
  account do not change the equity.
- For a multi-instrument forward test, "each position" means each instrument
  that the forward test holds. The close is the daily close of that
  instrument in the bar store.
- The fill records get `symbol` and `exchange`, because a forward test can
  trade more than one instrument.
- A stock split adjustment is a ledger record, not a fill (section 12.22). The
  "Fills" table shows it as a row (section 12.16).
- The forward test routes read the fills of the forward test from the owner
  ledger. Whether `forward_test_fill` stays, and what happens to its old
  rows, is left to the implementation (section 12.24).

## 12.9 Order source

- The forward test sets `order_id_tag` to `FT<forward test ID>`.
- The IB execution client writes the `ClientOrderId` into `orderRef`. User code
  cannot change it.
- Phase 3 (#146): the ATrade execution client sends the orders. It also
  writes the `ClientOrderId` into `orderRef`, so the `orderRef` still holds
  `FT<ID>`. The order source rule below does not change.
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
- The comparison page uses the comparison view of section 9.5 ([`strategy.md`](strategy.md)): one key
  metric row for each test and both equity and drawdown curves on one chart.
- A fill table shows, for each bar, the fill price on each side and the
  difference.
- The chart marks interruptions in grey.
- Forward test metrics use the same metric functions that `backtest` exports.
- Phase 1 (#137): the forward test metrics include the new metrics of
  [`backtest.md`](backtest.md) section 10.4. They come from the same
  functions. A forward test has no in-sample and out-of-sample split, because
  a forward test is out-of-sample.
- Phase 1 (#151): the Net profit of a forward test is its final equity minus
  its start capital. Until Phase 3, the start capital is `start_balance_usd`.
  From Phase 3, it is the allocated capital.
- Phase 3 (#146): the same-period backtest uses:
  - the allocated capital as `paper_capital_usd`
  - for a multi-instrument forward test, the members that the forward test
    recorded for each quarter (`forward_test_universe_member`, section
    12.12). The backtest gets the universe source "forward test record"
    ([`backtest.md`](backtest.md)). So both tests have the same members, and
    a difference comes only from the fills and the bars.
- Phase 3: the `422` "no start balance" refusal goes away, because each new
  forward test has an allocated capital.
- Implementation (#78):
  - `POST /api/forward-tests/{id}/same-period-backtests` queues the backtest
    with `queue_backtest` of `backtest` (section 10.4). It records the
    backtest ID in `forward_test_same_period_backtest`, so the forward test
    page links to the comparison with each backtest of the same period. The period starts at
    `created_at_utc` and ends at `stopped_at_utc`, or now. The paper capital
    is `start_balance_usd`. `422` without a start balance, for each
    refusal of `check_backtest_request` (an empty period), and for an
    instrument that is not in USD: a forward test has no exchange rates, so
    its values are in the instrument currency and would not compare with a
    backtest in USD (`backtest.md` section 10.8). The
    backtest reads only saved bars: without saved bars of the period it
    fails with the message of section 10.
  - The comparison page `/forward-tests/{id}/comparison/{backtest_id}` reads
    `GET /api/forward-tests/{id}/comparison/{backtest_id}` every 2 seconds
    until the backtest has a final status. It is a workbench (spec #99,
    #109): the "Forward tests" side column, the comparison panel (header
    line with the backtest status, `ComparedKeyMetrics` and
    `EquityDrawdownChart` of `#lib/backtest`; no code diff: the same strategy
    version) over the Fills / Logs panel (the fill table, and the backtest
    error). The win rate of the forward test counts only the fills in the
    backtest period (the comparison route calculates it, #170).
  - Metrics: `calculate_metrics` with `start_balance_usd`, the range from
    the forward test start to its stop (or to now while it runs), the
    recorded equity points, and the recorded fills.
  - Decided (#170): the exposure counts the recorded equity points as the
    bars, because a forward test has no saved bars and the DataActor
    records one point at each bar end (section 12.8). The recorded fills
    go to `find_round_trips` with no change: `select_fills` gives
    `BacktestTrade` rows.
  - Decided (#170): the forward test metrics have the fields of the backtest
    `metrics` (backtest section 10.5, Phase 1 row) and `net_profit_usd`
    (the final equity minus `start_balance_usd`). They have no
    `split_metrics` and no `robustness`. The backtest summaries of the
    forward test routes have the same fields, and their `net_profit_usd`
    uses `paper_capital_usd`.
  - Decided (#170): in the comparison route, `win_rate_percent` of the
    forward test counts only the round trips that start and end in the
    backtest period (both ends included). The round trips come from all
    fills, so a position that opens before the backtest start does not
    change the pairs of the later fills. Without such a
    round trip it is null with the reason
    "No round trips in the backtest period". The other metrics use all
    fills. Decided (#168): the key metric rows show `win_rate_percent` and
    `sharpe_ratio` of the API, and the frontend has no win rate
    calculation.
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
    `EquityDrawdownChart` draws a grey column (a `HistogramSeries` on a hidden price
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
- Phase 2 (#140, #150): the AI assistant has no tool that starts or stops a
  forward test. Its tool allow list has no forward test route.

Phase 3 additions to the public entry (#146, #149). The names are choices of
this document. The implementation can change them.

| Name | Purpose |
|---|---|
| `OwnerLedgerExecutionClient`, `OwnerLedgerExecutionClientFactory(ledger_input, ledger, gateway)`, `OwnerLedgerInput` | The ATrade NautilusTrader execution client of section 12.19 (#213). `OwnerLedgerInput` has `forward_test_id`, `client_id`, `account_id`, `instruments`, and `fill_check_interval_seconds` (default 1). `gateway` is an `OrderGateway`: the order functions of the `ibkr` GatewayConnection. |
| `OwnerLedger`, `OwnerOrder`, `OwnerFill`, `OwnerPosition` | The owner ledger interface of the execution client (#213). |
| `BarStoreDataClient`, `BarStoreDataClientFactory(bar_store_input)`, `BarStoreInput` | The ATrade NautilusTrader data client of section 12.19 (#213). `BarStoreInput` has `database_url` and `instruments`. The factory keeps the created client in `client`, for `send_new_bars()`. |
| `add_atrade_clients(builder, data_client_factory, execution_client_factory)` | Adds both clients to a `LiveNodeBuilder` as the default route. Without a data client factory, it adds only the execution client (#213). |
| `BarFetcher(*, database_url, clock, open_gateway_connection, read_member_lists, sleep)` | The bar fetcher of section 12.20. `keep_fetching()` runs it in the worker. `fill_warm_up()` reads the warm-up before a start. |
| `ReadMemberLists` | The type of `read_member_lists`: it returns the members of each running multi-instrument forward test. |
| `QuarterlyUniverseJob(*, database_url, clock, databento_client)` | The quarterly universe calculation of section 12.21. |
| `StockSplitCheck(*, database_url, clock, gateway_connection)` | The daily stock split check of section 12.22. |
| `read_allocated_capital(*, database_url)` | The sum of the allocated capital of the forward tests that hold a client ID. `paper_trading` gets it from `app/web.py` for the "By hand" capital (section 11.10 of [`paper_trading.md`](paper_trading.md)). |

- Phase 3: `find_forward_test_on_instrument()` goes away with the rule of
  section 12.2.

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

Phase 3 table changes (#146). The column names are choices of this document.

| Table | Change |
|---|---|
| `forward_test` | Add `universe_kind` (`single`, `rule`, `list`), `universe_top_n` (null unless `rule`), and `allocated_capital_usd` (not null for a new row). `symbol`, `exchange`, and `currency` can be null (null unless `single`). Drop the partial unique index `forward_test_one_per_instrument`. `start_balance_usd` stays for the old rows. |
| `forward_test_universe_member` (new) | `forward_test_id`, `quarter_start_utc`, `symbol`, `exchange`, `currency`. Primary key `(forward_test_id, quarter_start_utc, symbol, exchange)`. `ON DELETE CASCADE` from `forward_test`. One row for each member that the forward test gave the strategy in that quarter. The same-period backtest reads it (section 12.10). |
| `quarterly_universe` (new) | `quarter_start_date`, `rank` (1 to 500), `symbol`, `exchange`, `average_trading_value_usd`, `window_end_date` (the last trading day of the 63-day window that the calculation used). Primary key `(quarter_start_date, rank)`. Section 12.21 writes it. |
| `quarterly_universe_run` (new) | `quarter_start_date` (primary key), `started_at_utc`, `ended_at_utc`, `window_end_date`, `status` (`running`, `done`, `failed`), `error_message`. One row for each calculation. |

- The watchlist kind (`list`) records the watchlist members at start in
  `forward_test_universe_member`. Whether a later change of the watchlist
  changes the members of a running forward test is left to the
  implementation (section 12.24).
- The owner ledger tables and the split check state belong to
  `paper_trading` ([`paper_trading.md`](paper_trading.md) sections 11.10 and
  11.11). The table of stock split events and the change of the stored bars
  are in [`market_data.md`](market_data.md) section 8.4.

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
| `GET /api/forward-tests/{id}` | `200` with `ForwardTestDetailResponse`, for the forward test page: `forward_test` (`ForwardTestResponse`), `metrics` (null without a start balance; the fields of section 12.10, #170), `equity_curve`, `fills` (`time_utc`, `side`, `quantity_shares`, `price_usd`, `commission_usd`, oldest first), and `same_period_backtests` (the backtest summary of the comparison route, newest first). `404` for an unknown ID. |
| `POST /api/forward-tests/{id}/stop` | `202`. Writes `desired_state = stopped`. `404` for an unknown ID. |
| `POST /api/forward-tests/{id}/same-period-backtests` | `201` with `{"backtest_id"}`: a queued backtest of the same period (section 12.10). `404` for an unknown ID. `422` without a start balance (`"The forward test has no start balance yet. The backtest uses it as the paper capital."`), for a currency that is not USD, or for an empty period. |
| `GET /api/forward-tests/{id}/comparison/{backtest_id}` | `200` with `ForwardTestComparisonResponse`: `forward_test`, `backtest` (`id`, `status`, `error_message`, `start_utc`, `end_utc`, `paper_capital_usd`, `metrics` or null), `forward_test_metrics` (null without a start balance; the fields of section 12.10, with the win rate in the backtest period, #170), `forward_test_equity_curve`, `backtest_equity_curve`, `fills` (`bar_end_utc`, `side`, quantity and price of each side or null, `price_difference_usd` or null), and `interruptions` (`start_utc`, `end_utc`). `404` for an unknown forward test or backtest. `422` when the backtest has another strategy version, instrument, or bar period. |
| `/ws/forward-tests` | `{"type": "forward_tests", "forward_tests": [...]}` at once and after each change. The server reads the table every 2 seconds, with a fixed number of database connections for the full list (not connections for each row). `{"type": "heartbeat"}` after 10 seconds without a change. The browser sends nothing. |

Phase 3 route changes (#146, #149). The field names, the new route path,
and the status codes of the new refusals are choices of this document.

| Route | Change |
|---|---|
| `POST /api/forward-tests` | `StartForwardTestRequest` gets `universe` (`kind`: `single`, `rule`, or `list`, then `symbol`, `exchange`, and `currency` for `single`, or `top_n` from 1 to 500 for `rule`) and `allocated_capital_usd` (decimal text, larger than 0). `422` for a `rule` or `list` universe with a bar period other than `1-DAY`, for `top_n` out of range, for an empty watchlist, or for an `allocated_capital_usd` that is not larger than 0. `409` with `StartRefusedResponse` (`detail`, `forward_test_id` null, `unallocated_usd`) when the allocated capital is larger than the unallocated amount, for example `"The allocated capital 30,000.00 USD is larger than the unallocated 21,250.00 USD."`. `409` when the paper account check did not pass or IBKR sent no `NetLiquidation` in USD, because ATrade cannot calculate the unallocated amount. The "already runs on" `409` goes away (section 12.2). |
| `GET /api/forward-tests/capital` (new) | `200` with `{"net_liquidation_usd", "allocated_usd", "unallocated_usd"}`. `allocated_usd` is the sum of `allocated_capital_usd` of the forward tests that hold a client ID. `unallocated_usd` is `net_liquidation_usd` minus `allocated_usd`. All 3 are `null` when the paper account check did not pass or no USD value is available. The start dialog reads it. |
| `GET /api/forward-tests`, `GET /api/forward-tests/{id}` | `ForwardTestResponse` gets `universe_kind`, `universe_top_n`, `allocated_capital_usd`, and `split_checks_needed` (a list of `symbol`, `exchange` of the instruments of the forward test in the "Split check needed" state). `ForwardTestDetailResponse` gets `instruments` (section 12.16) and `fills` rows with `symbol`, `exchange`, and `kind` (`fill` or `split_adjustment`). |
| `POST /api/forward-tests/{id}/same-period-backtests` | Uses `allocated_capital_usd` and the recorded members (section 12.10). |

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
   Phase 3: then the worker transfers the positions and the remaining cash
   of the forward test to "By hand" (section 12.6).
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
- Phase 3 (#146): the LiveNode has the ATrade execution client (section
  12.19) instead of the IB execution client. A multi-instrument forward test
  has the ATrade data client instead of the IB data client. Its warm-up bars
  come from the bar store, not from `read_historical_bars()` (section
  12.17). The instrument IDs are `SYMBOL.<primary exchange>`, for example
  `AAPL.NASDAQ`, as now. The single-instrument data client is left to the
  implementation (section 12.24).
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
  line shows the number, the strategy version (link to that version on the strategy page),
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
- Phase 1 (#137): the forward test page shows the key metrics in the order
  and with the functions of [`backtest.md`](backtest.md) section 10.6, because
  it uses the same `KeyMetricRow`. The Net profit uses the start capital of
  section 12.10. The page has no in-sample and out-of-sample split.
- Phase 3 (#146): changes of the start dialog. The layout is the layout of
  the backtest form ([`backtest.md`](backtest.md)).
  - "Instrument" becomes "Instruments" with 3 choices: one instrument, top N
    by trading value, and watchlist.
  - For top N and watchlist, the bar period list has only "1 day".
  - A "Capital (USD)" number input. Under it, the unallocated amount from
    `GET /api/forward-tests/capital`, for example
    "Unallocated: 61,250.00 USD". This line is data that the user needs to
    act, so rule one of the frontend design rules allows it.
  - When the capital is larger than the unallocated amount, the
    "Start forward test" button is disabled and the dialog says why, for
    example "Capital is larger than the unallocated 61,250.00 USD".
  - When the unallocated amount is not available, the button is disabled and
    the dialog gives the reason of the paper account check.
- Phase 3 (#146): changes of the forward test page. The layout is the layout
  of the backtest page. There is no new page.
  - The header line shows the universe name instead of the symbol for a
    multi-instrument forward test, for example "Top 500 by trading value" or
    "Watchlist (12)".
  - The header line shows the allocated capital, for example
    "Capital 20,000.00 USD".
  - The lower panel gets an "Instruments" tab (`ScrollRegion` "Instruments"),
    the same as the backtest page: symbol, fill count, Net profit (USD), and
    the number of quarters in the universe. Number columns are right aligned
    with tabular numbers.
  - The "Fills" table gets a "Symbol" column.
  - A stock split adjustment is a row of the "Fills" table (#149): "Side"
    shows the split, for example "Split 4:1". The quantity column shows the
    change of the share count. The price column is empty. The amount column
    shows the cash in lieu.
- Phase 3 (#149): when an instrument of the forward test is in the
  "Split check needed" state, the header line shows a warning icon, the
  words "Split check needed", and the instrument, for example
  "Split check needed: AAPL". The paper trading page has the actions
  ([`paper_trading.md`](paper_trading.md) section 11.7).
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
  checks the key metric row of each test, the interruption text, the fill
  table, and its
  scroll track. It also checks the key metrics, the chart, the Fills tab, and
  the Logs tab of the forward test page.


## 12.17 Multi-instrument forward test (Phase 3)

Source: [Forward tests of multi-instrument strategies](https://github.com/Mano-Liaoyan/ATrade/issues/146).

- A multi-instrument forward test runs 1 strategy version on a universe.
- The universe kind is `rule` (the top N instruments by trading value, N 500
  at most) or `list` (the watchlist). The kinds are the same as in the
  multi-instrument backtest ([`backtest.md`](backtest.md)).
- The bar period is 1 day only. Hourly bars are later work (section 12.23).
- Members:
  - `rule`: the first N ranks of the quarterly universe of the current
    quarter (section 12.21). A forward test that starts in the middle of a
    quarter uses the stored universe of that quarter.
  - `list`: the watchlist members at start.
- The platform gives the strategy only the members of the current quarter.
  At each quarter start, the platform tells the strategy the new members and
  gives it the bars of the new members. The mechanism is the same as in the
  multi-instrument backtest ([`backtest.md`](backtest.md)).
- The forward test records the members of each quarter in
  `forward_test_universe_member` (section 12.12).
- Instrument IDs are `SYMBOL.<primary exchange>`, for example `AAPL.NASDAQ`.
  This is the default of the IB adapter, and the paper contract test used
  it. The strategy uses only the instrument IDs that the platform gives. It
  does not write a venue in its code. The strategy templates and the rule
  builder generate code by this rule
  ([ADR 0003](../adr/0003-one-simulated-venue-per-currency.md)).
- Bars: the bar fetcher saves the daily bars of the members in `ibkr_bar`
  after each close (section 12.20). The ATrade data client reads them from
  the bar store and gives them to the strategy. The strategy uses `on_bar`
  as in a backtest (section 12.19).
- Warm-up: the warm-up of a multi-instrument forward test on daily bars is
  1 year, the same as the multi-instrument backtest. The reason: 12-1
  momentum and the distance to the 52-week high need about 252 daily bars.
  The old look-back of 1-day bars is 60 days
  (`backend/src/atrade/backtest/backtest_run.py`).
  - The child reads the warm-up bars from the bar store with the global
    source order (`ibkr_bar`, then `databento_bar`,
    [`market_data.md`](market_data.md)). It sends no request to IBKR. The
    cost is 0 USD.
  - Before the start, the bar fetcher reads the missing ranges from IBKR.
  - 500 instruments for 1 year are about 126,000 daily bars. The read time is
    not measured.
- The ATrade execution client checks each order against the owner ledger
  (section 12.19).
- The equity and the metrics are in USD (section 12.8).

## 12.18 Allocated capital (Phase 3)

Sources: [Forward tests of multi-instrument strategies](https://github.com/Mano-Liaoyan/ATrade/issues/146),
[ADR 0007](../adr/0007-owner-ledger-for-shared-paper-account.md).

- The user types the allocated capital in USD in the start dialog
  ("Capital (USD)").
- The sum of the allocated capital of the running forward tests must not be
  larger than the `NetLiquidation` of the paper account in USD
  ([`paper_trading.md`](paper_trading.md) section 11.9). A running forward
  test is a forward test that holds a client ID (section 12.2).
- When the new amount is larger than the unallocated amount, the start is
  refused. The refusal gives the unallocated amount (section 12.13).
- The unallocated amount is `NetLiquidation` (USD) minus the sum of the
  allocated capital. This is also the capital of "By hand".
- The allocated capital does not change while the forward test runs.
- The cash of a forward test owner is its allocated capital, plus the cash of
  its fills, plus its cash in lieu. The ATrade execution client reports this
  cash as the account state of the strategy. The strategy calculates its
  order quantities from this cash. The strategy code does not change.
- The allocated capital is the start capital of the equity curve, of the
  metrics, and of the Net profit (#151). It is the paper capital of the
  same-period backtest (section 12.10).
- No owner uses margin. So one owner cannot use the buying power of another
  owner.

## 12.19 ATrade execution client and data client (Phase 3)

Sources: [Forward tests of multi-instrument strategies](https://github.com/Mano-Liaoyan/ATrade/issues/146),
[ADR 0007](../adr/0007-owner-ledger-for-shared-paper-account.md).

ATrade writes its own NautilusTrader `ExecutionClient` and `DataClient` in
Python with `nautilus_trader.live.clients`. ATrade does not change the
NautilusTrader code and does not fork it.

Execution client (`OwnerLedgerExecutionClient`,
`backend/src/atrade/forward_test/owner_ledger_execution_client.py`):

- It implements `_submit_order`, `_cancel_order`, and the 4 reconciliation
  hooks, including `_generate_position_status_reports`
  (`docs/developer_guide/python_adapters.md` of NautilusTrader).
- It sends the orders with `ib_async` and the client ID of the forward test.
  The `orderRef` is `FT<ID>` (section 12.9).
- Before each order, it checks the owner ledger with the order rules of
  [`paper_trading.md`](paper_trading.md) section 11.10. When a rule fails,
  the strategy gets `OrderDenied` with the reason. ATrade sends nothing.
- An order on an instrument in the "Split check needed" state also gets
  `OrderDenied` ([`paper_trading.md`](paper_trading.md) section 11.11).
- It reports only the orders and the fills of its own client ID.
- It writes each fill into the owner ledger, with the forward test as the
  owner.
- For reconciliation, it reports the owner position of each instrument
  (`PositionStatusReport` with `quantity` and `avg_px_open`) and the owner
  cash (section 12.18). It does not report the account positions or the
  account cash.
- After a restart, NautilusTrader restores the strategy position from these
  reports. Thus the strategy knows its position and does not buy again.
  NautilusTrader 2.0.0rc7 makes an external order with an inferred fill
  from each report. The strategy gets the position only when its
  `external_order_instrument_ids` hold the instrument (section 12.7).
- Until #214 and #215, the owner ledger is the interface `OwnerLedger`
  (`backend/src/atrade/forward_test/owner_ledger.py`). The tests use the
  in-memory fake `backend/tests/fakes/owner_ledger.py`.
- Each order adds 1 PostgreSQL query. The time is not measured.

Data client (`BarStoreDataClient`,
`backend/src/atrade/forward_test/bar_store_data_client.py`):

- It implements `_subscribe_bars` and `_request_bars`.
- It gives the strategy the bars from the bar store, merged by the global
  source order as in a backtest (`market_data.md` section 8.7.2). The
  strategy uses `on_bar` and `request_bars` as before.
- A multi-instrument forward test uses it (section 12.17).

Rules for both clients:

- With its own Python clients, a LiveNode cannot use a database cache. ATrade
  does not use a database cache, so this limit has no effect.
- `nautilus_trader.live.clients` is new in NautilusTrader 2.0. Each
  NautilusTrader upgrade must run the tests of both clients.
- Before the implementation, a LiveNode test must run both clients with a
  fake IBKR connection: send an order, fill it, restart, and check the
  strategy position. The test also gets a stock split step (section 12.22).
  The tests are `backend/tests/forward_test/test_atrade_clients_live_node.py`
  and `backend/tests/forward_test/test_bar_store_data_client.py` (#213).
  `add_atrade_clients()` adds both clients to a `LiveNodeBuilder`. The child
  process still uses the IB clients until #215.

## 12.20 Bar fetcher (Phase 3)

Source: [Forward tests of multi-instrument strategies](https://github.com/Mano-Liaoyan/ATrade/issues/146).

- The `forward-test` worker runs 1 bar fetcher.
- It uses the fixed client ID `ATRADE_IBKR_BAR_FETCHER_CLIENT_ID` (default
  `20`, section 12.4).
- After each daily close, it reads the daily bars of the members of all
  running multi-instrument forward tests. It reads each instrument one time,
  also when more than one forward test has it.
- It uses `reqHistoricalData` without `keepUpToDate`
  (`GatewayConnection.read_historical_bars()`). It saves the bars and their
  ranges in `ibkr_bar` with `save_received_bars()` of `market_data`.
- Before a multi-instrument forward test starts, it reads the missing ranges
  of the 1-year warm-up (section 12.17).
- Each bar read from IBKR also reads 1 stored daily bar, for the stock split
  evidence A ([`market_data.md`](market_data.md) section 8.4,
  [ADR 0008](../adr/0008-stock-splits-from-ibkr-evidence.md)). So each
  instrument can need 1 more request each day.
- The reason for the fetcher: the IB adapter subscribes to 1-hour and 1-day
  bars with `reqHistoricalData` and `keepUpToDate`. 500 members need 500 open
  requests. IBKR allows 50 open historical data requests at most.
- The requests are 0.5 seconds apart ([`market_data.md`](market_data.md)
  section 8.4). So 500 instruments take about 250 seconds at least. The real
  time is not measured.
- The cost is 0 USD.
- Implementation (#216): `BarFetcher` in `forward_test/bar_fetcher.py`.
  - `fetch_when_due()`: the daily read. It reads the union of the member
    lists, each instrument 1 time, for the year before the current UTC day.
  - `fill_warm_up(instruments, start_utc)`: the warm-up fill before a start.
    It reads the year before the UTC day of `start_utc`.
    No start path calls it before the multi-instrument forward test
    ([#217](https://github.com/Mano-Liaoyan/ATrade/issues/217)).
  - Both ask IBKR only for the ranges that no bar source in the global
    source order saved (`read_unsaved_ranges` of `market_data`). So the daily
    read asks only for the days after the last saved day. A day that is not
    complete (section 8.4 of [`market_data.md`](market_data.md)) is not read.
  - The fetcher waits 0.5 seconds before each request after the first one.
  - The member lists come from a function argument. Until the
    multi-instrument forward test
    ([#217](https://github.com/Mano-Liaoyan/ATrade/issues/217)), the worker
    passes a function that returns no list.
  - Stock split evidence A comes later with the `market_data` read path
    ([#196](https://github.com/Mano-Liaoyan/ATrade/issues/196)).

## 12.21 Quarterly universe (Phase 3)

Sources: [Forward tests of multi-instrument strategies](https://github.com/Mano-Liaoyan/ATrade/issues/146),
[Decision on the screen data sources](https://github.com/Mano-Liaoyan/ATrade/issues/141).

- The rule is the rule of the backtest universe. On the first trading day of
  each quarter, the universe is the top 500 common stocks (no ETFs). The
  rank is the average daily trading value of the previous 63 trading days. The trading value is the
  close times the volume.
- The data is Databento EQUS.SUMMARY `ohlcv-1d` for all symbols. The backtest
  universe uses the same data source after 2024-07, so the ranks agree. IBKR
  is not used, because 5000 candidate instruments need about 5000 IBKR
  requests (about 42 minutes), and IBKR filters the volume of historical
  bars.
- The worker downloads the data and calculates the universe at 06:00 ET on
  the first trading day of the quarter.
- When the daily bar of the previous trading day is not available yet, the
  worker tries again every 15 minutes until 09:00 ET.
- When the bar is still missing at 09:00 ET, the worker uses the 63 trading
  days that end 1 trading day earlier. It records the actual end date in
  `window_end_date`.
- The new universe goes to the strategies before the market opens.
- The worker stores each result in `quarterly_universe` and each calculation
  in `quarterly_universe_run` (section 12.12).
- Cost: about 1.30 USD for each quarter. On 2026-10-30, `metadata.get_cost`
  gave 1.23 USD to 1.36 USD for one quarter. After the free credit, the
  Databento account pays.
- The setting `DATABENTO_API_KEY` holds the key (`.env.example`).
- The download time and the calculation time are not measured. The estimate
  is a few minutes.

## 12.22 Stock split check (Phase 3)

Sources: [How the owner ledger changes at a stock split](https://github.com/Mano-Liaoyan/ATrade/issues/149),
[ADR 0008](../adr/0008-stock-splits-from-ibkr-evidence.md).

This section has the check and the restart of the forward tests.
[`paper_trading.md`](paper_trading.md) section 11.11 has the ledger change
and the "Split check needed" state. [`market_data.md`](market_data.md)
section 8.4 has the stock split table and the change of the stored bars.

- Scope: forward splits, reverse splits, and bonus issues, for US and HK
  instruments. A bonus issue uses its ratio, for example 1.1 for 1 new share
  for each 10 shares.
- The check runs before the market opens on each trading day: 08:00 ET for
  US instruments, 08:30 HKT for HK instruments.
- It checks each instrument that has a paper account position or an owner
  position.
- Evidence A: the ratio between a stored daily close and the new IBKR
  `TRADES` close of the same day. IBKR adjusts `TRADES` bars for stock splits,
  not for dividends.
- Evidence B: the ratio between the paper account position and the sum of
  the owner positions.
- When both ratios agree, the stock split is confirmed. An instrument
  without a position has only evidence A. `market_data` finds it when it
  reads bars ([`market_data.md`](market_data.md) section 8.4).
- When the evidence is not complete, the check tries again every 15 minutes
  until 5 minutes before the market opens.
- After a confirmed stock split:
  1. Cancel the open orders of all owners on the instrument. IBKR also
     cancels GTC orders at a stock split, but only as best effort.
  2. Change the owner ledger in one transaction
     ([`paper_trading.md`](paper_trading.md) section 11.11).
  3. Restart the child processes of the forward tests that trade the
     instrument. The restart cancels their open orders (section 12.7) and
     restores the strategy positions from the new ledger.
- The restart avoids a position report with a new quantity in a running
  LiveNode. Nobody checked what a running LiveNode does with it.
- The restart time is not measured. The estimate is 1 minute or less for
  each forward test.
- When the 2 ratios do not agree, the instrument goes to the
  "Split check needed" state ([`paper_trading.md`](paper_trading.md)
  section 11.11).
- The `forward-test` worker runs the check, because the check restarts
  forward test children. This is a choice of this document.
- The cost is 0 USD.

## 12.23 Limits and later work

- Version 1 does not handle cash dividends. A cash dividend changes the
  paper account cash without a fill. The paper trading page shows the
  difference as "Unattributed" ([`paper_trading.md`](paper_trading.md)
  section 11.12). Cash dividends are in the "Not yet specified" list of the
  planning map.
- Spin-offs, mergers, symbol changes, and delistings are not handled. The
  paper trading page shows the difference as "Unattributed".
- The owner ledger is long only (section 12.18).
- Later work: a multi-instrument forward test on hourly bars. First measure
  the time that the bar fetcher needs to read the hourly bars of 500
  instruments. 500 instruments need 500 requests each hour.

## 12.24 Left to the implementation

The decisions do not name these details. The implementation picks the
simplest option and records it in this document.

- The data client of a single-instrument forward test. The IB data client of
  the adapter, or the ATrade data client. One client ID cannot have 2
  connections. The ATrade execution client holds an `ib_async` connection
  with the client ID of the forward test. Check if the IB data client can
  share the client ID with it before this choice.
- How the ATrade data client gets the new daily bars after the bar fetcher
  saved them.
- Decided (#198): the platform tells the strategy the new members at a
  quarter start with NautilusTrader custom data, as the multi-instrument
  backtest does ([`backtest.md`](backtest.md) section 10.10.8): one
  `CustomData` with `DataType("UniverseUpdate")`, which the strategy gets in
  `on_data`. Not checked in a LiveNode: how the ATrade data client sends it.
- Decided (#216): the bar fetcher reads the bars at the first check after
  00:30 UTC of each UTC day. A daily bar starts at 00:00 UTC of its trading
  date, so the bar of the last US trading day is complete then. The worker
  checks every 5 minutes. When IB Gateway is not reachable, or the
  connection is lost during the read, the fetcher logs the reason and reads
  again at the next check. The worker does not crash. A failed request of
  one instrument on a working connection is logged and not saved, so the
  next daily read asks IBKR again.
- Decided (#216): the bar fetcher and the daily bar update of `web`
  ([Screen page prototype](https://github.com/Mano-Liaoyan/ATrade/issues/145))
  are 2 jobs. They run in different processes with different client IDs.
- The status code of a `rule` start when no universe of the current quarter
  is stored, and what the calculation does without `DATABENTO_API_KEY`.
- How ATrade maps a Databento symbol to the IBKR primary exchange.
- The trading day calendar for "first trading day of the quarter" and
  "before the market opens".
- Whether the downloaded EQUS.SUMMARY bars go into `databento_bar`.
- Which capability owns `quarterly_universe`. The screen page also uses the
  universe of the current quarter.
- Whether a change of the watchlist changes the members of a running
  `list` forward test.
- Whether `forward_test_fill` stays as a copy of the ledger fills, and the
  migration of the old rows and of `start_balance_usd`.
- Whether a stock split restart opens an interruption.
- What the stock split check does when IB Gateway is not reachable until
  5 minutes before the open.
- How the stock split check cancels the orders of other client IDs. IBKR lets
  a client cancel only its own orders. The forward test restart cancels the
  forward test orders. The Web client can cancel the orders by hand.
- Market orders and limit orders that a strategy sends after the daily close.
  Check how IBKR handles a DAY order that ATrade sends outside the trading
  hours.
