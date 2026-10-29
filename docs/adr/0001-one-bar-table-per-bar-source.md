# One bar table for each bar source, and a source order that the user sets

ATrade gets historical US bars from Databento in addition to IBKR
([issue 141](https://github.com/Mano-Liaoyan/ATrade/issues/141)). Each bar
source has its own bar table and its own saved-range table (`ibkr_bar`,
`databento_bar`). The old `bar` table becomes `ibkr_bar`. ATrade reads bars
through a source order, which is a global setting in PostgreSQL. A backtest can
change the source order, and it records the source order and the bar count of
each bar source that it used. For each time range, the first bar source that
saved the range gives all bars of the range. Another bar source does not fill
a holiday.

## Considered options

- One `bar` table with a `source` column, and IBKR always first. This is less
  code, but it fixes the precedence in the code. The user does not know if
  IBKR stays the best bar source, and more bar sources can come later.
- Merge by each bar (the first bar source with a bar at that start time). This
  is simpler, but one day can then mix the bars of 2 bar sources.

## Consequences

- Each query that reads bars, and each function that reads the saved ranges
  (the watchlist `saved_bars` too), takes a source order and reads more than
  one table.
- A new bar source needs a new enum value, a new bar table, and a new
  saved-range table.
