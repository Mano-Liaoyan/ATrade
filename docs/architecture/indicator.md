# Indicator library

This document is section 23 of the architecture specification
([`docs/architecture.md`](../architecture.md)). It is a new section of the
planning map
[Wayfinder: indicators, screens, and strategy help](https://github.com/Mano-Liaoyan/ATrade/issues/129).
Terms have the meaning that [`GLOSSARY.md`](../../GLOSSARY.md) gives them.

Sources: [Evidence for classic indicators and factors](https://github.com/Mano-Liaoyan/ATrade/issues/130),
[NautilusTrader 2.0 indicators, multi-instrument backtests, and batch backtests](https://github.com/Mano-Liaoyan/ATrade/issues/131),
[Indicator library scope and calculation place](https://github.com/Mano-Liaoyan/ATrade/issues/136),
ADR [0001](../adr/0001-one-indicator-definition-for-screens-and-strategies.md).

Phase: the indicator library is part of phase 1 of the map #129 (indicator
library, new metrics and robustness, rule builder, strategy templates, on the
existing single-instrument backtest). Screens (section 24) use it in phase 3.

## 23.1 Decisions

Source: [Indicator library scope and calculation place](https://github.com/Mano-Liaoyan/ATrade/issues/136),
ADR [0001](../adr/0001-one-indicator-definition-for-screens-and-strategies.md).

- Screens and strategies use one ATrade indicator definition. Each
  indicator is one class in the new module `indicator/`.
- When NautilusTrader 2.0 has the indicator, the class wraps the built-in
  indicator. When it does not, ATrade writes the calculation.
- A strategy registers the class with
  `Strategy.register_indicator_for_bars(bar_type, indicator)`.
- A screen gives the same class the saved daily bars (section 24).
- Because the code is the same, an indicator with the same name and the same
  parameters gives the same value in a screen and in a strategy.
- Time rule: the value at time t includes the bar that closes at t. The
  class uses only bars that close at or before t. NautilusTrader updates
  registered indicators before `on_bar`, so `on_bar` sees this value.
- Warm-up rule: when the class has not received enough bars, its value is
  "no value". It must not give the NautilusTrader default `0.0`. A screen
  removes an instrument with no value (section 24.3). The UI shows
  "No value".
- An indicator describes one instrument. A ranking across instruments, for
  example "top 20% by 12-1 momentum", is a screen condition (section 24.3),
  not an indicator. An indicator value does not change with the instrument
  list.
- Bar period:
  - In a screen, an indicator uses daily bars only. Its period is a number
    of trading days, for example 252.
  - A strategy can use the same class on 1-hour bars. The period is then a
    number of bars. One trading day has 7 regular-session 1-hour bars
    ([#141](https://github.com/Mano-Liaoyan/ATrade/issues/141)).
- Strategy code can also use the 39 NautilusTrader built-in indicators
  directly. Only the indicators of section 23.2 can be in a screen
  condition or in the rule builder.

## 23.2 First indicator set

Source: [Indicator library scope and calculation place](https://github.com/Mano-Liaoyan/ATrade/issues/136),
[Evidence for classic indicators and factors](https://github.com/Mano-Liaoyan/ATrade/issues/130).

The first set has 11 indicators. All of them use bars only. The formulas and
the usual parameters come from the #130 research
(`docs/research/indicators-and-factors-evidence.md` on the branch
`research/indicators-and-factors-evidence`). The level is the evidence level
of #130 (A is the strongest, D is practitioner use only).

| Indicator | Formula (daily bars, period n) | Usual parameters (#130) | Outputs | Code | Level (#130) |
|---|---|---|---|---|---|
| SMA | mean of the last n closes | n = 50, 200 | `value` | wraps `SimpleMovingAverage` | B (trend filter) |
| EMA | exponential average of the closes | not given | `value` | wraps `ExponentialMovingAverage` | B (trend filter) |
| 12-1 momentum | close(t − skip) / close(t − look-back) − 1 | look-back 252, skip 21 | `value` | ATrade | A (US), B (HK) |
| Distance to 52-week high | close / max(high of the last 252 days) | 252 | `value` | ATrade | B |
| Realized volatility | standard deviation of the daily log returns × √252 | n = 60 or 252 | `value` | ATrade | A |
| ATR | Wilder average of the true range, max(high − low, \|high − previous close\|, \|low − previous close\|) | n = 14 | `value` | wraps `AverageTrueRange` | B (risk control only) |
| Average trading value | mean(close × volume) | n = 20 or 60 | `value` | ATrade | B (screen only) |
| RSI | 100 − 100 / (1 + average gain / average loss), Wilder average | n = 14, levels 30 and 70 | `value` | wraps `RelativeStrengthIndex` | D |
| MACD | fast EMA − slow EMA, and its signal line | not given | `value` (MACD line), `signal`, `histogram` | wraps `MovingAverageConvergenceDivergence` | D (entry timing) |
| Bollinger Bands | middle average ± k standard deviations | not given | `upper`, `middle`, `lower` | wraps `BollingerBands` | D (entry timing) |
| Donchian channel | highest high and lowest low of the last n bars | not given | `upper`, `middle`, `lower` | wraps `DonchianChannel` | B (trend filter, range break) |

- The output names of the wrapped indicators are the NautilusTrader names.
  Checked in #138: MACD has `value`, `signal`, and `histogram`. Bollinger
  Bands and the Donchian channel have `upper`, `middle`, and `lower`.
- Average trading value is in the currency of the instrument (USD for US
  instruments, HKD for Hong Kong instruments).
- RSI, MACD, and Bollinger Bands are entry timing tools only. #130 found no
  reliable evidence of a return after costs for them.
- ATR does not predict direction. Use it for stops and position size.
  Average trading value does not predict direction. Use it for liquidity
  conditions.

### 23.2.1 Indicators that are not in the first set

- The financial-data indicators E/P (or EBIT/EV), book-to-market, gross
  profitability, and the Piotroski F-score are not in the first set.
- They come after a decision on a financial data source, in a new ticket.
- Hong Kong instruments have no financial data in ATrade
  ([#141](https://github.com/Mano-Liaoyan/ATrade/issues/141)). When these
  indicators come, their value for a Hong Kong instrument is "no value".

## 23.3 Module

- Path: `backend/src/atrade/indicator/`. One public entry file.
- `indicator` imports only `foundation` of the ATrade modules. It also
  imports `nautilus_trader`, for the built-in indicators and the
  NautilusTrader bar type.
- `indicator` reads no database and calls no IBKR. The caller reads the bars
  and gives them to the class.
- `indicator` has no table, no HTTP route, and no WebSocket path.
- Callers:
  - `screen` (section 24) gives saved daily bars (`foundation/bar.py` `Bar`)
    to the classes.
  - Strategy code imports `atrade.indicator` and registers the classes. The
    backtest child and the forward test child run this code
    ([`strategy.md`](strategy.md) section 9.2).
  - The rule builder writes strategy code that imports `atrade.indicator`
    ([#138](https://github.com/Mano-Liaoyan/ATrade/issues/138)).

Each class has:

| Part | Behavior |
|---|---|
| Constructor | The parameters of the indicator, each with a default value. |
| `handle_bar(bar)` | Takes one NautilusTrader `Bar`. `register_indicator_for_bars` calls it. |
| A method for one `foundation` `Bar` | The screen path. It gives the same update as `handle_bar` for the same open, high, low, close, and volume. |
| `initialized` | `True` when the class has enough bars for a value. NautilusTrader reads it for `indicators_initialized()`. |
| Outputs (`value`, or the names of section 23.2) | The value, or "no value" while `initialized` is `False`. |
| `reset()` | Removes all received bars. |

The public entry also exports a catalog of the first set. For each
indicator, the catalog has:

- the key that screens and rule builder rules store (section 23.6),
- the name that the UI shows, for example `RSI(14)`,
- the parameters with their types, defaults, and allowed ranges,
- the outputs,
- the number of daily bars that a screen reads (section 23.4).

`screen` uses the catalog to check a screen (section 24.6). The rule builder
uses it for its condition lists.

## 23.4 Look-back bars of a screen

Source: [Indicator library scope and calculation place](https://github.com/Mano-Liaoyan/ATrade/issues/136).

A screen reads only the daily bars that each indicator in its conditions
needs. Examples from #136: RSI(14) reads about 100 bars. 12-1 momentum reads
253 bars.

| Indicator | Daily bars that a screen reads |
|---|---|
| SMA(n), average trading value(n), Bollinger Bands(n), Donchian channel(n) | n |
| Distance to 52-week high | 252 |
| 12-1 momentum (look-back L) | L + 1 |
| Realized volatility(n) | n + 1 (n log returns) |
| EMA, RSI, ATR, MACD | A fixed count for each indicator, more than its warm-up (RSI(14): about 100) |

EMA, RSI, ATR, and MACD use recursive averages. Their value depends a little
on the first bar that the class receives. Section 23.8 has the open point.
Section 21.1 of [`docs/architecture.md`](../architecture.md) has the
measured differences (#160).

## 23.5 Consistency test

Source: ADR [0001](../adr/0001-one-indicator-definition-for-screens-and-strategies.md).

- Each indicator of the first set has one consistency test.
- The test gives the same bars to the screen path and to the strategy path.
  The strategy path is a NautilusTrader backtest engine run with the class
  registered by `register_indicator_for_bars`.
- The values at each bar must be equal. "No value" must be equal too: both
  paths give "no value" for the same bars.
- Each indicator also has a test that the value before the warm-up end is
  "no value", not `0.0`.
- Each indicator written by ATrade has a test with known values from its
  formula.

## 23.6 Stored indicator references

Screens (section 24.4) and rule builder rules
([#138](https://github.com/Mano-Liaoyan/ATrade/issues/138)) store an
indicator reference in JSON:

```json
{"indicator": "rsi", "parameters": {"period": 14}, "output": "value"}
```

- `indicator` is a catalog key. The keys are choices of this document:
  `sma`, `ema`, `momentum_12_1`, `distance_to_52_week_high`,
  `realized_volatility`, `atr`, `average_trading_value`, `rsi`, `macd`,
  `bollinger_bands`, `donchian_channel`.
- `parameters` holds the constructor parameters. A missing parameter gets
  its default.
- `output` names one output of section 23.2. A multi-line indicator needs it
  (MACD, Bollinger Bands, Donchian channel).

## 23.7 Phase

| Part | Phase of map #129 |
|---|---|
| `indicator/` module, the 11 classes, the catalog, the consistency tests | Phase 1 |
| Use of the classes in the rule builder and the strategy templates | Phase 1 |
| Use of the classes in screens (section 24) | Phase 3 |
| Financial-data indicators (section 23.2.1) | After a decision on a financial data source. Not in a phase yet. |

## 23.8 Left to the implementation

- The Python type of a value and of "no value" (for example `float | None`,
  as the NautilusTrader indicators use `float`).
- The name of the screen-path method of section 23.3.
- The defaults of EMA, MACD, Bollinger Bands, and the Donchian channel.
  #130 gives no usual parameters for them.
- The skip parameter of 12-1 momentum must accept 0, or the strategy template
  S3 "12-month time-series momentum" (look-back 252, skip 0) becomes a code
  template ([#139](https://github.com/Mano-Liaoyan/ATrade/issues/139)).
- The fixed look-back count of EMA, RSI, ATR, and MACD in a screen
  (section 23.4).
- The smoothing type of the wrapped ATR and RSI. #130 gives the Wilder
  average. If the NautilusTrader default is different, the class passes
  `MovingAverageType.Wilder`.
- The annualization factor of realized volatility on 1-hour bars. The #130
  formula (√252) is for daily bars.
- The names that the UI shows for the indicators.
