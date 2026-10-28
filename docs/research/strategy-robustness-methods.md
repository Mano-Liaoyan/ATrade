# Strategy robustness methods and new metrics

Research for issue [#132](https://github.com/Mano-Liaoyan/ATrade/issues/132)
of the map [#129](https://github.com/Mano-Liaoyan/ATrade/issues/129).

Question: which methods find an overfit strategy? What does each method
need, and how much does it cost to compute? Which minimal set must ATrade
add first? What are the exact definitions of the new metrics?

Terms follow `GLOSSARY.md`: metric, backtest, forward test, equity curve,
round trip, win rate, net profit, paper capital, bar period, instrument,
strategy version.

## 1. Short answer

1. A backtest overfits when the user (or an AI assistant) tries many
   strategy versions or parameter sets and keeps the best one. The best
   backtest then shows mostly luck. All methods below measure or remove
   this selection effect.
2. ATrade has 1 instrument per backtest, no parameter sweep yet, and a user
   who is not a statistician. The minimal first set is:
   - **New metrics** (section 4): annualized return (CAGR), annualized
     volatility, Sharpe ratio, Sortino ratio, Calmar ratio, profit factor,
     average win, average loss, exposure time, turnover. All come from the
     equity curve and the trades that ATrade already saves. Cost: one pass
     over the data.
   - **Probabilistic Sharpe ratio (PSR)** with the number of tries `N`
     (section 3.3): ATrade counts the backtests of the same strategy, same
     instrument, and same bar period, and shows the Deflated Sharpe ratio
     (DSR) when `N > 1`. Cost: one pass over the daily returns.
   - **Out-of-sample split** (section 3.1): the user marks the last part of
     the range (default 30 %) as out-of-sample. ATrade shows the metrics of
     the in-sample part and the out-of-sample part side by side. Cost: no
     extra backtest. ATrade splits the equity curve of one backtest.
3. Add later, when the parameter sweep exists (map step 3):
   walk-forward analysis (section 3.2), parameter sensitivity (section 3.6),
   and the Probability of Backtest Overfitting with CSCV (section 3.4).
4. Do not add in the first version: White's Reality Check, Hansen's SPA,
   purged and combinatorial purged cross-validation, Monte Carlo of trade
   order. Section 3 gives the reasons.

## 2. Why one backtest is not sufficient

- Bailey, Borwein, López de Prado, and Zhu show that with daily data, a
  researcher who tries enough configurations always finds one with a high
  in-sample Sharpe ratio, also when the true Sharpe ratio of all
  configurations is 0. They give the Minimum Backtest Length: for 5 years
  of daily data, about 45 independent tries are sufficient to find an
  annualized in-sample Sharpe ratio of 1 by luck [BBLZ14].
- Harvey, Liu, and Zhu count 316 published factors. They conclude that a
  new factor must have a t-statistic above 3.0, not above 2.0, because of
  multiple testing [HLZ16]. Harvey and Liu apply the same idea to trading
  strategies: they reduce ("haircut") the Sharpe ratio by the number of
  tries [HL15].
- The t-statistic of a Sharpe ratio is about `SR_annual × sqrt(years)`
  [Lo02]. So `t > 3` needs, for example, an annualized Sharpe ratio of 1.34
  over 5 years, or 0.95 over 10 years.
- Consequence for ATrade: the number of tries is the most important input.
  ATrade saves each backtest with its strategy version, so ATrade can count
  the tries. Most retail products cannot.

## 3. Methods

Each subsection gives the inputs, the computation cost, a way to show the
result to a user who is not an expert, and the pitfalls. `T` is the number
of return observations. `N` is the number of tries (strategy versions or
parameter sets). `B` is the number of bootstrap samples.

### 3.1 In-sample and out-of-sample split (holdout)

- **Method**: the user develops the strategy on the first part of the data
  (in-sample, IS). The user then runs the strategy one time on the last
  part (out-of-sample, OOS) and does not change it after that run
  [Pardo08, ch. on optimization; AFML18 ch. 11].
- **Inputs**: one equity curve, one split time.
- **Cost**: zero extra backtests when the strategy has no fitted state.
  ATrade calculates the metrics on 2 parts of one equity curve.
- **Show it**: two columns of the same key metrics, "In-sample" and
  "Out-of-sample", and a vertical line at the split time on the equity
  chart. Show the OOS Sharpe ratio as a share of the IS Sharpe ratio. Pardo
  calls the similar ratio of annualized returns "walk-forward efficiency"
  and accepts about 50 % to 60 % or more [Pardo08].
- **Pitfalls**:
  - The OOS part is clean only one time. When the user looks at the OOS
    result and changes the strategy, the OOS part becomes in-sample
    [AFML18 ch. 11]. ATrade can count the backtests that include the OOS
    range and show a warning.
  - A short OOS part has a large error. One year of daily data gives a
    Sharpe ratio standard error of about 1.0 (annualized) [Lo02].
  - One split tests one market period only (for example a bull market).

### 3.2 Walk-forward analysis

- **Method**: optimize the parameters on a window of `k` bars, test the
  best parameters on the next `m` bars, move both windows forward by `m`,
  and repeat. Join all OOS parts into one OOS equity curve [Pardo08].
  Windows can be rolling (fixed length) or anchored (start fixed).
- **Inputs**: a parameter grid, a window length, a step length, an
  objective metric (for example the Sharpe ratio).
- **Cost**: (number of windows) × (grid size) backtests. For example, 10
  windows × 50 parameter sets = 500 backtests. With the current backtest
  limits (concurrency 1 by default), this needs a parameter sweep runner
  first.
- **Show it**: one joined OOS equity curve, a table of windows (IS
  period, chosen parameters, OOS return), and the walk-forward efficiency.
  Parameters that change much from window to window show an unstable
  strategy.
- **Pitfalls**:
  - It tests only one path through history. López de Prado shows that a
    single walk-forward path overfits easily when the user repeats it with
    changes [AFML18 ch. 11, ch. 12].
  - The first IS window gives no OOS data, so less data is tested.
  - The window length is a parameter too, and the user can tune it.

### 3.3 Probabilistic Sharpe ratio and Deflated Sharpe ratio

- **PSR** [BLdP12]: the probability that the true Sharpe ratio is above a
  benchmark `SR*`, given the observed Sharpe ratio, the sample length, and
  the skewness and kurtosis of the returns.

  ```text
  PSR(SR*) = Φ( (SR^ − SR*) × sqrt(T − 1)
                / sqrt(1 − γ3 × SR^ + ((γ4 − 1) / 4) × SR^²) )
  ```

  - `SR^`: the observed Sharpe ratio, **not annualized**, at the frequency
    of the returns (daily).
  - `γ3`: skewness of the returns. `γ4`: kurtosis (not excess kurtosis, so
    a normal distribution gives 3).
  - `Φ`: the standard normal cumulative distribution function.
  - QuantConnect LEAN uses this formula with `SR* = 0` by default
    [LEAN].
- **DSR** [BLdP14]: the PSR with a benchmark `SR0` that is the expected
  maximum Sharpe ratio of `N` tries when all true Sharpe ratios are 0.

  ```text
  SR0 = sqrt(V[SR_n]) × ( (1 − γ) × Φ⁻¹(1 − 1/N) + γ × Φ⁻¹(1 − 1/(N × e)) )
  DSR = PSR(SR0)
  ```

  - `V[SR_n]`: the variance of the (not annualized) Sharpe ratios of the
    `N` tries. `γ ≈ 0.5772` (Euler-Mascheroni constant). `e`: Euler's
    number.
  - `N` is the number of **independent** tries. Correlated tries count as
    fewer. The paper suggests clustering of the tries' returns to estimate
    the effective `N` [BLdP14].
- **Inputs**: the daily returns of the chosen backtest. For DSR also `N`
  and the Sharpe ratios of all tries.
- **Cost**: one pass over the returns. Trivial.
- **Show it**: one percent with a word, for example "Sharpe ratio above 0:
  93 % probability (12 tries counted)". Use a status word with its color:
  at or above 95 % "Likely real", 50 % to 95 % "Uncertain", below 50 %
  "Likely luck". The thresholds are a product decision. The paper uses
  95 % as an example [BLdP14].
- **Pitfalls**:
  - `N` is the critical input. When the user tries ideas outside ATrade,
    ATrade does not know them. Count what ATrade can see and say what the
    count includes.
  - When `N = 1`, `V[SR_n]` is not defined. Show PSR with `SR* = 0` only.
  - It needs enough returns. With fewer than about 60 daily returns,
    skewness and kurtosis are not reliable. Show "–" and the reason.
  - Use the same return frequency as the Sharpe ratio (daily, section 4.1).

### 3.4 Probability of Backtest Overfitting (PBO) with CSCV

- **Method** [BBLZ17]: build a matrix `M` of `T` rows (time) and `N`
  columns (tries), each cell a return. Split the rows into `S` blocks
  (`S` even, for example 16). For each of the `C(S, S/2)` ways to choose
  half of the blocks as IS (the rest is OOS):
  1. Find the try `n*` with the best IS Sharpe ratio.
  2. Find the relative rank `ω` of `n*` in the OOS Sharpe ratios
     (between 0 and 1).
  3. Calculate the logit `λ = ln(ω / (1 − ω))`.

  PBO is the share of combinations with `λ ≤ 0`: the share in which the
  best IS try is at or below the OOS median.
- **Inputs**: the return series of all `N` tries over the same dates.
  This needs a parameter sweep (`N` at least about 10 to be useful).
- **Cost**: `C(S, S/2)` combinations × `N` Sharpe ratios. With `S = 16`
  this is 12,870 combinations. No new backtests. Seconds in NumPy.
- **Show it**: one percent: "Chance that the best parameter set is
  overfit: 38 %". Add a histogram of `λ` for advanced users. The paper
  also gives the "performance degradation" plot (IS Sharpe ratio against
  OOS Sharpe ratio), which a user can read without statistics.
- **Pitfalls**:
  - It measures the selection process, not one strategy version.
  - Blocks break serial dependence at the block borders. Use long blocks.
  - With few tries (`N < 10`) the rank `ω` is coarse.

### 3.5 Multiple-testing corrections: White's Reality Check, Hansen's SPA, Harvey-Liu-Zhu

- **White's Reality Check** [White00]: tests the null hypothesis "the best
  of `N` strategies is not better than a benchmark". It uses the stationary
  bootstrap of Politis and Romano [PR94] on the performance differences.
- **Hansen's SPA** [Hansen05]: the same test with a studentized statistic
  and less weight for very poor strategies. It has more power than the
  Reality Check. Romano and Wolf give a stepwise version that finds all
  strategies that beat the benchmark [RW05].
- **Harvey-Liu-Zhu** [HLZ16, HL15]: Bonferroni, Holm, and
  Benjamini-Hochberg-Yekutieli adjustments of p-values, and a Sharpe ratio
  "haircut".
- **Inputs**: return series of all `N` tries (and a benchmark).
- **Cost**: `B × N` (for example 1,000 × 100). Seconds to minutes.
- **Show it**: an adjusted p-value. Most users cannot read a p-value
  without help.
- **Pitfalls**: more inputs (bootstrap block length) and harder to show
  than DSR and PBO, which answer the same question. **Not in the first
  version.** DSR covers the multiple-testing effect for one chosen try.
  PBO covers it for a sweep.

### 3.6 Parameter sensitivity

- **Method**: vary each parameter around the chosen value and plot the
  metric. A robust strategy has a broad "plateau". An overfit strategy has
  a narrow "peak" [Pardo08].
- **Inputs**: a parameter grid around the chosen value.
- **Cost**: (grid size) backtests. For example, ±50 % in 5 steps for 2
  parameters = 25 backtests.
- **Show it**: a line chart (1 parameter) or a heatmap (2 parameters) of
  the Sharpe ratio, with the chosen value marked. This is easy for a user
  who is not an expert, and TradingView and QuantConnect users know it.
- **Pitfalls**:
  - More than 2 parameters cannot show in one chart. Show pairs.
  - The plateau is in-sample. A plateau does not prove OOS performance.
  - The sweep itself adds tries to `N` for the DSR.

### 3.7 Purged k-fold and combinatorial purged cross-validation

- **Method** [AFML18 ch. 7, ch. 12]: k-fold cross-validation for models
  that are fitted to labels that span time. "Purging" removes training
  observations whose labels overlap the test period. "Embargo" removes a
  small period after each test fold. Combinatorial purged CV (CPCV) gives
  many backtest paths instead of one walk-forward path.
- **Inputs**: a fitted model (for example a machine learning classifier)
  with labels and their time spans.
- **Cost**: k fits (purged CV) or `C(k, k − j)` fits (CPCV).
- **Pitfalls and decision**: ATrade strategies are rule code with
  parameters, not fitted models with labels. **Not in the first version.**
  Use these methods only when ATrade adds strategies that train a model.

### 3.8 Monte Carlo resampling

Two different methods use this name.

- **Trade-order shuffle or trade bootstrap**: resample the round trips (with
  or without replacement) and rebuild many equity curves. It gives a
  distribution of the max drawdown and of the final equity. Cost: `B`
  passes over the round trips (for example 1,000). Show it: a fan of
  equity curves and "95 % of the paths have a max drawdown below 31 %".
  Pitfalls: it assumes that round trips are independent. It keeps the
  edge of the strategy, so it does **not** test overfitting. It shows
  only path risk. A shuffle without replacement does not change the final
  equity.
- **Block bootstrap of returns** [PR94]: keeps serial dependence. It is
  the engine of White's Reality Check and Hansen's SPA (section 3.5).
- **Decision**: not in the first version. The trade bootstrap of the max
  drawdown is a cheap later addition, but label it as path risk, not as an
  overfitting test.

### 3.9 Summary table

| Method | Inputs | Extra backtests | Detects overfitting | First version |
|---|---|---|---|---|
| New metrics (section 4) | equity curve, trades | 0 | no | yes |
| PSR / DSR | daily returns, `N`, Sharpe ratios of tries | 0 | yes (selection) | yes |
| IS/OOS split | equity curve, split time | 0 | yes (one time) | yes |
| Walk-forward | grid, windows | windows × grid | yes | later |
| Parameter sensitivity | grid | grid | partly | later |
| PBO (CSCV) | returns of all tries | 0 after sweep | yes (process) | later |
| Reality Check / SPA | returns of all tries, benchmark | 0 after sweep | yes | no |
| Purged CV / CPCV | fitted model, labels | k fits | yes | no |
| Monte Carlo of trades | round trips | 0 | no (path risk) | later |

## 4. Metric definitions

### 4.1 Common rules

- **Return series**: ATrade calculates the return metrics from **daily
  returns**, also for backtests with intraday bar periods. Take the last
  equity point of each trading day (exchange time zone of the instrument)
  and calculate `r_d = E_d / E_(d−1) − 1`. The first `E_(d−1)` is the paper
  capital. Reasons:
  - Intraday returns have strong intraday seasonality and overnight gaps.
    The annualization factor for intraday bars depends on the trading hours
    (6.5 hours on US exchanges, 5.5 hours on HKEX), and a wrong factor
    changes the Sharpe ratio by a large amount.
  - Backtests with different bar periods then give comparable metrics.
  - LEAN calculates its statistics from daily performance with a
    `tradingDaysPerYear` parameter [LEAN].
- **Annualization factor**: `A = 252` trading days per year for US and
  Hong Kong stocks. HKEX has about 245 to 250 trading days. The difference
  changes `sqrt(A)` by less than 1.5 %, so one value is sufficient. Write
  `A` in the metric documentation.
- **Risk-free rate**: `r_f = 0` in the first version. Reasons: the result
  stays comparable between backtests and forward tests, it needs no new
  data source, and LEAN defaults to 0 in its PSR [LEAN]. TradingView uses
  2 % per year by default, with monthly returns [TV-Sharpe], so ATrade
  numbers will differ from TradingView numbers. Show "Risk-free rate: 0"
  in the tooltip of the metric. A later version can use a daily rate
  `r_f,d = (1 + r_f,annual)^(1/A) − 1`.
- **Minimum length**: when the backtest has fewer than 2 daily returns,
  the ratio metrics are "–". When the standard deviation is 0, the ratio is
  "–", not infinite.
- **Standard deviation**: sample standard deviation (divide by `n − 1`).
- **Currency**: the metrics use the equity curve in its currency (section
  10.8 of `docs/architecture/backtest.md` converts instruments that are not
  in USD). Ratios do not depend on the currency.

### 4.2 Definitions

`n` is the number of daily returns. `E_0` is the paper capital (or the
start balance of a forward test). `E_end` is the final equity. `years` is
`(end_utc − start_utc) / 365.25 days`.

| Metric | Definition | Notes |
|---|---|---|
| Annualized return (CAGR) | `(E_end / E_0)^(1 / years) − 1` | Calendar years, as in LEAN `CompoundingAnnualPerformance` [LEAN]. A CAGR of a few weeks of data is very large and has no meaning. The product can show "–" below a minimum length (for example 90 days) and show the reason. |
| Annualized volatility | `stdev(r_d) × sqrt(A)` | Percent. |
| Sharpe ratio | `mean(r_d − r_f,d) / stdev(r_d − r_f,d) × sqrt(A)` | Arithmetic mean of daily returns [Sharpe94]. The `sqrt(A)` scaling is correct only for returns without serial correlation. Lo gives the correction factor `η(q) = q / sqrt(q + 2 Σ_{k=1}^{q−1} (q − k) ρ_k)` [Lo02]. Use `sqrt(A)` in the first version and state it. Note: LEAN annualizes the mean as `(1 + mean)^A − 1` and divides by the annual standard deviation [LEAN], which gives a slightly different number. |
| Sortino ratio | `mean(r_d − MAR_d) / DD × sqrt(A)`, with `DD = sqrt( Σ min(0, r_d − MAR_d)² / n )` | `MAR = 0`. The downside deviation uses **all** `n` days in the denominator, with 0 for the days above the MAR [SP94]. LEAN instead takes the variance of only the returns below the MAR [LEAN]. The two give different numbers. ATrade uses the Sortino-Price definition and documents it. |
| Max drawdown | as now: largest fall from a peak, percent of the peak, paper capital as first peak | Use the equity curve at bar resolution, not daily, so the value does not change. |
| Calmar ratio | `CAGR / |max drawdown|` | Young used the last 36 months [Young91]. ATrade uses the whole backtest range and states it. "–" when the max drawdown is 0. |
| Profit factor | `Σ profit of winning round trips / |Σ profit of losing round trips|` | After commissions. Same as TradingView "gross profit / gross loss" [TV-PF]. "–" when there is no losing round trip. Uses round trips (the glossary term), not single trades. |
| Average win | mean profit (USD) of the round trips with a profit after commissions | Also show it as a percent of the entry value. |
| Average loss | mean profit (USD, negative) of the round trips with a loss after commissions | Average win / |average loss| is the "payoff ratio". |
| Exposure time | share of bars in which the position is not 0 | Count the bars of the range. A position that opens and closes in the same bar does not count. Percent. |
| Turnover | `Σ |quantity × price| of all trades / mean(E) / years` | Annualized, as a multiple of the mean equity ("3.2× per year"). One round trip of the full capital gives 2× (buy + sell). Some sources count only one side (divide by 2). ATrade counts both sides and states it. |

### 4.3 Order of key metrics

The current `KeyMetricRow` shows Total return, Net profit, Max drawdown,
Win rate, Trades, Final equity. The frontend design rules say that all
pages show the same key metrics in the same order. A proposal for the
grilling ticket: keep the key row short and add a second table "All
metrics" with the full list of section 4.2, PSR, and DSR. Add Sharpe
ratio to the key row after Max drawdown, because users of TradingView and
QuantConnect look for it first.

## 5. Recommended minimal first version

1. Add the metrics of section 4.2 to `calculate_metrics` and save them with
   the backtest and the forward test (same functions, section 12.10 of the
   architecture).
2. Add PSR (`SR* = 0`) and DSR. `N` = the number of finished backtests of
   the same strategy (all versions), instrument, and bar period. Show `N`
   next to the value.
3. Add an optional OOS split time to the backtest request. Show IS and OOS
   metrics side by side, and count the backtests that include the OOS
   range.
4. Later, with the parameter sweep: parameter sensitivity chart,
   walk-forward analysis, PBO with CSCV. They share one runner: a set of
   backtests with one strategy and different parameters.

All items of the first version run on the data that one backtest already
saves. They need no new backtests and no new data source.

## 6. Sources

- [BLdP12] Bailey, D. H., López de Prado, M. (2012). The Sharpe Ratio
  Efficient Frontier. Journal of Risk 15(2). SSRN 1821643.
  <https://papers.ssrn.com/sol3/papers.cfm?abstract_id=1821643>
- [BLdP14] Bailey, D. H., López de Prado, M. (2014). The Deflated Sharpe
  Ratio: Correcting for Selection Bias, Backtest Overfitting and
  Non-Normality. Journal of Portfolio Management 40(5), 94–107. SSRN
  2460551. <https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2460551>
- [BBLZ14] Bailey, D. H., Borwein, J. M., López de Prado, M., Zhu, Q. J.
  (2014). Pseudo-Mathematics and Financial Charlatanism: The Effects of
  Backtest Overfitting on Out-of-Sample Performance. Notices of the AMS
  61(5), 458–471. <https://www.ams.org/notices/201405/rnoti-p458.pdf>
- [BBLZ17] Bailey, D. H., Borwein, J. M., López de Prado, M., Zhu, Q. J.
  (2017). The Probability of Backtest Overfitting. Journal of
  Computational Finance 20(4), 39–69. SSRN 2326253.
  <https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2326253>
- [HLZ16] Harvey, C. R., Liu, Y., Zhu, H. (2016). … and the Cross-Section
  of Expected Returns. Review of Financial Studies 29(1), 5–68.
  <https://doi.org/10.1093/rfs/hhv059>
- [HL15] Harvey, C. R., Liu, Y. (2015). Backtesting. Journal of Portfolio
  Management 42(1), 13–28. SSRN 2345489.
  <https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2345489>
- [White00] White, H. (2000). A Reality Check for Data Snooping.
  Econometrica 68(5), 1097–1126. <https://doi.org/10.1111/1468-0262.00152>
- [Hansen05] Hansen, P. R. (2005). A Test for Superior Predictive
  Ability. Journal of Business & Economic Statistics 23(4), 365–380.
  <https://doi.org/10.1198/073500105000000063>
- [RW05] Romano, J. P., Wolf, M. (2005). Stepwise Multiple Testing as
  Formalized Data Snooping. Econometrica 73(4), 1237–1282.
- [PR94] Politis, D. N., Romano, J. P. (1994). The Stationary Bootstrap.
  JASA 89(428), 1303–1313.
- [Lo02] Lo, A. W. (2002). The Statistics of Sharpe Ratios. Financial
  Analysts Journal 58(4), 36–52. <https://doi.org/10.2469/faj.v58.n4.2453>
- [Pardo08] Pardo, R. (2008). The Evaluation and Optimization of Trading
  Strategies, 2nd ed. Wiley. (Walk-forward analysis and walk-forward
  efficiency.)
- [AFML18] López de Prado, M. (2018). Advances in Financial Machine
  Learning. Wiley. Ch. 7 (purged k-fold CV, embargo), ch. 11 (dangers of
  backtesting), ch. 12 (CPCV), ch. 14 (backtest statistics, PSR, DSR).
- [Sharpe94] Sharpe, W. F. (1994). The Sharpe Ratio. Journal of Portfolio
  Management 21(1), 49–58.
- [SP94] Sortino, F. A., Price, L. N. (1994). Performance Measurement in a
  Downside Risk Framework. Journal of Investing 3(3), 59–64.
- [Young91] Young, T. W. (1991). Calmar Ratio: A Smoother Tool. Futures
  20(1), 40.
- [LEAN] QuantConnect LEAN, `Common/Statistics/Statistics.cs` (Apache
  2.0): `SharpeRatio`, `SortinoRatio`, `AnnualDownsideStandardDeviation`,
  `CompoundingAnnualPerformance`, `ProbabilisticSharpeRatio`.
  <https://github.com/QuantConnect/Lean/blob/master/Common/Statistics/Statistics.cs>
- [TV-Sharpe] TradingView Help Center, Sharpe ratio (monthly returns,
  default risk-free rate 2 %, `risk_free_rate` of `strategy()`).
  <https://www.tradingview.com/support/solutions/43000681694-sharpe-ratio/>
- [TV-PF] TradingView Help Center, Profit factor.
  <https://www.tradingview.com/support/solutions/43000681698-profit-factor/>

Not verified against the full text in this research: the page numbers of
Pardo08 and the exact wording of Young91. The formulas of BLdP12, BLdP14,
and BBLZ17 match the LEAN implementation of PSR [LEAN].
