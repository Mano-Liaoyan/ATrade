# One simulated venue for each currency in a multi-instrument backtest

A backtest with more than one instrument puts all instruments of its one
currency on one simulated venue (`SMART` for US instruments). The strategy
gets the instrument IDs `SYMBOL.SMART`. The trade table still records the
real exchange. Reason: NautilusTrader 2.0 makes one cash account for each
venue. With the exchange as the venue (`SYMBOL.EXCHANGE`, as in a
single-instrument backtest), NASDAQ, NYSE, and ARCA instruments get 3
separate cash amounts. `routing=True` does not merge them: the engine
refuses an instrument whose venue was not added. One simulated venue gives
one shared cash account, as the IBKR SMART routing does. Single-instrument
backtests keep the exchange as the venue. Decision:
[#142](https://github.com/Mano-Liaoyan/ATrade/issues/142), 2026-10-29.

## Considered options

- One account for each exchange: the paper capital must be split between
  the exchanges before the start.
- `SMART` also for single-instrument backtests: all existing backtest and
  forward test instrument IDs change.

## Consequences

- One multi-instrument backtest has one currency. A USD cash account cannot
  pay for an HKD instrument, and the engine does not convert cash.
- A multi-instrument forward test uses the live IDs `SYMBOL.EXCHANGE`, not
  `SYMBOL.SMART`. The live IB account has one account for all venues. A
  strategy uses only the instrument IDs that the platform gives it and does
  not write a venue in its code
  ([#146](https://github.com/Mano-Liaoyan/ATrade/issues/146)).
