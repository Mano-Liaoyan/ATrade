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
| Bollinger Bands | mean of the last n closes ± k population standard deviations of the same closes | not given | `upper`, `middle`, `lower` | wraps `BollingerBands` | D (entry timing) |
| Donchian channel | highest high and lowest low of the last n bars | not given | `upper`, `middle`, `lower` | wraps `DonchianChannel` | B (trend filter, range break) |

- The output names of the wrapped indicators are the NautilusTrader names.
  Checked in #138: MACD has `value`, `signal`, and `histogram`. Bollinger
  Bands and the Donchian channel have `upper`, `middle`, and `lower`.
- The ATrade classes of the wrapped indicators (#161) and their defaults.
  #130 gives no usual parameters for EMA, MACD, Bollinger Bands, and the
  Donchian channel. Their defaults are the common textbook values.

  | Indicator | Class | Defaults | First value at bar |
  |---|---|---|---|
  | SMA | `SMA` | `period=50` | `period` |
  | EMA | `EMA` | `period=20` | `period` |
  | ATR | `ATR` | `period=14` | `period` |
  | RSI | `RSI` | `period=14` | `period + 1` |
  | MACD | `MACD` | `fast_period=12`, `slow_period=26`, `signal_period=9` | `slow_period + signal_period - 1` |
  | Bollinger Bands | `BollingerBands` | `period=20`, `k=2.0` | `period` |
  | Donchian channel | `DonchianChannel` | `period=20` | `period` |

- The ATrade classes of the indicators that ATrade writes (#162) and their
  defaults. #130 gives n = 60 or 252 for realized volatility and n = 20 or
  60 for average trading value. The defaults are the shorter values.

  | Indicator | Class | Defaults | First value at bar |
  |---|---|---|---|
  | 12-1 momentum | `Momentum12_1` | `look_back=252`, `skip=21` | `look_back + 1` |
  | Distance to 52-week high | `DistanceTo52WeekHigh` | `period=252` | `period` |
  | Realized volatility | `RealizedVolatility` | `period=60`, `bars_per_year=252` | `period + 1` |
  | Average trading value | `AverageTradingValue` | `period=20` | `period` |

- 12-1 momentum accepts `skip` from 0 to `look_back − 1`. With `skip=0` the
  value is close(t) / close(t − look-back) − 1 (template S3). The class
  refuses other values with a `ValueError`.
- Realized volatility is the sample standard deviation (n − 1) of the last
  n log returns of the close, times √`bars_per_year`. On daily bars
  `bars_per_year` is 252. On 1-hour bars the strategy passes 1764 (252 days
  × 7 regular-session bars, section 23.1). The class does not read the bar
  period.
- Distance to 52-week high uses the highs of the last `period` bars, the
  current bar included, so the value is at most 1.
- The Donchian `middle` is the mean of `upper` and `lower`. The MACD
  `histogram` is `value` − `signal`. RSI is on a scale of 0 to 100.
- The wrapped ATR and RSI use the Wilder average (#130). The NautilusTrader
  2.0.0rc7 default of both is Wilder, so the classes do not pass
  `MovingAverageType.Wilder` (#160, section 21.1 of
  [`docs/architecture.md`](../architecture.md)).
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
- `indicator` has no table, no HTTP route, and no WebSocket path. The
  chart routes of section 23.9 are in `market_data`.
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
| `update(bar)` | The screen path: takes one `foundation` `Bar`. It gives the same update as `handle_bar` for the same open, high, low, close, and volume. A wrapped class makes a NautilusTrader bar from it and calls `handle_bar`. |
| `initialized` | `True` when the class has enough bars for a value. NautilusTrader reads it for `indicators_initialized()`. |
| Outputs (`value`, or the names of section 23.2) | The value (`float`), or "no value" (`None`) while `initialized` is `False`. |
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

Decided (#163): the catalog is `INDICATOR_CATALOG`
(`indicator/indicator_catalog.py`), a mapping from the key to an
`IndicatorDefinition` (`key`, `name`, `short_name`, `chart_placement`,
`parameters`, `outputs`, `display_name(parameters)`,
`screen_look_back_bars(parameters)`). `short_name` and `chart_placement`
are the fields for charts of section 23.9.2 (#327). Each
`IndicatorParameter` has `name`, `value_type` (`int` or `float`), `default`,
`minimum`, and `maximum`. The range includes both ends.

| Key | UI name (defaults) | Parameters: default (allowed range) | Outputs |
|---|---|---|---|
| `sma` | `SMA(50)` | `period`: 50 (1 to 1000) | `value` |
| `ema` | `EMA(20)` | `period`: 20 (1 to 1000) | `value` |
| `momentum_12_1` | `12-1 momentum(252, 21)` | `look_back`: 252 (1 to 1000), `skip`: 21 (0 to 999, less than `look_back`) | `value` |
| `distance_to_52_week_high` | `Distance to 52-week high(252)` | `period`: 252 (1 to 1000) | `value` |
| `realized_volatility` | `Realized volatility(60)` | `period`: 60 (2 to 1000), `bars_per_year`: 252 (1 to 10000) | `value` |
| `atr` | `ATR(14)` | `period`: 14 (1 to 1000) | `value` |
| `average_trading_value` | `Average trading value(20)` | `period`: 20 (1 to 1000) | `value` |
| `rsi` | `RSI(14)` | `period`: 14 (1 to 1000) | `value` |
| `macd` | `MACD(12, 26, 9)` | `fast_period`: 12 (1 to 1000, less than `slow_period`), `slow_period`: 26 (2 to 1000), `signal_period`: 9 (1 to 1000) | `value`, `signal`, `histogram` |
| `bollinger_bands` | `Bollinger Bands(20, 2)` | `period`: 20 (1 to 1000), `k`: 2.0 (0.1 to 10.0) | `upper`, `middle`, `lower` |
| `donchian_channel` | `Donchian channel(20)` | `period`: 20 (1 to 1000) | `upper`, `middle`, `lower` |

- The UI name is the indicator name and its parameter values in the
  constructor order, for example `RSI(14)`. A `float` shows without a
  trailing zero (`2`, `2.5`). `bars_per_year` is not in the name.
- The ranges are the simplest ones that each class accepts. 1000 bars is
  about 4 years of daily bars.

## 23.4 Look-back bars of a screen

Source: [Indicator library scope and calculation place](https://github.com/Mano-Liaoyan/ATrade/issues/136).

A screen reads only the daily bars that each indicator in its conditions
needs. Examples from #136: RSI(14) reads about 100 bars. 12-1 momentum reads
253 bars.

| Indicator | Daily bars that a screen reads |
|---|---|
| SMA(n), average trading value(n), Bollinger Bands(n), Donchian channel(n) | n |
| Distance to 52-week high (period n, default 252) | n |
| 12-1 momentum (look-back L) | L + 1 |
| Realized volatility(n) | n + 1 (n log returns) |
| EMA(n), RSI(n), ATR(n) | 8 × n (RSI(14): 112) |
| MACD(fast, slow, signal) | 8 × (slow + signal) (MACD(12, 26, 9): 280) |

EMA, RSI, ATR, and MACD use recursive averages. Their value depends a little
on the first bar that the class receives. Decided (#163): the fixed count is
8 × the longest period of the recursive average. Section 21.1 of
[`docs/architecture.md`](../architecture.md) has the measured differences
(#160): with 8 × the period, each difference is less than 0.005, half of
the last place of a value with 2 decimals. #160 did not measure the MACD
signal line. The signal line is an EMA of the MACD line, so the MACD count
adds 8 × `signal_period`.

`IndicatorDefinition.screen_look_back_bars(parameters)` gives the count. A
test gives each class with its default parameters exactly this count of
bars and checks that each output has a value
(`tests/indicator/test_indicator_catalog.py`).

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
- Decided (#163): `check_indicator_reference(reference)` returns a list of
  `IndicatorProblem(location, message)`. An empty list means the reference
  is correct. `location` is the path in the reference, for example
  `("parameters", "period")`, `("output",)`, or `()` for the reference.
  A screen (section 24.6) and the rules of the rule builder put the location
  of the condition before it. The problems are:
  - the reference is not an object, or has a field that is not
    `indicator`, `parameters`, or `output`,
  - an unknown `indicator` key,
  - `parameters` is not an object, an unknown parameter, a parameter of the
    wrong type (an `int` parameter refuses `20.5` and `true`), or a
    parameter out of its range,
  - a parameter order rule fails: 12-1 momentum `skip` less than
    `look_back`, MACD `fast_period` less than `slow_period`,
  - a multi-line indicator without `output`, or an unknown `output`.
- A single-line indicator without `output` uses `value`.
- `check_indicator_reference(reference, has_output=False)` and
  `create_indicator(reference, has_output=False)` check a reference of a
  whole indicator, as a bar chart uses it (section 23.9): `output` is then an
  unknown field, and a multi-line indicator needs no `output` (#327).
- `create_indicator(reference)` makes the class with the defaults for the
  missing parameters. It raises `ValueError` when the reference has
  problems.

## 23.7 Phase

| Part | Phase of map #129 |
|---|---|
| `indicator/` module, the 11 classes, the catalog, the consistency tests | Phase 1 |
| Use of the classes in the rule builder and the strategy templates | Phase 1 |
| Use of the classes in screens (section 24) | Phase 3 |
| Financial-data indicators (section 23.2.1) | After a decision on a financial data source. Not in a phase yet. |
| Indicators on bar charts (section 23.9) | After phase 1. It uses the classes and the catalog of phase 1. Not in a phase of map #129. |

## 23.8 Left to the implementation

No open points.

## 23.9 Indicators on bar charts

Source: [Indicators on bar charts](https://github.com/Mano-Liaoyan/ATrade/issues/323)
(research, prototype, and the choices A1, B1, C1 with mark style M3 of the
user).

### 23.9.1 Decisions

- The backend calculates each indicator value on a chart with the classes of
  this section. The frontend does not calculate indicators. So a chart, a
  screen, and a strategy give the same value for the same indicator, the
  same parameters, and the same bars.
- A bar without a value is whitespace data of `lightweight-charts` (a point
  with only `time`). The legend shows "No value" for it.
- One chart indicator set is in PostgreSQL. All market data charts use it
  (today: the bar chart of the instrument page). A change saves at once.
- The backtest and forward test charts show the indicators in
  `CHART_INDICATORS` of the strategy version code (section 23.9.8), not the
  chart indicator set.
  The user can add, change, and remove indicators there. These changes are
  not saved.
- No indicator templates and no set for each instrument in the first
  version.
- No limit on the indicator count. A chart has the price pane and at most 3
  own panes (section 23.9.3).
- In code and in this document, a part of a chart with its own price scale
  is a pane. User copy does not use the word (GLOSSARY "Panel").

### 23.9.2 Catalog fields for charts

Each `IndicatorDefinition` (section 23.3) gets 2 fields:

| Key | `short_name` | `chart_placement` |
|---|---|---|
| `sma` | `SMA` | `price` |
| `ema` | `EMA` | `price` |
| `bollinger_bands` | `BB` | `price` |
| `donchian_channel` | `DC` | `price` |
| `rsi` | `RSI` | `own` |
| `macd` | `MACD` | `own` |
| `atr` | `ATR` | `own` |
| `realized_volatility` | `RV` | `own` |
| `momentum_12_1` | `MOM 12-1` | `own` |
| `distance_to_52_week_high` | `52W HIGH` | `own` |
| `average_trading_value` | `ATV` | `own` |

- `price`: the indicator draws on the price pane. `own`: it draws in an own
  pane.
- The legend name is `short_name` and the values of the parameters with
  `is_in_name`, with one space between them, for example `SMA 50`,
  `BB 20 2`, `MACD 12 26 9`. A `float` shows without a trailing zero.

### 23.9.3 Panes and lines

- The price pane is always the first pane. It holds the candlesticks and
  the `price` indicators.
- Each new `own` indicator gets a new pane under the others. When the chart
  has 3 own panes, a new `own` indicator goes into the last pane. Thus a
  pane can hold more than one indicator.
- When the last indicator of an own pane goes away, the pane goes away.
- The user drags the line between 2 panes to change their heights
  (`layout.panes.enableResize`). The heights are not saved.
- Lines of each indicator (`lightweight-charts` 5.2.1):

  | Indicator | Series |
  |---|---|
  | SMA, EMA, ATR, realized volatility, 12-1 momentum, distance to 52-week high | 1 `LineSeries` |
  | Bollinger Bands, Donchian channel | 3 `LineSeries` (`upper`, `middle`, `lower`). The first version has no fill between the bands. |
  | RSI | 1 `LineSeries`, and 2 price lines at 30 and 70 (`createPriceLine`, dashed, `--cds-border-strong-01`, no axis label) |
  | MACD | 2 `LineSeries` (`value`, `signal`) and 1 `HistogramSeries` (`histogram`) |
  | Average trading value | 1 `HistogramSeries` |

- Number formats of the price scale and the legend:

  | Indicator | Format |
  |---|---|
  | SMA, EMA, Bollinger Bands, Donchian channel, ATR, MACD | `CHART_PRICE_FORMAT` ("11,000.00") |
  | RSI | 2 decimals ("75.86") |
  | 12-1 momentum, distance to 52-week high, realized volatility | The value × 100 with 2 decimals and " %" ("-3.20 %"). Distance to 52-week high shows "96.80 %" for 0.968. |
  | Average trading value | A short amount with 2 decimals ("12.35 B", "820.10 M") |

- Line style. Each line has `color`, `style`, and `width`:
  - `color` is an index from 1 to 14 in the Carbon data visualization
    categorical palette (14 colors). The light themes use the light palette
    (purple 70, cyan 50, teal 70, magenta 70, red 50, red 90, green 60,
    blue 80, magenta 50, yellow 50, teal 50, cyan 90, orange 70,
    purple 50). The dark theme uses the dark palette (purple 60, cyan 40,
    teal 60, magenta 40, red 50, red 10, green 30, blue 50, magenta 60,
    yellow 40, teal 40, cyan 20, orange 60, purple 30). A theme change
    applies the other palette (`watchColorScheme`). Checked against
    `@carbon/colors` 11.61.0 (#327): each name is a color of the package, and
    the light hex values are the Carbon categorical palette (`#6929c4`,
    `#1192e8`, ...). `chart_indicator_styles.ts` imports the colors from the
    package.
  - `style` is `solid`, `dashed`, or `dotted`.
  - `width` is 1 to 4 pixels.
  - A new indicator gets the first palette colors that no line of the chart
    uses, one color for each line, in palette order. Its lines are `solid`
    with width 2. A histogram has a color only. When all 14 colors are in
    use, the palette starts again with the colors that the fewest lines use
    (#327).
- Crosshair: each visible line series and histogram series shows the
  crosshair marker (a dot where the line crosses the vertical crosshair
  line, `crosshairMarkerVisible`).

### 23.9.4 Legend

- Each pane has its legend at its top left, over the chart (an HTML layer
  over the canvas). Text: IBM Plex Mono, tabular numbers, Carbon
  `label-01`.
- The first row of the price pane: `O 297.31  H 301.54  L 294.82  C 300.40`.
  The letters are `--cds-text-secondary`. The values are
  `--cds-text-primary`.
- One row for each indicator: the legend name (section 23.9.2) in
  `--cds-text-secondary`, then one value for each line in the line color,
  for example `BB 20 2  191.20  185.10  179.00`. No labels.
- The values are the values at the bar of the crosshair. When the crosshair
  leaves the chart, the legend shows the values at the last bar that has
  indicator data (section 23.9.6). A line without a value shows
  "No value".
- Each line series and histogram series of a visible indicator also shows
  the value of the legend (the same bar) as a label on the price axis of
  its pane, in the line color. It is a price line with `lineVisible: false`
  and `axisLabelVisible: true`; its price follows the crosshair. A hidden
  indicator or a bar without a value shows no label.
- When the pointer is on a row, or the focus is in it, the row shows 3 ghost
  icon buttons. Each has a Bits UI `Tooltip`:
  - "Hide <legend name>" (`View`) or "Show <legend name>" (`ViewOff`). A
    hidden indicator keeps its row. The name is `--cds-text-disabled`, the
    row has no values, and the Show button stays visible.
  - "Settings for <legend name>" (`Settings`). It opens the settings
    (section 23.9.5). A click on the legend name also opens them.
  - "Remove <legend name>" (`Close`).
- Each own pane has a ghost icon button "Options for <legend name of its
  first row>" (`OverflowMenuHorizontal`) at its top right. It opens a
  Bits UI `DropdownMenu` (`foundation/carbon` `OverflowMenu`):
  - "Move up" (not on the first own pane), "Move down" (not on the last own
    pane). They change the order of the own panes.
  - "Maximize" gives the pane all the chart height (the other panes get
    height 0). Then the item is "Restore", which gives back the heights from
    before. Not saved.
  - "Remove indicators" removes the pane and all its indicators.
- The price pane has the same button with "Maximize" or "Restore" only.
- A legend that is higher than its pane scrolls in itself with a visible
  track (`ScrollRegion`, section 13.1).
- Decided (#328):
  - `lightweight-charts` 5.2.1 does not hide a pane with height 0:
    `pane.setHeight(0)` gives the minimum height of 30 pixels, and a stretch
    factor of 0 gives 2 pixels (the layout minimum). So "Maximize" sets the
    stretch factors: the pane gets all the height but 2 pixels for each
    other pane (`findMaximizedStretchFactors`). A pane of 2 pixels shows no
    legend and no options button.
  - The options button of the price pane is "Options for bars".
  - "Move up" and "Move down" move the pane height with the pane. "Move
    up", "Move down", "Remove indicators", and a new or removed pane first
    do "Restore".
  - The own panes stay in the chart while their series are drawn again
    (`setPreserveEmptyPane`), so a new value list keeps the heights that the
    user dragged. An own pane with only hidden indicators stays.
  - The legend layer takes no pointer events (the crosshair follows the
    pointer over it). The options button and the legend scroll track take
    them. The mouse wheel over a legend moves the chart, not the legend.

### 23.9.5 Add indicator and settings

- The chart panel header line has the ghost icon button "Add indicator"
  (`ChartLineData`, Bits UI `Tooltip` "Add indicator (/)"), after the bar
  period switcher. The key `/` opens the same dialog when the focus is not
  in a text field, a number field, or the code editor.
- The dialog is a Bits UI `Command` in a Carbon modal ("Add indicator"),
  in `src/lib/foundation/`. It has a search field and one list:
  - One row for each catalog indicator: the catalog `name`, and the
    `short_name` at the end in IBM Plex Mono when it is different.
  - A star icon button at the end of each row: "Add <name> to favorite
    indicators" (`Star`) or "Remove <name> from favorite indicators"
    (`StarFilled`). GLOSSARY: "Favorite indicator".
  - The favorite indicators come first, then the others, each in catalog order. No
    groups.
  - The search matches the name, the short name, and the key.
  - Enter or a click on a row adds the indicator with the catalog defaults
    and closes the dialog. A click on the star does not add.
- The favorites are saved in the chart indicator set (section 23.9.7), also
  from a backtest or forward test chart.
- The instrument page reads the chart indicator set when it opens. The
  indicators stay when the bar period or the instrument changes (#330).
- Settings (B1): a Bits UI `Popover` at the legend row. Heading: the catalog
  `name`. Content, from top to bottom:
  - One Carbon `NumberInput` for each parameter (also the parameters
    without `is_in_name`, for example `bars_per_year`). The label is the
    parameter label of the screen editor (`parameterLabel`). The range and
    the default come from the catalog route. A value out of its range, or a
    parameter order rule of section 23.6, shows the Carbon invalid text.
  - For each line, a group with the output label ("Upper", "MACD line",
    "Histogram"). The group has 3 fields:
    - the 14 palette colors as a radio group. The accessible name of each
      color is its name, for example "Purple 70".
    - "Line style": Solid, Dashed, Dotted.
    - "Width": 1 to 4.

    A histogram has the colors only.
  - "Reset to defaults" (ghost button): the catalog defaults of the
    parameters, `solid`, and width 2. The colors do not change.
  - "Apply" (primary button). It is disabled while a field is invalid,
    and a helper text line below it says why ("Fix Fast period to apply.",
    the first invalid field). It applies the changes and closes the
    popover. Escape closes the popover
    without a change.
- Decided (#329):
  - A chart without `onPanesChange` has no row buttons (as the pane
    options menu has only Maximize and Restore then).
  - The row buttons are in the tab order also while they are not shown:
    the focus in the row shows them. The legend name is a button out of the
    tab order; the Settings button gives its action to the keyboard. A row
    with buttons takes pointer events, so the crosshair does not follow the
    pointer over that row.
  - The tooltips of the row buttons go under `<body>` (`IconButton`
    `floatingTooltip`), so the legend `ScrollRegion` does not clip them. The
    popover is at the legend row. Its fields scroll between the heading and
    the buttons in a `ScrollRegion` ("Settings of <name>").
  - The line group headings: "Line" (or "Histogram") for an indicator with
    one line, "MACD line" and "Signal line" for MACD, else the output label
    ("Upper", "Histogram").
  - The invalid texts: "Enter a number.", "Enter a whole number.", "Enter a
    value from <minimum> to <maximum>.", and for an order rule "Fast period
    must be less than slow period (26)." on the smaller parameter. The
    catalog route does not give the order rules, so `indicator_settings.ts`
    holds them.
  - A hidden indicator stays in the series request, so "Show" draws the
    line again at once.
- A market data chart saves each change at once with
  `PUT /api/market-data/chart-indicators`. A failed save shows an
  `InlineNotification` with the `detail` text over the chart, and the chart
  keeps the change.

### 23.9.6 HTTP routes

All routes are in `market_data`. `market_data` imports the public entry of
`indicator` for them (new arrow `market_data -> indicator`, architecture.md
section 6.2).

| Route | Behavior |
|---|---|
| `GET /api/market-data/indicators` | `200` with the catalog in its order: the body of `GET /api/screen-indicators` (screen.md section 24.7), and `short_name` and `chart_placement` for each indicator. `GET /api/screen-indicators` gets the 2 fields too. |
| `POST /api/market-data/indicator-series` | Body `{"symbol", "exchange", "currency", "bar_period", "start_utc", "end_utc", "source_order", "indicators": [{"indicator", "parameters"}, ...]}`. `source_order` is optional: without it, the route uses the global source order. The route reads only, and changes no data. `200` with `{"times": [...], "series": [{"indicator", "parameters", "outputs": {"<output>": [...]}}, ...]}`. |
| | `times` holds the start (UNIX seconds) of each saved bar of the range, oldest first, the same as `GET /api/market-data/bars` gives for the range. Each output list has one value for each time: a number, or `null` for "no value". `parameters` holds all parameters, with the defaults. |
| | `422` for the time and range problems of the bars route and for an unknown bar period. `422` for a source order that `PUT /api/market-data/source-order` refuses. `422` for each problem of `check_indicator_reference`. Its location starts with `indicators` and the index. |
| `GET /api/market-data/chart-indicators` | `200` with the chart indicator set (section 23.9.7). |
| `PUT /api/market-data/chart-indicators` | Body: the chart indicator set. `200` with the saved set. `422` for each problem of section 23.9.7. |

- The series route never calls IBKR. It reads saved bars with
  `read_saved_bars`. The chart first reads its bars with the bars route,
  which saves them, then it asks for the series.
- Warm-up: for each indicator, the route also reads the last N saved bars
  before `start_utc`. N is `screen_look_back_bars(parameters)`
  (section 23.4). It reads them as a backtest reads the look-back bars of a
  rule builder version (backtest.md section 10.3.1). The read length is
  N × bar period × 2 for 1-day bars, and × 6 for intraday bars. It is at
  least 7 days. The route calculates
  over all bars with `update(bar)` and returns only the values of the range.
  So a chart value is equal to the screen value at the same daily bar. For
  a recursive average (EMA, RSI, ATR, MACD), a strategy value can be
  different by less than 0.005 (section 23.4).
- The bars route and the series route get the optional query and body field
  `source_order`. A backtest chart gives the `source_order` of its backtest.
- Live bars (`/ws/market-data`) have no indicator value. The indicator
  lines end at the last saved bar of the chart request. A new chart request
  (a bar period change, a page load) reads the series again.
- Decided (#327):
  - `start_utc` and `end_utc` are required. The route widens the range as
    the bars route does (whole bar periods, cut at the start of the current
    bar). The chart sends the start of its first bar and 1 second after the
    start of its last bar.
  - The `422` answers of the bars route (time, range, source order) have
    `{"detail"}`. An unknown bar period is the FastAPI `422`. The problems
    of `check_indicator_reference(reference, has_output=False)` give
    `{"problems": [{"location", "message"}]}`, for example
    `{"location": ["indicators", 0, "parameters", "period"], ...}`.
  - The route reads the warm-up bars with one read for the largest N of the
    request. Each indicator then gets the last N bars of its own count.
  - The indicators of one request each get their own class, so the same
    indicator 2 times gives the same values 2 times.

### 23.9.7 Chart indicator set

- Table `chart_indicator_set` (owner `market_data`), one row like
  `source_order`: `single_row` (primary key, always true), `panes`
  (`jsonb`), `favorites` (`jsonb`), `changed_at_utc`. The migration writes
  `{"panes": [{"indicators": []}], "favorites": []}`.
- JSON of the set:

  ```json
  {
    "panes": [
      {"indicators": [
        {"indicator": "sma", "parameters": {"period": 50}, "hidden": false,
         "lines": [{"output": "value", "color": 1, "style": "solid", "width": 2}]}
      ]},
      {"indicators": [
        {"indicator": "rsi", "parameters": {"period": 14}, "hidden": false,
         "lines": [{"output": "value", "color": 5, "style": "solid", "width": 2}]}
      ]}
    ],
    "favorites": ["sma", "rsi"]
  }
  ```

- The first pane is the price pane. The order of the other panes is the
  order on the chart.
- The `PUT` route refuses (`422`, the location of the problem):
  - no pane, or more than 4 panes,
  - an own pane without an indicator,
  - an indicator with `chart_placement` `own` in the first pane, or with
    `price` in another pane,
  - a problem of `check_indicator_reference` (without `output`),
  - `lines` that do not have each output of the indicator exactly 1 time,
  - a `color` that is not 1 to 14, a `style` that is not `solid`,
    `dashed`, or `dotted`, a `width` that is not 1 to 4,
  - a `favorites` value that is not a catalog key, or a key 2 times.
- The last `PUT` wins. Two browser tabs do not merge their changes.
- Decided (#330):
  - The `422` answer has `{"problems": [{"location", "message"}]}`, as the
    series route. The location is the path in the body, for example
    `["panes", 1, "indicators", 0, "lines", 0, "color"]`, `["panes"]` for
    the pane count, `["panes", 1, "indicators"]` for an own pane without an
    indicator, `[..., "indicator"]` for a wrong placement, `[..., "lines"]`
    for a missing output, `[..., "lines", 3, "output"]` for an unknown output
    or an output 2 times, and `["favorites", 1]` for a favorite problem. A
    body of a wrong JSON type (for example a text `color`) is the FastAPI
    `422`. Unknown fields are ignored.
  - The OpenAPI schemas are `ChartIndicatorSet`, `SavedChartPane`,
    `SavedChartIndicator`, and `SavedChartLine` (`style` is a string: the
    route checks it, so a wrong style is a problem with its location).
  - Without a row (only an emptied test database), `GET` gives the set of
    the migration.
  - Frontend: `chart_indicator_set.ts` (`readChartIndicatorSet`,
    `saveChartIndicatorSet`, `toggleFavorite`, `orderByFavorites`) and the
    class `ChartIndicatorSetStore` (`chart_indicator_set_store.svelte.ts`).
    The page that owns the store saves; `BarChart` does not save. The store
    sends one `PUT` after the other, each with the set at that time, so the
    last change is the last saved set. A change before the read answer
    keeps the changed part, and the read gives the other part.
  - A favorite change sends the saved panes back unchanged. The backtest
    and forward test pages each have their own store for the favorites only
    (no notification for a failed favorite save). When the
    read of the set failed, no change is saved: the `PUT` would save the
    part that did not load (the empty panes or the empty favorites) over
    the saved part. The page keeps the change and shows the read problem.
    The next change reads the set again and, after a good read, saves all
    changes.
  - The failed save `InlineNotification` shows the message of the first
    problem, else the `detail` text. It has a close button, because it is
    over the price pane legend. The next good save removes it.
  - `AddIndicatorButton` has the star buttons only with `onToggleFavorite`.
    `CommandDialog` items have an optional `action` (Carbon contained list
    item action, an `IconButton` with a floating tooltip). A click on it
    calls `onAction` and does not select the item.
  - Playwright tests of the instrument page chart replace the 2 routes with
    a set in the browser context (`e2e/local_chart_indicator_set.ts`), and
    `run_bar_chart.spec.ts` does the same: the set is one global row, and
    the 4 projects and other specs use one database at the same time.

### 23.9.8 Bar charts of backtests and forward tests

- The backtest panel header line and the forward test panel header line get
  a Carbon `sm` content switcher with "Equity" and "Bars". It has the size
  of the bar period switcher of the instrument page. "Equity" shows the
  `EquityDrawdownChart` (the default). "Bars" shows the bar chart. The page
  address keeps the choice (`?chart=bars`). A backtest has the switcher,
  and a single-instrument forward test has it.
- The bar chart of a backtest shows the bars of its instrument, bar period,
  and range, read with its `source_order`. A multi-instrument backtest shows
  one universe member and only the trades of that member. While "Bars" shows,
  the header line has the "Instrument" select (`ChartInstrumentSelect`): the
  members with trades come first, and the first member is the default. On
  the backtest page, a click on a Trades row or an Instruments row also
  selects the member. The member comes from `instruments` and the `currency`
  of the backtest. A backtest from before the migration has no `currency`,
  so it has no switcher. `RunChart` keeps the selected member while the run
  stays open; the page address does not keep it. The bar chart of a forward test
  shows the bars from `created_at_utc` to `stopped_at_utc`, or to now.
- Strategy indicators: `GET /api/backtests/{backtest_id}` and
  `GET /api/forward-tests/{id}` (in `forward_test`) get
  `strategy_indicators` (`[{"indicator", "parameters"}, ...]`).
  - The list comes from `CHART_INDICATORS` in the code of the strategy
    version (strategy section 9.2). All versions use this one source: code
    written by hand, code from the rule builder, and the code templates.
  - The public entry of `strategy` exports
    `list_chart_indicators(code, parameters)`. It reads `CHART_INDICATORS`
    with `ast` and does not run the code. It replaces each configuration
    field name with the value of the field: the value in `parameters` (a
    parameter sweep run), else the default value of the field.
    `list_version_chart_indicators(version, parameters)` reads the code of
    a strategy version (an empty list without the version). The backtest
    route and the forward test route use it.
  - A version without `CHART_INDICATORS` has an empty list. Its chart starts
    without indicators.
- The chart puts the strategy indicators as section 23.9.3 says, with the
  colors of a new indicator. "Add indicator", the legend buttons, and the
  settings work as on the instrument page. No change is saved, except the
  favorites.
- Decided (#331):
  - `GET /api/backtests/{backtest_id}` has `strategy_indicators` in
    `BacktestDetailResponse` (so the comparison route has it too). The
    forward test has it in `forward_test` of
    `GET /api/forward-tests/{id}` only (`ForwardTestWithIndicatorsResponse`),
    not in the list. A forward test has no sweep parameters: it uses the
    field defaults.
  - The switcher shows for each status of a backtest. A queued or failed
    backtest also shows its bars.
  - The bars route gets `start_utc`, `end_utc`, and the `source_order` of
    the backtest. A forward test sends no `end_utc` while it runs, so the
    range ends now. The bars and the indicator values are read one time for
    each run; a running forward test does not read new bars.
  - The bars route and the series route refuse a range of more than
    20000 bar lengths (`MAX_BARS_PER_REQUEST`), for example a 1-minute
    backtest of more than about 13 days. So the chart reads a longer run
    range in consecutive windows of at most 20000 bar lengths, one after
    the other, and joins the answers (`readRunBars` and
    `readRunIndicatorSeries` in `run_bars.ts`). A bar at a window border
    comes only 1 time. Each series window reads its own warm-up bars
    (section 23.9.6), so the first values of a window have a value. A failed window shows its
    message; the chart then shows no bars.
  - The changes of the user belong to the open run in the page
    (`RunChartIndicators`). Both pages use one `RunChart`
    (`run_chart.svelte.ts`: the run indicators, the favorite indicators,
    and the pointed and the selected table row), `RunAddIndicatorButton`,
    and `RunBarChart`. Another run, or a page load, starts again with
    the strategy indicators. "Equity" and "Bars" keep the changes while the
    run stays open.

### 23.9.9 Trade marks

- The bar chart of a backtest or a forward test shows each trade (GLOSSARY
  "Trade") as a mark on the price pane. A forward test split adjustment has
  no mark. The marks have no lines between trades.
- A `lightweight-charts` series primitive (`attachPrimitive` on the
  candlestick series) draws the marks. Do not use `createSeriesMarkers`.
- A trade goes on the bar with start < `time_utc` ≤ start + bar period. (A
  backtest records the fill at the bar end, `ts_event`.)
- Mark (style M3):
  - A 16 × 16 px square, `--cds-background-inverse`, with "B" (buy) or "S"
    (sell) in IBM Plex Mono semibold 11px, `--cds-text-inverse`.
  - A 4px pointer on the square points at the bar. The "B" mark is 4px
    below the bar low. The "S" mark is 4px above the bar high.
- One mark for each bar and side. When the bar spacing is less than 16px,
  marks of the same side that touch become one mark at the first bar. A
  mark touches when its bar is less than 16px from the bar of the mark
  before it on that side (the first bar of a merged mark).
- When the pointer is on a mark, the mark gets a 2px `--cds-focus` ring.
  A tooltip shows one line for each trade of the mark, in IBM Plex Mono
  with tabular numbers:
  - "Buy 50 @ 182.35"
  - "Sell 50 @ 190.10  +387.50". The signed number is the net profit of the
    round trip that the trade ends, after commissions, in
    `--cds-support-success` or `--cds-support-error`. A trade that ends no
    round trip has no number.
  - The tooltip is a Carbon popover (no high contrast, so the support
    colors keep their contrast), below a "B" mark and above an "S" mark.
  - A legend row over a mark takes the pointer first.
- Each trade of `GET /api/backtests/{backtest_id}` and each fill of
  `GET /api/forward-tests/{id}` gets `round_trip_net_profit_usd` (decimal
  text, or null). The backend calculates it with the round trip rule of the
  Instruments tab (`summarize_instruments()` of `backtest`).
- Link with the table (the backtest Trades tab, the forward test Fills
  tab):
  - A pointer on a row, or the focus on a row, gives the mark of its trade
    the `--cds-focus` ring.
  - A click on a row (or Enter) selects the row and shows "Bars". The
    chart scrolls so that the bar of the trade is in the center
    (`timeScale().setVisibleLogicalRange`, with the width of the visible
    range). The chart cannot scroll the first bar to the right
    of the left edge, so for a bar near the first bar the range is
    narrower: as many bars on each side as there are before the bar, but at
    least 10. The mark keeps the ring while its row stays selected.
  - Only a single-instrument run has "Bars", so only its rows link. A split
    adjustment row has no mark and no link.
  - The row itself takes the focus (`tabindex="0"`) and shows the Carbon
    focus (a 2px `--cds-focus` inset border, drawn on the cells). The
    selected row has `aria-current="true"` and the Carbon selected row
    color (`SelectableTableRow` in `foundation/carbon`).
- For screen readers and tests, the chart has a hidden "Trade marks" list:
  one item for each mark with the tooltip text, the mark center in chart
  pixels (`data-x`, `data-y`), and `data-ring`.

### 23.9.10 Code and tests

- Backend: `indicator_catalog.py` (the 2 fields),
  `market_data/indicator_series.py` (the series route and the warm-up),
  `market_data/chart_indicator_set.py` (table and routes),
  `strategy/chart_indicators.py` (`list_chart_indicators` and the save
  check), `CHART_INDICATORS` in `strategy/rules_code.py`, the "Blank code"
  start point, and the code templates, and the round trip field in
  `backtest` and `forward_test`.
- Backend tests: the series route gives
  the same values as the screen path for the same bars, the warm-up, the
  `422` problems, the set routes, the `CHART_INDICATORS` save check, and
  `list_chart_indicators` with field names, defaults, and a parameter sweep
  run. Each start point and rule template passes the check.
- Frontend: `#lib/market_data` holds `BarChart` with panes, legend,
  settings popover, add dialog, `chart_indicators.ts` (pure functions for
  add, remove, move, and placement), `chart_indicator_styles.ts` (palette,
  number formats), and `trade_marks.ts` (the series primitive).
  `foundation/carbon` gets `NumberInput`. `foundation` gets the `Command`
  dialog.
- Done in #327:
  - `market_data/indicator_series.py`: `list_indicator_catalog()` (also the
    body of `GET /api/screen-indicators`), the series route, and the
    warm-up.
  - `foundation/command_dialog`: `CommandDialog` (Carbon modal, Bits UI
    Command, one list, an optional action button on each item).
  - `#lib/market_data`: `AddIndicatorButton` (the header button, the `/`
    key, and the dialog), `ChartLegend` (one pane legend: the OHLC row and
    the indicator rows), `chart_indicators.ts` (`formatLegendName`,
    `addChartIndicator`, `findFreeColors`, `findLegendIndex`,
    `findIndicatorSeries`, `buildLegendRows`, `isAddIndicatorShortcut`),
    `chart_indicator_styles.ts` (`readPaletteColor`, `readPaletteColorName`,
    `formatIndicatorValue`, `readIndicatorPriceFormat`), and
    `indicator_series.ts` (`listChartIndicatorCatalog`,
    `readIndicatorSeries`, `listSeriesIndicators`). `BarChart` draws the
    price pane indicators and its legend. `ChartFrame` gets an `overlay`
    snippet for HTML over the canvas.
- Done in #328: `BarChart` draws one chart pane for each pane of the
  indicators (line series, histogram series, the RSI price lines),
  `ChartPaneOverlay` (the legend in a `ScrollRegion` and the options menu
  of one pane), `chart_indicators.ts` (`removeChartIndicator`,
  `moveOwnPane`, `removeOwnPane`, `listPaneActions`,
  `findMaximizedStretchFactors`), `chart_indicator_styles.ts`
  (`isHistogramLine`, `RSI_GUIDE_LEVELS`), and the `horizontal` icon of
  `OverflowMenu`. `BarChart` gets `onPanesChange` for the menu changes.
- Done in #329: the legend row buttons (`ChartLegend` `actions`) and the
  settings popover (`IndicatorSettings`), `indicator_settings.ts`
  (`createSettingsDraft`, `checkSettingsDraft`, `resetSettingsDraft`,
  `applySettingsDraft`, `replaceChartIndicator`, `formatParameterLabel`,
  `formatLineLabel`), and `foundation/carbon` `NumberInput`. `LegendRow`
  gets `indicatorIndex` and `hidden`.
- Done in #331: `strategy_indicators` of the 2 detail routes,
  `readBars` with an optional range and source order, `RunBarChart` (the
  bar chart of a run range), `RunChartIndicators` (the panes of a run chart),
  `strategy_indicators.ts` (`placeStrategyIndicators`), and in
  `#lib/backtest` `ChartViewSwitcher` and `chart_view.ts` (`readChartView`,
  `formatChartViewSearch`). Tests: `test_strategy_indicators.py`,
  `e2e/run_bar_chart.spec.ts` (the e2e server has a stopped forward test of
  "E2E chart indicators" on 45 saved FTBAR bars). `RunBarChart` passes
  `onPanesChange`, so the legend buttons and the settings of #329 work on
  these charts.
- Done in #332: `round_trip_net_profit_usd` (`find_round_trip_net_profits`
  in `backtest/universe_instruments.py`), `trade_marks.ts`
  (`TradeMarksPrimitive`, `findTradeBarIndex`, `groupTradeMarks`,
  `mergeTouchingMarks`, `layoutTradeMarks`, `findMarkAt`,
  `formatTradeLine`, `readCenteredRange`, `listChartTrades`),
  `TradeMarkLayer` (the tooltip and the "Trade marks" list), the `trades`,
  `barPeriod`, `ringTrades`, and `centerTrade` props of `BarChart` and
  `RunBarChart`, and `foundation/carbon` `SelectableTableRow` (the linked
  rows of `BacktestTradeTable` and `ForwardTestFillTable`). Tests:
  `test_round_trip_net_profit.py`, `trade_marks.test.ts`, and
  `e2e/trade_marks.spec.ts` (the e2e server has the finished backtest of
  "E2E trade marks" with 5 trades and 2 fills on the forward test of "E2E
  chart indicators").
- Playwright: the 4 projects (chromium, firefox, webkit, msedge) for each
  UI slice.

### 23.9.11 Left to the implementation

Nothing now. The height 0 check is in section 23.9.4 (#328).
