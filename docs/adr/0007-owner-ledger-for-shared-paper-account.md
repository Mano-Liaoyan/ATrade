# An owner ledger lets forward tests and orders by hand share one paper account

More than one forward test (single-instrument and universe) and paper orders
by hand run at the same time on the one paper account, also on the same
instruments. ATrade keeps an owner ledger in PostgreSQL: each order, fill,
position, and cash amount belongs to one owner (a forward test, or "by hand").
The paper account position of an instrument is the sum of the owner
positions. Each forward test gets allocated capital at its start and trades
only with it. ATrade writes its own NautilusTrader `ExecutionClient` and
`DataClient` in Python (`nautilus_trader.live.clients`). The execution client
sends the orders with `ib_async` and the client ID of the forward test, checks
the ledger before each order, and reports the owner positions and cash, not
the account values, for reconciliation. The first version is long only: an
owner cannot sell more than it holds or buy for more than its cash. Decision:
[#146](https://github.com/Mano-Liaoyan/ATrade/issues/146), 2026-10-30. This
replaces the rules "one running forward test for each instrument" and "orders
by hand are refused for that instrument" of `docs/architecture/forward_test.md`
section 12.2 and `docs/architecture/paper_trading.md` section 11.3.

## Considered options

- Lock instruments: one forward test for each instrument, or all US
  instruments for a universe forward test. The user refused this: different
  strategies on the same stocks must run at the same time.
- Keep the IB adapter and set `filter_unclaimed_external_orders=True`,
  `filter_position_reports=True`, and `generate_missing_orders=False`. After a
  restart, the NautilusTrader cache is empty, and the Python API has no
  database cache and no way to add a position. The strategy then does not know
  its position and buys again.
- Fork NautilusTrader and change the position reports of the IB adapter. Each
  upgrade then needs the patch again and a Rust wheel build.

## Consequences

- The LiveNode of a forward test does not use the IB execution client.
- The paper account margin is not used by any owner, so one owner cannot use
  the buying power of another.
- Orders from outside ATrade (TWS, IBKR website, phone app) belong to "by
  hand". ATrade cannot refuse them. When the account position differs from
  the sum of the owner positions, the paper trading page shows the difference.
- When a forward test stops, its positions and cash go to "by hand".
- Each NautilusTrader upgrade must run the tests of both clients, because
  `nautilus_trader.live.clients` is new in 2.0.
- A stock split changes the owner positions as
  [ADR 0008](0008-stock-splits-from-ibkr-evidence.md) says. Not checked: whether IBKR
  refuses opposite orders of two owners on one instrument (self-trade
  prevention).
