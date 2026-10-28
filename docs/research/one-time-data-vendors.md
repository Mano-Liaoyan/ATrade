# One-time and pay-as-you-go historical data vendors

Research for [issue 144](https://github.com/Mano-Liaoyan/ATrade/issues/144),
part of the map [issue 129](https://github.com/Mano-Liaoyan/ATrade/issues/129).
This document continues two earlier files. Read them for the vendors and
sources that this document does not repeat:

- [`screen-data-sources.md`](https://github.com/Mano-Liaoyan/ATrade/blob/research/screen-data-sources/docs/research/screen-data-sources.md)
  ([issue 134](https://github.com/Mano-Liaoyan/ATrade/issues/134)): IBKR,
  Sharadar, Tiingo, Massive, EODHD, FMP, Norgate subscriptions.
- [`free-data-sources.md`](https://github.com/Mano-Liaoyan/ATrade/blob/research/free-data-sources/docs/research/free-data-sources.md)
  ([issue 143](https://github.com/Mano-Liaoyan/ATrade/issues/143)). It covers the free
  combination (IBKR, SEC EDGAR, WIKI Prices, Tiingo symbol list), and the
  method to join an old data set to IBKR bars.

All prices, limits, and terms were read on 2026-10-28, unless a line gives a
different date. Vendors change prices and terms often. Read the cited page
again before you pay.

Terms have the meaning that [`GLOSSARY.md`](../../GLOSSARY.md) gives them.
This document also uses the terms of `free-data-sources.md`: universe,
survivorship bias, look-ahead bias, point-in-time (PIT) fundamentals, and
filing date. In addition:

- **One-time purchase**: one payment that gives data the buyer can keep and
  use with no time limit. No payment repeats.
- **Pay as you go**: the vendor charges for each download by size. There is
  no monthly fee.
- **Raw bars**: bars with no adjustment for splits or dividends.
- **Split-only adjusted**: bars adjusted for splits but not for dividends.
  IBKR `TRADES` bars, which ATrade uses now, have this form.

## Short answer

1. For US stocks, the best value is **FirstRate Data "Stocks Complete"** at
   EUR 499.95, one time (price shown with VAT for this session's location).
   It has 1-minute to daily bars from January 2000 for 16,329 symbols,
   including more than 7,000 delisted symbols. It supplies raw, split-only
   adjusted, and split and dividend adjusted bars, plus split and dividend
   files. The licence is perpetual. Add the fundamentals add-on for
   EUR 199.95 (EUR 695.95 together). It has a `filing_date` field from 2000.
2. **Databento** pay-as-you-go needs no subscription. New users get USD 125
   of credits. US equities history starts on 2018-05-01 (Nasdaq ITCH) and
   includes all symbols that traded since then. One year of daily bars for
   all US symbols cost about USD 4 in 2025 (a user report). The credits can
   pay for the post-2018 delisted bars that the free combination lacks.
3. **Kibot** "All Stocks & ETFs" costs USD 990, one time. It has 1-minute and
   daily bars from 1998 and lists 12,926 delisted symbols. Forum opinions
   about its data quality are mixed.
4. **No vendor sells Hong Kong bars once, at a listed price.** Tick Data
   covers HKEX from 2008-05-13 but gives prices only on request. HKEX sells
   raw order data (Historical Full Book), not bars. For HK, keep IBKR.
5. Subscriptions do not become a one-time purchase if you cancel after one
   month. Sharadar requires deletion within 30 days. Massive ends all rights
   at termination. Norgate stops the database. SimFin requires deletion.
   FirstRate and Kibot are different: their terms let you keep the data.

Recommendation: start with combination A (free combination + Databento
credits, USD 0). Buy FirstRate Stocks Complete (combination B) when a
backtest needs US intraday bars or delisted symbols before 2018.

## Comparison

"Delisted" means that the source has bars of instruments that stopped
trading. "Keep" means that the licence lets you keep and use downloaded data
after the access period ends, for personal use.

| Vendor | Price (2026-10-28) | Payment | US / HK | Bars | History | Delisted | Adjustment | Fundamentals | Keep |
|---|---|---|---|---|---|---|---|---|---|
| FirstRate Data, Stocks Complete | EUR 499.95. With fundamentals EUR 695.95 | One time. 1 month of updates included. Then USD 59.95/month (optional) | US only | 1m, 5m, 30m, 1h, 1d | 2000-01 to now | Yes, more than 7,000. Not complete | Raw, split-only, split + dividend. Split and dividend files | Add-on EUR 199.95, from 2000, has `filing_date` | Yes, perpetual |
| Kibot, All Stocks & ETFs bundle | USD 990 | One time. 1 year of download access | US only | 1m, 1d (tick extra) | 1998 to now | Yes, 12,926 listed as delisted | Raw, split-only, split + dividend | No | Yes |
| Kibot, All Stocks 1-minute | USD 3,000 (30-minute USD 600) | One time | US only | 1m or 30m, 1d | 1998 | Yes | As above | No | Yes |
| Databento US Equities | Pay per GB. USD 125 free credits (expire after 6 months) | Pay as you go | US only | 1s, 1m, 1h, 1d (and tick) | 2018-05-01 (ITCH). Consolidated daily from 2024-07-01 | Yes, every symbol that traded in the range | Raw only | No | Not checked (see section) |
| EODData | USD 15 per 5 years, up to USD 90 for 30 years, per exchange | One time (EOD). Intraday USD 5/month per exchange | US (NYSE, NASDAQ, AMEX). No HK | 1d. Intraday from 2008 by subscription | Up to 30 years | Not stated | Split-adjusted EOD. Intraday raw | No | Not stated |
| BacktestMarket | EUR 199.34 "Most Traded Stocks", EUR 220.24 "Complete Pack" | One time | Not stated | 1m, 1d | From 1991 | Not stated | Not stated | No | Not stated |
| PiTrading | No price on the page | Not stated | US (most active) | Intraday | "Over a decade" | Not stated | Not stated | No | Not stated |
| MarketParquet | USD 79 | One time. Updates USD 15/month (optional) | US only | 1m to 1d | 2000-01-03 | Yes (count not stated) | Split-adjusted. Raw not stated | No | Not stated |
| Algoseek | Lease USD 1,500/month (12-month minimum). Buy: quote only | Lease or one-time buy-out | US only | Minute bars, TAQ | 2007 | Not stated | Factors supplied | No | Buy-out: perpetual |
| Tick Data LLC | Quote only | Not stated | US from 1993. HK from 2008-05-13 | Tick, bars | See left | Not stated | Not stated | No | Not stated |
| HKEX Historical Full Book | HK$5,000 per month of data (old page, not checked) | Per month of data | HK only | Order and trade records, not bars | Not stated | Instruments of each day | Raw | No | Not stated |
| Norgate | US Platinum USD 630/year | Subscription only (6 or 12 months) | US, no HK | 1d | 1990 | Yes | Several | Current only | No. Access stops |
| Massive (Polygon) flat files | From USD 29/month | Subscription only | US only | 1m, 1d | 5 to 20+ years by plan | Yes | Raw | Separate | No. Rights end at termination |
| QuantQuote | USD 0 to 99/month | Subscription only (EOD API now) | US only | 1d | 2000 (Pro, "coming soon") | Not stated | Not stated | Some | No |

## Vendors

### FirstRate Data

Sources: [Stocks Complete](https://firstratedata.com/b/22/stock-complete-historical-intraday),
[FAQ](https://firstratedata.com/about/FAQ),
[License](https://firstratedata.com/about/license),
[Financials](https://firstratedata.com/fundamental-data/financials/).

- Price: the "Buy Now" button showed EUR 499.95 for Stocks Complete and
  EUR 695.95 with fundamentals. The fundamentals add-on showed EUR 199.95.
  The FAQ says that the button shows the local currency and includes local
  VAT. A US dollar price is "indicative only". The price for a buyer in the
  Netherlands can be different from the price this session saw.
- Payment: "a one-off payment with no rebilling". It includes the full
  history and one month of daily updates. Updates after that cost
  USD 59.95 per month (USD 79 with fundamentals). Updates are optional.
  ATrade gets recent bars from IBKR, so ATrade does not need them.
- Download links work only while a subscription is active. Download all
  files in the first month.
- Coverage: main US exchanges. OTC-only securities are not included.
  16,329 symbols: 9,329 listed and more than 7,000 delisted. The page lists a
  start date for each symbol (example: `AAPL` from 2000-01-04).
- Delisted: the FAQ says that the delisted list "is not the complete
  universe of tickers since 2000". More symbols are missing in older years.
  Delisted symbols have a `-DELISTED` suffix.
- Symbol changes: the full history is under the newest symbol (example:
  Facebook under `META`). Changes from 2022 are fully merged. Before 2022,
  only "the larger ticker changes" are merged.
- Adjustment: each data set has raw bars, split-only adjusted bars, and split
  and dividend adjusted bars. Volume is adjusted too. Separate files give
  each split (date, ratio) and each dividend (ex-date, cash amount). Mergers
  and spin-offs are not covered.
- Fundamentals: income statement, balance sheet, cash flow, and ratios from
  10-K and 10-Q filings, from January 2000. Each record has `filing_date`.
  The page calls the data "point-in-time". The page does not say whether a
  restatement replaces the first value. Check a sample before you trust it
  for backtests.
- Licence: "the license is perpetual, with no time limit on use and no need
  to stay subscribed". Use is private. Raw data must not be redistributed.
  Charts, backtest results, and derived statistics can be published.
- Fit for ATrade: the split-only adjusted bars have the same form as IBKR
  `TRADES` bars. The join method of `free-data-sources.md` applies directly.

### Kibot

Sources: [Buy](https://www.kibot.com/buy.aspx),
[All stocks and ETFs](http://www.kibot.com/Historical_Data/All_Stocks_and_ETFs_Historical_Intraday_Data.aspx),
[Support FAQ](https://www.kibot.com/support.aspx),
[License](https://www.kibot.com/license.html).

- Bundle "All Stocks & ETFs": USD 990, "one-time payment · one year of
  download access". 18,000+ US stocks and 6,900+ ETFs, 1-minute and daily
  bars, "from 1998 to today". The page also lists "All Stocks" 1-minute alone
  at USD 3,000, so the bundle is the better price. The page says that 1-minute
  data "is currently on sale" in a bundle. The price can change.
- Updates: 45 days of daily updates, then quarterly updates at 3, 6, and 9
  months. Premium subscription (daily updates, API) costs USD 139 per month.
- Delisted: the stock page lists 26,220 instruments, of which 12,926 are
  delisted. The FAQ says that thinly traded and short-lived delisted symbols
  are often missing. A reused symbol can hold 2 unrelated histories in one
  file.
- Adjustment: raw, split-only adjusted, and split and dividend adjusted
  files. Kibot uses the Yahoo method.
- Daily close: the last trade of the regular session, not the official
  closing auction price. This can be different from IBKR daily bars.
- Licence: "Data already delivered to the Licensee is his to keep
  permanently." Internal use on 2 computers. No redistribution.
- Reputation (opinion, not fact): Elite Trader and NexusFi posts from 2010 to
  2022 are mixed. Some posters report bad ticks and wrong dividend
  adjustment. Others say that the bars are good enough for backtests at
  5-minute or longer periods. Some of the negative reviews came from a
  competitor site (QuantQuote), as Kibot and posters said.
  [Elite Trader, 2017](https://www.elitetrader.com/et/threads/is-kibot-legit-place-to-get-tick-historical-data-from.308296/),
  [NexusFi](https://nexusfi.com/showthread.php?t=38956).

### Databento

Sources: [Pricing](https://databento.com/pricing),
[US Equities catalog](https://databento.com/catalog/us-equities),
[Datasets](https://databento.com/docs/venues-and-datasets).

- Payment: "Pay as you go for historical data". No subscription is
  necessary. Price is per GB of uncompressed binary data. The page does not
  print the rate. The estimator and the API `metadata.get_cost` give the
  cost before you download.
- Credits: "New users get $125 in free credits that can be used towards
  historical data from any of our datasets. Credits expire 6 months after
  signup and each team is eligible for one set of credits."
- Data sets for US stocks (no Hong Kong data set):
  - `XNAS.ITCH` (Nasdaq TotalView-ITCH): from 2018-05-01. Schemas include
    OHLCV-1s, 1m, 1h, 1d. The bars count only trades on Nasdaq venues, so the
    volume is lower than the consolidated volume.
  - `EQUS.SUMMARY`: consolidated daily bars from all US exchanges and ATSs,
    from 2024-07-01. Raw prices.
  - `EQUS.MINI` and venue data sets (NYSE, Cboe, IEX, and others) are also
    available. The pricing table says "8+ years" for OHLCV history.
- Historical licence: "A license isn't required to access historical data"
  (XNAS.ITCH page). No exchange fee for historical downloads.
- Cost (user report, opinion): a Hacker News user priced one year of daily
  bars for all US symbols at USD 4.38 on `EQUS.SUMMARY` and USD 3.78 on
  `XNAS.ITCH` (2024-07-01 to 2025-07-01, comment of 2025-10-08).
  [HN](https://news.ycombinator.com/item?id=45516154). Databento staff gave a
  start price of USD 0.45 per GB on Elite Trader (older post). 1-minute bars
  for all symbols since 2018 are much larger. Get the cost with `get_cost`
  before you download.
- Delisted: the data contains every symbol that traded on each day. So
  symbols that stopped trading after 2018-05-01 are in it. This is an
  inference from how a feed capture works, not a statement on the page.
- Adjustment: raw only. Use IBKR or FirstRate split files to adjust.
- Keep: this document did not find a clause about local storage of
  historical data. Read the Databento terms before you keep the files.
- NautilusTrader 2.0 has a Databento adapter and loader for DBN files. This
  makes the import simple.
- Reputation (opinion): Hacker News users call it a "low-friction" source
  and say pay-as-you-go is cheaper than the USD 199 plan. One 2024 comment
  says that history is short and that cleaning methods are not documented.

### EODData

Source: [Historical data](https://www.eoddata.com/products/historicaldata.aspx),
[Products](https://www.eoddata.com/products/default.aspx).

- EOD history is sold once per exchange: USD 15 for 5 years, up to USD 90
  for 30 years. You can download a purchase again as often as you like.
- Intraday (1 to 60 minutes) costs USD 5 per month per exchange, from
  2008-01-01. That is a subscription.
- EOD prices are split-adjusted and "cleaned for spikes". Intraday is raw.
- No Hong Kong exchange. The page does not say whether delisted symbols are
  included. Memberships are "for personal use only".
- Weak point for ATrade: daily bars only, no dividend data, delisted status
  not known. The free WIKI Prices set (issue 143) covers the same need up to
  2018.

### BacktestMarket and PiTrading

Sources: [BacktestMarket](https://www.backtestmarket.com/),
[Most Traded Stocks](https://www.backtestmarket.com/en/most-traded-stocks-pack),
[PiTrading](https://pitrading.com/).

- BacktestMarket sells sector packs (EUR 49.11 to 199.34) and a Complete
  Pack (EUR 220.24). The pages do not list the symbols, the adjustment, or
  delisted coverage. The packs are made for MetaTrader users.
- PiTrading does not show prices or adjustment rules on its pages.
- Do not buy either for ATrade. The pages do not give enough facts to check
  survivorship bias or adjustment.

### MarketParquet

Source: [marketparquet.com](https://marketparquet.com/).

- USD 79 one time for US stocks, ETFs, and futures, 1-minute to daily, from
  2000-01-03, delisted symbols included, Parquet files.
- The site does not name its data source or its owner. Adjustment is
  split-adjusted. Raw bars are not stated. No reputation evidence was found.
- The price is low. Treat it as not verified. Compare its free sample with
  FirstRate and IBKR before you pay.

### Algoseek, Tick Data LLC, QuantQuote

Sources: [Algoseek pricing](https://www.algoseek.com/pricing),
[Tick Data equity data](https://www.tickdata.com/equity-data/),
[QuantQuote](https://quantquote.com/).

- Algoseek: lease from USD 1,500 per month with a 12-month minimum. A
  perpetual buy-out exists, but the price is "contact sales". The customers
  are firms. Too expensive for ATrade.
- Tick Data: US equities from 1993-01-01. HK equities: "All equities listed
  on the Hong Kong Stock Exchange (HKEx) since May-13-2008". Prices only on
  request. This is the only vendor found with deep HK intraday history.
  Ask for a quote if HK intraday backtests become necessary.
- QuantQuote now sells an EOD API by subscription (USD 0 to 99 per month).
  No one-time product was found. Its old second-level data set (1998 to
  2016) is sold to institutions.

### HKEX

Sources: [Historical Data Services](https://www.hkex.com.hk/Services/Market-Data-Services/Historical-Data-Services),
[HKEX Data Marketplace](https://www.hkex.com.hk/Services/Market-Data-Services/Historical-Data-Services/HKEX-Data-Marketplace).

- The old Historical Data platform closed after 2026-05-31. Products moved
  to the HKEX Data Marketplace. Contact: `datamarketplace@hkex.com.hk`.
- Securities products: "Historical Full Book" (all orders and trades, CSV)
  and "Securities Attribute Daily Files" (static data). There is no bar
  product.
- An old HKEX page listed the Full Book at HK$5,000 per month of data. The
  current pages give no price. Not checked.
- To get bars, you must build them from the order and trade records. For
  10 years, the cost at the old price is about HK$600,000. Not suitable.

### Subscriptions that do not work as one-time purchases

Sources: issue 134 file, [Massive individuals terms](https://massive.com/legal/individuals-terms-of-service),
[Norgate packages](https://norgatedata.com/stockmarketpackages.php),
[SimFin prices](https://www.simfin.com/en/prices/).

- Sharadar: after the subscription ends, you must delete the data within
  30 days (issue 134).
- Massive: on termination, "the license and any other rights granted under
  the Agreement will end".
- Norgate: subscription only (6 or 12 months). Database access stops.
- SimFin: plans from USD 15 per month (annual). Users must delete downloaded
  data after cancellation.

## Point-in-time fundamentals at a low one-time cost

| Source | Cost | Markets | From | PIT method | Weak points |
|---|---|---|---|---|---|
| SEC EDGAR `companyfacts.zip` (issue 143) | Free | US | 2009 | First `filed` date of each value | You build the field mapping. No values before 2009 |
| FirstRate fundamentals | EUR 199.95 add-on, EUR 399.95 alone | US | 2000 | `filing_date` on each record. Called "point-in-time" | Not checked whether restatements do not replace first values. 40+ fields only |
| Sharadar SF1 (AR dimensions) | USD 499/year | US | 1998 | As reported, no restatements | Subscription. Delete after end |

No source of HK PIT fundamentals with a one-time price was found. Issue 134
found none at a personal price either.

FirstRate fundamentals add years 2000 to 2008, which EDGAR XBRL does not
have. Buy them only if a strategy needs fundamentals before 2009. First check
the sample: find a company with a known restatement and compare the values
with the first 10-Q.

## Recommended combinations

All combinations keep IBKR for recent bars, live bars, and all HK bars.
They keep SEC EDGAR for US fundamentals from 2009 (issue 143). Prices are
from 2026-10-28.

### A. Free combination + Databento credits (USD 0)

- Add to issue 143: Databento `XNAS.ITCH` or `EQUS` daily bars, and 1-minute
  bars for selected symbols, from 2018-05-01, paid by the USD 125 credits.
- Gain: bars of US symbols that stopped trading after 2018. The free
  combination has no source for them. This makes the survivorship bias much smaller
  for backtests after 2018.
- Weak points: no bars before 2018 from Databento (WIKI Prices covers 1996 to
  2018-03 for daily). Raw bars only. `XNAS.ITCH` volume is Nasdaq only.
  Credits expire 6 months after signup. 1-minute bars for all symbols may
  cost more than the credits. Local storage terms not checked.

### B. A + FirstRate Stocks Complete (EUR 499.95 one time, recommended when intraday is necessary)

- US: 1-minute to daily bars from 2000, more than 7,000 delisted symbols,
  raw and split-only adjusted bars, split and dividend files. Perpetual
  licence.
- Optional: fundamentals add-on, total EUR 695.95.
- Gain over the free combination: intraday bars for 26 years, delisted bars
  from 2000, dividend data. The split-only bars join directly to IBKR bars.
- Weak points: US only. Delisted list not complete before 2022. Download
  window is one month. No mergers or spin-offs in the adjustment.

### C. A + Kibot All Stocks & ETFs (USD 990 one time)

- US: 1-minute and daily bars from 1998, 12,926 delisted symbols (by the
  page count), raw and adjusted files, quarterly updates for 9 months.
- Gain over B: 2 more years, more delisted symbols, ETFs included.
- Weak points: about double the price of B. Mixed opinions on data quality.
  Daily close is the last trade, not the closing auction. Reused symbols can
  share one file. No fundamentals.

### Comparison with the free combination (issue 143)

| Need | Free (issue 143) | A | B | C |
|---|---|---|---|---|
| One-time cost | 0 | 0 | EUR 499.95 | USD 990 |
| US daily bars, listed | IBKR | IBKR | IBKR, FirstRate | IBKR, Kibot |
| US daily bars, delisted before 2018 | WIKI (partial, to 2018-03) | Same | FirstRate from 2000 | Kibot from 1998 |
| US daily bars, delisted after 2018 | None | Databento | Databento, FirstRate | Databento, Kibot |
| US intraday history | IBKR (listed only, pacing limits) | Databento from 2018 | FirstRate from 2000 | Kibot from 1998 |
| US fundamentals | EDGAR from 2009 | Same | Same, or FirstRate from 2000 (EUR 199.95 more) | EDGAR |
| HK bars | IBKR (listed only) | Same | Same | Same |
| HK fundamentals | None | None | None | None |

## Not checked

- FirstRate price for a buyer in the Netherlands. The session location was
  not checked. Read the button price at checkout.
- FirstRate fundamentals: whether a restatement replaces the first value.
- Databento cost of 1-minute bars for all US symbols since 2018. Run
  `get_cost` after signup.
- Databento terms for local storage of historical data after use of credits.
- HKEX Historical Full Book current price.
- MarketParquet data source, owner, and data quality.
- Tick Data price for HK equities.
- Reddit r/algotrading opinions: the search tool could not read reddit.com.
  Opinions in this document come from Elite Trader, NexusFi, and Hacker
  News.
