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

**Bar source**:
A data provider that gives bars, for example IBKR or Databento. ATrade keeps
the bars of each bar source apart. In Chinese, write K 线来源.
_Avoid_: feed, vendor (for this meaning), provider

**Source order**:
The ordered list of bar sources that ATrade reads bars from. For each time
range, the first bar source in the list that has saved that range gives the
bars. In Chinese, write 来源顺序.
_Avoid_: source priority, fallback

**Official close**:
The price of the closing auction on the listing exchange of an instrument.
The close of a daily bar is the official close. In Chinese, write 官方收盘价.
_Avoid_: last price, last trade

**Exchange rate**:
The USD value of 1 unit of another currency at the close of one day. It is
the IBKR forex rate. In Chinese, write 汇率. A backtest of an instrument that
is not in USD uses it.
_Avoid_: FX price, conversion factor

**Indicator**:
One number that describes an instrument at one time, calculated from its bars
or its financial data, for example RSI(14) or the price to earnings ratio. In
Chinese, write 指标.
_Avoid_: metric, signal, factor (in user copy)

**Screen**:
A saved set of conditions on the instruments of one market, and an order. It
names the instruments that it starts from, then filters them by price, trading
value, exchange, and trading status, then applies conditions on indicators, for
example "still trading, price above $10, RSI(14) below 30, ordered by 12-1
momentum". All conditions must be true. In Chinese, write 选股条件.
_Avoid_: screener (the page name only), filter, scan

**Screen result**:
The ordered list of instruments that one run of a screen gives, with the run
time. In Chinese, write 选股结果.
_Avoid_: scan result, hits

**Watchlist**:
The list of instruments that the user saves. In Chinese, write 自选股.
_Avoid_: favorites, pins

**HK instrument list**:
The list of Hong Kong instruments that the user keeps for screens. ATrade keeps
the daily bars of these instruments up to date. It has no instruments that
stopped trading. In Chinese, write 港股品种表.
_Avoid_: HK universe, HK watchlist, HK pool

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

**Rule builder**:
The form that writes a strategy version from entry conditions, exit
conditions, and a position size. It writes code in one direction only: it
does not read code back into conditions. In Chinese, write 规则构建器.
_Avoid_: no-code editor, visual editor, wizard, strategy generator

## Strategy testing

**Backtest**:
A test of a strategy on historical bars. No order goes to a broker.
_Avoid_: simulation, historical run

**Backtest limits**:
The timeout of one backtest and the number of backtests that run at the same
time (the concurrency). The user changes them in the UI. Other backtests wait
in the queue.
_Avoid_: backtest settings, quota

**Universe**:
The instruments that one backtest can trade at each time. A point-in-time rule
(for example the top instruments by trading value of each quarter) or a fixed
list gives it. A point-in-time rule uses only data known at that time, so it
includes instruments that stopped trading later. A screen that runs again at
each rebalance on the data known at that date is a point-in-time rule. A screen
result used for the full time range is a fixed list. In Chinese, write 品种池.
_Avoid_: index members, stock pool, basket, symbol list, portfolio

**Parameter sweep**:
A set of backtests of one strategy version on the same universe and time
range, one backtest for each combination of parameter values. In Chinese,
write 参数扫描.
_Avoid_: optimization, grid search, batch backtest

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
functions. All pages show the same key metrics in the same order, and show
the max drawdown as a negative percent. In Chinese, write 绩效指标.
_Avoid_: statistic, KPI, indicator

**Round trip**:
The trades of a test from a position of 0 back to a position of 0.
_Avoid_: closed trade

**Win rate**:
The share of round trips with a profit after commissions.
_Avoid_: hit rate

**Net profit**:
The final equity of a test minus its start capital (the paper capital of a
backtest, or the allocated capital of a forward test).
_Avoid_: PnL

**In-sample**:
The part of a backtest range before the split time. The user develops the
strategy on this part. In Chinese, write 样本内.
_Avoid_: training set

**Out-of-sample**:
The part of a backtest range after the split time. The user checks the
strategy on this part one time and does not change the strategy for it. In
Chinese, write 样本外.
_Avoid_: holdout, validation set

**Trial count**:
The number of finished backtests of the same strategy (all strategy
versions), instrument, and bar period. It tells how many tries a result was
selected from. In Chinese, write 尝试次数.
_Avoid_: number of tries, N

**Forward test**:
A test of a strategy that runs automatically on live market data and sends
orders to a paper account.
_Avoid_: paper trading run, live simulation

**Same-period backtest**:
A backtest of the strategy version, instruments, and bar period of a forward
test, from the forward test start to its end (or to now), with the allocated
capital as paper capital. For a universe, it uses the members that the
forward test recorded for each quarter. The user compares it with the forward
test.
_Avoid_: shadow backtest, replay

**Interruption**:
A time in which a forward test did not run: after a crash, while IB Gateway
was not reachable, or after a restart of the forward-test service. The
forward test records the start and the end of each interruption.
_Avoid_: outage, downtime gap

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

**Owner**:
The forward test, or the user by hand, that one order belongs to. Each fill,
position, and cash amount in the paper account belongs to one owner. Orders
from outside ATrade belong to the user by hand. In Chinese, write 所有者.
_Avoid_: sub-account, bucket, sleeve

**Owner ledger**:
The record of the fills, positions, and cash of each owner. The position of
the paper account in an instrument is the sum of the owner positions. In
Chinese, write 所有者账本.
_Avoid_: virtual account, sub-ledger

**Allocated capital**:
The USD amount of the paper account that one forward test gets at its start.
The forward test trades only with this amount and its own fills. In Chinese,
write 分配资金.
_Avoid_: start balance, budget, allocation

**Paper capital**:
The cash amount a backtest starts with. It comes from the paper account
balance, or from a local value when no balance is available.
_Avoid_: fallback capital, ledger

## AI assistant

**AI assistant**:
The language model that discusses strategies and screens with the user, writes
strategy versions and new screens, runs screens, and runs and compares
backtests. It never changes or deletes a screen that the user saved, never
changes the watchlist, never sends a paper order, and never starts a forward
test. In Chinese, write AI 助手.
_Avoid_: agent, bot, copilot

**Conversation**:
One exchange of messages between the user and the AI assistant. It belongs to
at most one strategy. In Chinese, write 对话.
_Avoid_: chat, thread, session

**Credential**:
One named subscription login or API key of a model provider that the AI
assistant uses, for example "Anthropic API key · personal". In Chinese, write
凭据.
_Avoid_: account, auth, token

**Prompt version**:
One saved copy of the part of the AI assistant's system prompt that the user
can edit. It does not change after it is saved. Each conversation records the
prompt version that it used. In Chinese, write 提示词版本.
_Avoid_: prompt revision, instructions

**Discarded strategy version**:
A strategy version that the AI assistant saved and the user discarded. It
stays in the history, and its backtests stay. In Chinese, write 已丢弃的策略版本.
_Avoid_: deleted version, rejected version

## User interface

**Workbench**:
A page that fills the window below the header and does not scroll as a page.
It has side columns and panels. Each region that can overflow scrolls in
itself. In Chinese, write 工作台.
_Avoid_: dashboard, layout

**Panel**:
A region of a workbench with a 32px header line (a name or tabs) and a body.
The user can minimize a panel (only its header line, or a 24px status bar,
stays) or maximize it (it gets all the height). A panel with a status bar
(the strategy page "Problems and output" panel) always shows the status bar
at its bottom. In Chinese, write 面板.
_Avoid_: pane, card, widget (in user copy; code and docs can name a part of
a chart a pane, for example the drawdown pane, and keep the storage key
`pane-order`)

**Side column**:
A column at the left or right side of a workbench, for example the watchlist
or the paper order form. The user can collapse it to a 32px rail. In Chinese,
write 侧栏.
_Avoid_: sidebar, drawer

**Splitter**:
The bar between 2 panels. The user drags it, or moves it with the arrow keys,
to change the panel heights. In Chinese, write 分隔条.
_Avoid_: divider, resizer
