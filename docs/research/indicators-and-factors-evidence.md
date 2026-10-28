# Evidence for classic indicators and factors

Research for issue [#130](https://github.com/Mano-Liaoyan/ATrade/issues/130),
part of the map [#129](https://github.com/Mano-Liaoyan/ATrade/issues/129).
Date: 2026-10-28.

## Answer

1. Price trend (moving average) and momentum (12-1 month return) have the
   strongest evidence of all price-based indicators. Time-series trend rules
   on indexes and cross-sectional momentum on stocks keep a return after
   realistic costs. Momentum is weak in Japan and in some Asian markets, and
   it has large crashes.
2. Value, profitability/quality, and low volatility (low beta) keep evidence
   after costs and after publication. They have low turnover, so costs are
   small. Their returns became smaller after publication.
3. Size alone is weak after the 1980s. Short-term reversal and post-earnings
   drift are real in gross returns, but transaction costs remove most of the
   return for a small trader.
4. Oscillator indicators (RSI, MACD, Bollinger Bands) have little reliable
   peer-reviewed evidence of a net return on stocks after costs and after a
   data-snooping correction. Use them as filters or as entry timing, not as
   the source of the return.
5. ATR and volume do not predict return directly. ATR has a good use for risk
   control (stop distance and position size). Volume is a good liquidity
   screen condition.
6. Hong Kong evidence: studies found value and size effects in Hong Kong data. Low beta
   and quality are in the international samples that include Hong Kong.
   Momentum is weaker in Asia than in the US. Technical trading rules gave
   little profit in Hong Kong in early tests.

## Terms

This document uses the terms in [`GLOSSARY.md`](../../GLOSSARY.md):
Instrument, Bar, Strategy, Backtest, Metric.

`GLOSSARY.md` does not yet define these terms. This document uses them with
these working meanings:

- **Indicator**: a value that a function calculates from the bars or the
  financial data of one instrument, for example a 50-day moving average.
- **Factor**: an indicator that the research uses to rank many instruments
  against each other, for example book-to-market.
- **Screen**: a set of conditions on indicators. It selects instruments from
  a list.
- **Screen result**: the instruments that agree with all conditions of a
  screen at one time.

## How to read the evidence levels

| Level | Meaning |
|---|---|
| A | Many peer-reviewed studies. The effect replicates out of sample and in many countries. It stays after realistic costs. |
| B | Peer-reviewed evidence exists and replicates. It is smaller after publication, or costs remove a large part of it, or it is weak in some markets. |
| C | Original study only, or results that do not stay after costs or after a data-snooping correction. |
| D | Practitioner use only. No reliable peer-reviewed evidence of a return. |

## General findings on decay and replication

- McLean and Pontiff studied 97 return predictors. Returns were 26% lower out
  of sample and 58% lower after publication
  ([McLean & Pontiff 2016, JF](https://doi.org/10.1111/jofi.12365)).
- Hou, Xue, and Zhang replicated 452 anomalies with value weights and NYSE
  breakpoints. 65% did not pass |t| ≥ 1.96. With the multiple-test hurdle
  |t| ≥ 2.78, 82% did not pass. Most failures were liquidity and trading
  frictions anomalies that live in microcaps
  ([Hou, Xue & Zhang 2020, RFS](https://doi.org/10.1093/rfs/hhy131)).
- Harvey, Liu, and Zhu recommend a t-statistic above 3.0 for a new factor,
  because many researchers tested the same data
  ([Harvey, Liu & Zhu 2016, RFS](https://doi.org/10.1093/rfs/hhv059)).
- Jensen, Kelly, and Pedersen found that most factors replicate when the
  test uses a Bayesian method across 153 factors and 93 countries. They group
  the factors into 13 themes, for example value, momentum, quality, and low
  risk ([Jensen, Kelly & Pedersen 2023, JF](https://doi.org/10.1111/jofi.13249)).
  Their data covers Hong Kong ([jkpfactors.com](https://jkpfactors.com)).
- Chen and Zimmermann reproduced 319 published predictors from the original
  papers ([Chen & Zimmermann 2022, Critical Finance Review](https://doi.org/10.1561/104.00000112)).

### Transaction costs

- Novy-Marx and Velikov measured the costs of 23 anomalies. Anomalies with
  turnover below about 50% per month (value, profitability, size, low
  volatility) keep most of the return after costs. Momentum keeps a part.
  High-turnover anomalies (short-term reversal, and others) lose the return
  ([Novy-Marx & Velikov 2016, RFS](https://doi.org/10.1093/rfs/hhv063)).
- AQR measured the costs of its own live trades, about 1.7 trillion USD from
  1998 to 2016. The real costs were much lower than the academic estimates.
  Value, size, momentum, and short-term reversal stayed profitable at a large
  scale with their costs
  ([Frazzini, Israel & Moskowitz 2018, SSRN 3229719](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3229719)).
  A personal trader with retail commissions and no smart order routing has
  higher costs than AQR.

## Factors

### Value

- Definition: book-to-market (B/M), earnings-to-price (E/P), cash-flow-to-
  price, or a composite. HML in the Fama-French 3-factor model
  ([Fama & French 1993, JFE](https://doi.org/10.1016/0304-405X(93)90023-5)).
- International: value premium in many markets and asset classes
  ([Asness, Moskowitz & Pedersen 2013, JF](https://doi.org/10.1111/jofi.12021)),
  and in the Asia Pacific region
  ([Fama & French 2012, JFE](https://doi.org/10.1016/j.jfineco.2012.05.011)).
- Hong Kong: B/M explains returns in Hong Kong data
  ([Chui & Wei 1998, Pacific-Basin Finance Journal](https://doi.org/10.1016/S0927-538X(98)00013-4)).
  Size, B/M, and E/P explain Hong Kong returns in a second study
  ([Lam 2002, Global Finance Journal](https://doi.org/10.1016/S1044-0283(02)00049-8)).
- Decay: the US value premium was much smaller in 1991–2019 than in
  1963–1991 ([Fama & French 2021, RAPS](https://doi.org/10.1093/rapstu/raab001)).
- Costs: low turnover. Value keeps its return after costs (Novy-Marx &
  Velikov 2016).
- Level: **B**. Real and global, but weak in the US since about 2007.

### Momentum (cross-sectional)

- Definition: the return from month t−12 to month t−2. The research skips
  the last month because of short-term reversal
  ([Jegadeesh & Titman 1993, JF](https://doi.org/10.1111/j.1540-6261.1993.tb04702.x)).
  UMD in the Carhart 4-factor model
  ([Carhart 1997, JF](https://doi.org/10.1111/j.1540-6261.1997.tb03808.x)).
- Index providers: MSCI Momentum Indexes use 6-month and 12-month price
  momentum, scaled by volatility
  ([MSCI Momentum Indexes methodology](https://www.msci.com/index-methodology)).
- Risk: momentum has large crashes after market rebounds, for example in
  2009. Volatility scaling reduces the crashes
  ([Daniel & Moskowitz 2016, JFE](https://doi.org/10.1016/j.jfineco.2015.12.003),
  [Barroso & Santa-Clara 2015, JFE](https://doi.org/10.1016/j.jfineco.2014.11.010)).
- Asia: Fama and French found momentum in all regions except Japan (Fama &
  French 2012). Momentum is weak in Asian countries with low individualism
  ([Chui, Titman & Wei 2010, JF](https://doi.org/10.1111/j.1540-6261.2009.01532.x)).
  Asian momentum profits were small and not significant in a 17-country study
  ([Griffin, Ji & Martin 2003, JF](https://doi.org/10.1046/j.1540-6261.2003.00614.x)).
- Volume: momentum is stronger in stocks with high past turnover, and its
  reversal is faster ([Lee & Swaminathan 2000, JF](https://doi.org/10.1111/0022-1082.00280)).
- Costs: medium turnover. A part of the return stays after costs (Novy-Marx &
  Velikov 2016).
- Level: **A** in the US and Europe. **B** in Hong Kong.

### Time-series momentum and trend

- Definition: hold an instrument long when its own past 12-month return is
  positive ([Moskowitz, Ooi & Pedersen 2012, JFE](https://doi.org/10.1016/j.jfineco.2011.11.003)).
  This study used futures, not single stocks.
- Moving-average rule: hold an index when its price is above the 10-month
  simple moving average. The rule reduced drawdown with a similar return
  ([Faber 2007, Journal of Wealth Management](https://doi.org/10.3905/jwm.2007.674809)).
- Level: **B** for indexes and futures. **C** for a single stock alone.

### 52-week high

- Definition: the close price divided by the highest price of the last 52
  weeks. Stocks near their 52-week high do better than stocks far from it.
  The 52-week high explains a large part of momentum
  ([George & Hwang 2004, JF](https://doi.org/10.1111/j.1540-6261.2004.00695.x)).
- Level: **B**. Low data cost: daily bars only.

### Quality and profitability

- Gross profitability: (revenue − cost of goods sold) / total assets. It
  predicts returns as well as B/M does
  ([Novy-Marx 2013, JFE](https://doi.org/10.1016/j.jfineco.2013.01.003)).
- RMW (operating profitability) and CMA (investment) are in the Fama-French
  5-factor model ([Fama & French 2015, JFE](https://doi.org/10.1016/j.jfineco.2014.10.010)).
  The q-factor model has similar factors
  ([Hou, Xue & Zhang 2015, RFS](https://doi.org/10.1093/rfs/hhu068)).
- Quality minus junk (profitability, growth, safety, payout) works in 24
  countries, including Hong Kong
  ([Asness, Frazzini & Pedersen 2019, RAS](https://doi.org/10.1007/s11142-018-9470-2)).
- Costs: low turnover. Profitability keeps its return after costs (Novy-Marx &
  Velikov 2016).
- Level: **A**.

### Low volatility and low beta

- High idiosyncratic volatility predicts low returns in the US
  ([Ang, Hodrick, Xing & Zhang 2006, JF](https://doi.org/10.1111/j.1540-6261.2006.00836.x)).
  The same result is in 23 developed markets
  ([Ang, Hodrick, Xing & Zhang 2009, JFE](https://doi.org/10.1016/j.jfineco.2007.12.005)).
- Betting against beta works in 19 international equity markets, including
  Hong Kong ([Frazzini & Pedersen 2014, JFE](https://doi.org/10.1016/j.jfineco.2013.10.005)).
- Low-volatility stocks have a higher Sharpe ratio than high-volatility
  stocks in global data
  ([Blitz & van Vliet 2007, JPM](https://doi.org/10.3905/jpm.2007.698039)).
- Level: **A** for a better risk-adjusted return. The raw return is not
  always higher.

### Size

- Small stocks had higher returns in 1936–1975
  ([Banz 1981, JFE](https://doi.org/10.1016/0304-405X(81)90018-0)).
  The effect became weak after its publication.
- Size works again when the test controls for quality ("junk")
  ([Asness, Frazzini, Israel, Moskowitz & Pedersen 2018, JFE](https://doi.org/10.1016/j.jfineco.2018.05.006)).
- Small stocks have high costs. Many replication failures are in microcaps
  (Hou, Xue & Zhang 2020).
- Level: **C** alone. Use size as a liquidity screen condition, not as a
  source of return.

### Piotroski F-score

- Definition: 9 binary signals from financial data. Profitability (4):
  ROA > 0, CFO > 0, ΔROA > 0, CFO > net income. Leverage and liquidity (3):
  Δleverage < 0, Δcurrent ratio > 0, no new shares. Efficiency (2): Δgross
  margin > 0, Δasset turnover > 0. Score 0–9.
- Evidence: in high B/M stocks, high F-score (8–9) beat low F-score (0–1) by
  about 23% per year in 1976–1996
  ([Piotroski 2000, JAR](https://doi.org/10.2307/2672906)). Most of the return
  came from small, illiquid stocks.
- Later work: the F-score also separates value and glamour stocks that the
  market prices wrongly
  ([Piotroski & So 2012, RFS](https://doi.org/10.1093/rfs/hhs061)).
- Hong Kong: this research found no peer-reviewed Hong Kong test.
- Level: **B** as a quality filter inside a value screen.

### Greenblatt magic formula

- Definition: rank stocks by earnings yield (EBIT / enterprise value) and by
  return on capital (EBIT / (net working capital + net fixed assets)). Add
  the 2 ranks. Buy the 20–30 best. Hold 1 year
  ([Greenblatt, magicformulainvesting.com](https://www.magicformulainvesting.com/)).
- Evidence: the source is a book by the author, not a peer-reviewed study.
  The formula is a value factor plus a profitability factor. Those 2 factors
  have level A or B evidence alone.
- Level: **C** for the exact formula. Its parts have better evidence.

### Altman Z-score

- Definition: Z = 1.2 X1 + 1.4 X2 + 3.3 X3 + 0.6 X4 + 1.0 X5. X1 = working
  capital / total assets. X2 = retained earnings / total assets. X3 = EBIT /
  total assets. X4 = market value of equity / total liabilities. X5 = sales /
  total assets ([Altman 1968, JF](https://doi.org/10.1111/j.1540-6261.1968.tb00843.x)).
  The model is for US manufacturing firms.
- Evidence: Z predicts bankruptcy. It does not predict a higher return.
  Firms with high bankruptcy risk earn lower returns
  ([Dichev 1998, JF](https://doi.org/10.1111/0022-1082.00046),
  [Campbell, Hilscher & Szilagyi 2008, JF](https://doi.org/10.1111/j.1540-6261.2008.01416.x)).
- Level: **B** as an exclusion screen condition (remove distressed firms).
  Not a return signal.

### Short-term reversal

- Definition: stocks with a low return last month (or last week) have a
  higher return next month
  ([Jegadeesh 1990, JF](https://doi.org/10.1111/j.1540-6261.1990.tb05110.x)).
- Costs: the profit is in illiquid stocks and does not stay after costs
  ([Avramov, Chordia & Goyal 2006, JF](https://doi.org/10.1111/j.1540-6261.2006.01060.x),
  Novy-Marx & Velikov 2016). AQR found it profitable with institutional costs
  (Frazzini, Israel & Moskowitz 2018).
- Level: **C** for a personal trader.

### Post-earnings-announcement drift (PEAD)

- Definition: standardized unexpected earnings (SUE). Prices drift in the
  direction of the earnings surprise for about 60 trading days
  ([Bernard & Thomas 1989, JAR](https://doi.org/10.2307/2491062)).
- Costs: the drift is mostly in illiquid stocks. Costs remove a large part
  of the return
  ([Chordia, Goyal, Sadka, Sadka & Shivakumar 2009, FAJ](https://doi.org/10.2469/faj.v65.n4.3)).
- Data: earnings dates and consensus or past earnings. This needs a data
  source with an earnings calendar.
- Level: **B** in liquid stocks with a small size, **C** in illiquid stocks.

## Technical indicators

### Moving averages and trading range breaks

- Brock, Lakonishok, and LeBaron tested moving-average and range-break rules
  on the Dow Jones index for 1897–1986. The rules predicted returns
  ([Brock, Lakonishok & LeBaron 1992, JF](https://doi.org/10.1111/j.1540-6261.1992.tb04681.x)).
- After a correction for data snooping, the best rule was not significant in
  1987–1996 ([Sullivan, Timmermann & White 1999, JF](https://doi.org/10.1111/0022-1082.00163)).
- With a false-discovery control and costs, the rules did not give a net
  profit on the Dow Jones stocks
  ([Bajgrowicz & Scaillet 2012, JFE](https://doi.org/10.1016/j.jfineco.2012.06.001)).
- A moving-average timing rule on portfolios sorted by volatility gave
  returns that the usual factors do not explain
  ([Han, Yang & Zhou 2013, JFQA](https://doi.org/10.1017/S0022109013000586)).
- A survey found that many studies report profits, but many of them have
  data-snooping and cost problems
  ([Park & Irwin 2007, Journal of Economic Surveys](https://doi.org/10.1111/j.1467-6419.2007.00519.x)).
- Asia: moving-average rules predicted returns in Malaysia, Thailand, and
  Taiwan. They were less successful in Hong Kong and Japan. Break-even costs
  were small in the larger markets
  ([Bessembinder & Chan 1995, Pacific-Basin Finance Journal](https://doi.org/10.1016/0927-538X(95)00002-3)).
- Level: **B** as a trend filter on an index or a portfolio. **C** as a
  return signal for single stocks.

### RSI, MACD, and Bollinger Bands

- Origin: RSI from J. Welles Wilder (1978, book "New Concepts in Technical
  Trading Systems"). MACD from Gerald Appel. Bollinger Bands from John
  Bollinger. All are practitioner tools from books, not from peer-reviewed
  studies.
- Peer-reviewed tests are few and use small samples. The tests that exist
  have the data-snooping problem (Park & Irwin 2007).
- An RSI below 30 is a short-term "oversold" signal. It is a form of
  short-term reversal, so the cost findings for short-term reversal apply.
- MACD is the difference of 2 exponential moving averages. It is a form of
  a moving-average rule, so the moving-average findings apply.
- Level: **D** as a return source. Useful as entry timing and as a chart
  aid.

### ATR

- Definition: the average of the true range, max(high − low, |high −
  previous close|, |low − previous close|), over n bars. From Wilder (1978).
- Use: ATR measures volatility. It does not predict direction. Volatility
  scaling of positions improves the Sharpe ratio of momentum and of the
  market portfolio (Barroso & Santa-Clara 2015,
  [Moreira & Muir 2017, JF](https://doi.org/10.1111/jofi.12513)).
- Level: **B** for risk control. Not a return signal.

### Volume

- Stocks with an unusually high volume in one week have higher returns in
  the next month
  ([Gervais, Kaniel & Mingelgrin 2001, JF](https://doi.org/10.1111/0022-1082.00349)).
- Volume changes how momentum behaves (Lee & Swaminathan 2000).
- Amihud illiquidity (average |return| / dollar volume) measures the price
  effect of trade size
  ([Amihud 2002, JFM](https://doi.org/10.1016/S1386-4181(01)00024-6)).
- Level: **B** as a liquidity screen condition. **C** as a return signal.

## Data sources for factor returns

These sources supply factor returns that a backtest can use as a benchmark:

- [Kenneth French Data Library](https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/data_library.html):
  US and regional factors, including Asia Pacific ex Japan.
- [AQR datasets](https://www.aqr.com/Insights/Datasets): QMJ, BAB, value,
  and momentum factors by country.
- [JKP factors](https://jkpfactors.com): 153 factors in 93 countries,
  including Hong Kong.

## Recommended first indicator set

The set uses daily bars first, because each instrument already has bars.
Indicators that need financial data come after, when a data source for
financial data is available. Intraday bars are not necessary for this set.

| # | Indicator | Formula | Usual parameters | Data | Level |
|---|---|---|---|---|---|
| 1 | Simple moving average (SMA) | mean of the last n closes | n = 50, 200 days (10 months) | daily bars | B |
| 2 | Momentum 12-1 | close(t−21) / close(t−252) − 1 | 252 and 21 trading days | daily bars | A (US), B (HK) |
| 3 | Distance to 52-week high | close / max(high, last 252 days) | 252 days | daily bars | B |
| 4 | Realized volatility | stdev of daily log returns × √252 | 60 or 252 days | daily bars | A |
| 5 | ATR | Wilder average of true range | n = 14 | daily bars | B (risk only) |
| 6 | Average dollar volume | mean(close × volume) | 20 or 60 days | daily bars | B (screen only) |
| 7 | RSI | 100 − 100 / (1 + avg gain / avg loss), Wilder average | n = 14, levels 30/70 | daily bars | D |
| 8 | Earnings yield (E/P or EBIT/EV) | earnings / price | trailing 12 months | financial data + bars | B |
| 9 | Book-to-market | book equity / market value | last annual report | financial data + bars | B |
| 10 | Gross profitability | (revenue − COGS) / total assets | last annual report | financial data | A |
| 11 | Piotroski F-score | sum of 9 binary signals | score 0–9 | financial data (2 years) | B |

### Typical use of each indicator

| # | Indicator | As a screen condition | As a strategy rule |
|---|---|---|---|
| 1 | SMA | close > SMA 200 (uptrend only) | Buy when close crosses above SMA. Sell when close crosses below. Or use as a trend filter for other rules. |
| 2 | Momentum 12-1 | top 20% of the list by momentum | Each month, hold the top-ranked instruments. Scale the position by volatility to reduce crash risk. |
| 3 | 52-week high | close ≥ 0.9 × 52-week high | Buy near the 52-week high. Sell when the ratio falls below a level. |
| 4 | Realized volatility | bottom 30% of the list by volatility | Set the position size as target volatility / realized volatility. |
| 5 | ATR | ATR / close below a level (remove very unstable instruments) | Put the stop at entry − k × ATR (k = 2–3). Set the size from the risk per trade / (k × ATR). |
| 6 | Average dollar volume | above a minimum value (for example 5 million USD or the HKD equivalent per day) | Limit the order size to a small part of the daily volume. |
| 7 | RSI | RSI(14) < 30 together with close > SMA 200 | Buy a short pullback in an uptrend. Sell when RSI goes back above 50–70. Test the costs. |
| 8 | Earnings yield | top 30% of the list, earnings > 0 | Rank each quarter or each year. Combine with profitability (magic formula form). |
| 9 | Book-to-market | top 30% of the list | Rank each year. Combine with F-score. |
| 10 | Gross profitability | top 30% of the list | Rank each year. Combine with value. |
| 11 | Piotroski F-score | F-score ≥ 7 (inside a value screen) | Buy high-B/M instruments with F-score 8–9. Hold 1 year. |

### Notes for implementation

- Prefer combinations of factors to one factor alone. Value and momentum have
  a negative correlation, so a combination has a smaller drawdown (Asness,
  Moskowitz & Pedersen 2013).
- Prefer low-turnover rules (monthly or yearly rebalance). Costs remove the
  return of high-turnover rules (Novy-Marx & Velikov 2016).
- Use the Altman Z-score as an exclusion condition only, and only for
  non-financial firms.
- Each backtest must include commissions and a spread estimate. Hong Kong
  stocks also have stamp duty on each trade.
- Report a t-statistic or a similar metric, and test out of sample. A
  backtest that tests many parameters has the data-snooping problem (Harvey,
  Liu & Zhu 2016).
- Financial data has a reporting lag. A backtest must use the data only from
  the date when it became public, or it has look-ahead bias.

## Open items

- `GLOSSARY.md` does not define Indicator, Factor, Screen, or Screen result.
  A later change must add them.
- This research found no peer-reviewed Hong Kong test of the Piotroski
  F-score, the magic formula, RSI, MACD, or Bollinger Bands.
- The data source for financial data (IBKR or another source) is not part of
  this ticket.
