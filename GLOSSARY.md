# ATrade

ATrade is a personal trading platform. It finds stocks, shows charts, tests
strategies on history and on live data, and sends orders to a broker.

## Market data

**Instrument**:
A security that the user can trade. A stock symbol, an exchange, and a
currency identify it. Examples: `AAPL / NASDAQ / USD`, `700 / SEHK / HKD`.
_Avoid_: ticker. Use symbol only for the code part of an instrument.

**Bar**:
The open price, high price, low price, close price, and volume of one
instrument in one time period. In Chinese, write K 线. A chart can show a bar
as a candlestick, but the data is always a bar.
_Avoid_: candle

**Watchlist**:
The list of instruments that the user saves. In Chinese, write 自选股.
_Avoid_: favorites, pins

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

**Backtest limits**:
The timeout of one backtest and the number of backtests that run at the same
time (the concurrency). The user changes them in the UI. Other backtests wait
in the queue.
_Avoid_: backtest settings, quota

**Trade**:
One fill of an order in a backtest or a forward test: the time, the side, the
quantity, and the price.
_Avoid_: deal, execution

**Equity curve**:
The cash plus the value of the position at the end of each bar of a test.
_Avoid_: balance curve, PnL curve

**Metric**:
One number that describes the result of a test, for example the total return
or the max drawdown. Backtests and forward tests use the same metric
functions.
_Avoid_: statistic, KPI

**Forward test**:
A test of a strategy that runs automatically on live market data and sends
orders to a paper account.
_Avoid_: paper trading run, live simulation

**Paper trading**:
Trading on the broker's paper account. It includes paper orders sent by hand
and forward tests.
_Avoid_: demo trading, simulated trading

## Orders

**Paper account**:
The broker account that holds no real money. Paper orders go to this account.
_Avoid_: demo account, simulated account

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
