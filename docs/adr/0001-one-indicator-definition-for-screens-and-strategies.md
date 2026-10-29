# One indicator definition for screens and strategies

Screens and strategies use the same indicator code: one class for each
indicator in a new `indicator/` module. The module imports only `foundation`
and does not read the database. A strategy registers the class with
`register_indicator_for_bars`. A screen gives the same class the saved daily
bars. When NautilusTrader has the indicator, the class wraps the built-in
indicator. We decided this because 2 implementations can give different
values for the same name, for example because of a different warm-up or a
different smoothing method. A user who sees an instrument in a screen result
must get the same value in a strategy. Decision:
[#136](https://github.com/Mano-Liaoyan/ATrade/issues/136).

## Considered Options

- Strategies use the NautilusTrader indicators, and screens use a second
  implementation. Rejected: the values of an indicator with the same name
  can be different.
- Calculate all values before the run, keep them in PostgreSQL, and let
  strategies read them. Rejected: a forward test needs values from live
  bars, and stored values add a risk of look-ahead in backtests.

## Consequences

- The value of an indicator at time t includes the bar that closes at t,
  as in NautilusTrader, which updates indicators before `on_bar`.
- When there are not enough bars, the value is "no value", not the
  NautilusTrader default `0.0`. A screen leaves out an instrument with no
  value.
- Each indicator has a test: the screen path and the strategy path get the
  same bars and must give equal values.
- A ranking across instruments (for example "top 20% by momentum") is part
  of a screen condition, not an indicator. An indicator value does not
  change with the instrument list.
