# A custom indicator is a formula, and each reference holds its expression

The user adds own indicators as formula expressions, for example
`close / sma(50) - 1`. An expression is not Python code. The parser reads it
with Python `ast` and an allow-list: numbers, `+ - * / **`, the bar fields, the
functions `mean max min sum std lag abs log`, and calls to the built-in
indicators of the catalog. Nothing runs the text: ATrade does not use `eval` or
`exec`, and an attribute or a name outside the allow-list is a problem of the
check. So a custom indicator runs in the `web` process and in a backtest child
without a sandbox. Each stored indicator reference holds a copy of the
expression in its `formula` field, so a change or a delete of the custom
indicator does not change a saved screen, strategy version, or backtest.
Decision: [#372](https://github.com/Mano-Liaoyan/ATrade/issues/372).

## Considered Options

- Python classes written by the user. Rejected: the code needs a child process
  with limits of time, memory, and network, also for each screen run and each
  chart read.
- Immutable versions of a custom indicator in a table, with a reference that
  holds the version. Rejected: `check_indicator_reference`, the screen run, and
  the backtest child then need a database read, and `indicator` reads no
  database (ADR 0001). A delete also needs a hidden row.
- A reference that holds only the key, with one current expression. Rejected:
  an old backtest could not be repeated, and a delete would break a saved
  screen.
- Refuse a delete while a reference exists. Rejected: the check must read each
  screen, version code, and backtest, and the copy makes it unnecessary.

## Consequences

- The class is `FormulaIndicator(expression)` in `atrade.indicator`. The screen
  path, the chart path, and the strategy path use it, as ADR 0001 requires. A
  strategy version holds the expression in its code, so a backtest child needs
  no database read.
- The parser calculates the look-back from the expression. The user does not
  declare it.
- A divide by zero, NaN, infinity, a math domain problem, or a window that is
  not full gives "no value". The class never raises an exception for a bar, so
  one instrument cannot stop a screen run.
- A delete is always allowed. A deleted custom indicator stays in its saved
  references.
- A change does not reach saved references, also not the chart indicator set.
  To use the new expression, the user clicks "Use current expression" at the
  reference. So one screen can hold 2 expressions with 1 name. The screen check
  refuses this, because a result names its columns by the indicator name.
- A custom indicator has no parameters and one output, `value`. Its catalog key
  is `custom_<id>`. No built-in key can start with `custom_`, and the database
  does not give a deleted id again.
- An expression can call built-in indicators only, not other custom indicators.
  So a reference needs only 1 expression, and an expression cannot call itself.
