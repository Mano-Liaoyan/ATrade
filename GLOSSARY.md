# ATrade

ATrade is a personal trading platform. It finds stocks, shows charts, tests
strategies on history and on live data, and sends orders to a broker.

## Strategies

**Strategy**:
A set of trading rules that the user writes as code in the browser. The same
strategy runs in a backtest and in a forward test.
_Avoid_: algorithm, bot, script

**Strategy version**:
One saved copy of the code of a strategy. A strategy version does not change
after it is saved. Each backtest and each forward test records the strategy
version that it used.
_Avoid_: revision, snapshot, commit

## Strategy testing

**Backtest**:
A test of a strategy on historical bars. No order goes to a broker.
_Avoid_: simulation, historical run

**Forward test**:
A test of a strategy that runs automatically on live market data and sends
orders to a paper account.
_Avoid_: paper trading run, live simulation

**Paper trading**:
Trading on the broker's paper account. It includes paper orders sent by hand
and forward tests.
_Avoid_: demo trading, simulated trading

## Orders

**Paper order**:
A real order sent to the broker's paper account. The broker fills it at market
prices. No real money moves.
_Avoid_: simulated order, order simulation

**Live order**:
A real order sent to a broker account that holds real money.
_Avoid_: real trade, production order

**Paper capital**:
The cash amount a backtest starts with. It comes from the paper account
balance, or from a local value when no balance is available.
_Avoid_: fallback capital, ledger
