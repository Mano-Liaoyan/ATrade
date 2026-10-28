# Screening data sources for US and Hong Kong stocks

Research for [issue 134](https://github.com/Mano-Liaoyan/ATrade/issues/134),
part of the map [issue 129](https://github.com/Mano-Liaoyan/ATrade/issues/129).
The earlier broker and data survey is
[issue 43](https://github.com/Mano-Liaoyan/ATrade/issues/43).

All prices and limits were read on 2026-10-28 from the vendor pages that each
row cites. Prices are for one individual with personal, non-professional use.
Vendors change prices often. Read the cited page again before you buy.

Terms have the meaning that [`GLOSSARY.md`](../../GLOSSARY.md) gives them.
In this document:

- **Universe**: all instruments of one market that a screen examines.
- **Survivorship bias**: an error in a backtest that occurs when the data
  contains only instruments that are still listed today.
- **Point-in-time fundamentals**: financial statement values as they were
  known on a given date, before restatements. Without them, a backtest can
  use data that was not public on the test date (look-ahead bias).

## Short answer

1. IBKR gives bars for US and Hong Kong instruments, and a live market scanner
   with at most 50 results for each scan. IBKR removed the fundamentals API in
   TWS API 10.47. IBKR gives no bars for instruments that stopped trading.
   IBKR has no API call that lists all instruments of an exchange.
2. For US stocks, use Sharadar. Its personal plan costs USD 69 per month or
   USD 499 per year. It is the only surveyed vendor with delisted
   instruments, point-in-time fundamentals, and bulk files at a personal
   price.
3. For Hong Kong stocks, no surveyed vendor gives delisted instruments and
   point-in-time fundamentals at a personal price. IBKR bars for listed
   instruments are the practical source. FMP Ultimate is the only surveyed
   API vendor that states "Global Coverage" for both markets.
4. EODHD does not list the Hong Kong exchange. Tiingo, Massive, Sharadar,
   and Norgate are US only (Norgate also has Australia and Canada).

## IBKR

### Market scanner

Source: [Market Scanner Subscription](https://www.interactivebrokers.com/docs/tws-api/doc/market-scanner/subscription),
[Market Scan Parameters](https://www.interactivebrokers.com/docs/tws-api/doc/market-scanner/parameters).

- `reqScannerSubscription` runs a scan of the TWS Advanced Market Scanner.
  It returns contracts and a rank. It returns no prices.
- "Scans are limited to a maximum result of 50 results per scan code, and
  only 10 API scans can be active at a time."
- The scanner needs no market data subscription. Filters "generally" need
  one.
- Filters are tag-value pairs, for example `usdMarketCapAbove`. The
  instrument types, location codes, scan codes, and filter codes come from
  the XML that `reqScannerParameters` returns. Not all TWS scans are
  available in the API.
- The location code for a market comes from the same XML. Codes such as
  `STK.US.MAJOR` and `STK.HK.SEHK` are in common use. This survey did not run
  `reqScannerParameters`, so the exact list for this account is not checked.
- Result: the scanner is a live top-50 list. It cannot screen a full universe,
  and it cannot screen history. It cannot supply a backtest.

### Fundamental data

Source: [TWS 2026 API production release notes](https://www.ibkrguides.com/releasenotes/prod-2026.htm).

- TWS API 10.47, under "De-Supported Fundamentals Data Request", removed
  `reqFundamentalData`, `reqFundamentalsDataProtoBuf`,
  `cancelFundamentalData`, `cancelFundamentalsDataProtoBuf`, the callbacks
  `fundamentalData` and `fundamentalsDataProtoBuf`, and the tick type
  `FUNDAMENTAL_RATIOS = 47`. These calls returned the Refinitiv (LSEG)
  reports.
- The current TWS API documentation has no page for fundamental data and
  names no replacement.
- The API still gives Wall Street Horizon event data (`reqWshMetaData`,
  `reqWshEventData`): earnings dates, dividend dates, splits, and similar
  events. It needs the "Wall Street Horizon Corporate Event Data" research
  subscription. It gives no financial statement values.
  Source: [Calendar Event Data through WSH](https://www.interactivebrokers.com/docs/tws-api/doc/wall-street-horizon/introduction).
- The IBKR website still has a "Fundamentals Explorer" tool for TWS and the
  client portal. This survey found no API access to it.
- Result: IBKR gives no financial statement values through the API, in the
  paper account or in the live account.

### Paper account

Source: [About paper trading accounts](https://www.ibkrguides.com/clientportal/aboutpapertradingaccounts.htm).

- The paper account has the same "market data subscriptions" as the live
  account. The live account pays for them.

### Market data subscriptions (non-professional)

Source: [IBKR market data pricing](https://www.interactivebrokers.com/en/pricing/market-data-pricing.php),
read 2026-10-28.

| Subscription | Monthly fee | Note |
|---|---|---|
| US Securities Snapshot and Futures Value Bundle | USD 10.00 | Waived when monthly commissions are USD 30 or more |
| US Equity and Options Add-On Streaming Bundle | USD 4.50 | Streaming quotes for US stocks |
| Hong Kong Securities Exchange (Stocks, Warrants & Bonds) L1 | Fee waived | |

The API docs say: "Unless requesting Delayed Watchlist Data, a paid data
subscription is required to receive market data through the API."
([Market Data Limitations](https://www.interactivebrokers.com/docs/tws-api/doc/md/market-data-limitations))

### Historical bars

Sources: [Historical Bars](https://www.interactivebrokers.com/docs/tws-api/doc/md/historical-bars),
[Market Data Limitations](https://www.interactivebrokers.com/docs/tws-api/doc/md/market-data-limitations),
[Pacing Limitations](https://www.interactivebrokers.com/docs/tws-api/doc/pacing-limitations).

- One `reqHistoricalData` request for 1-day bars can have a duration of up
  to `68 Y`. One request for each instrument can thus return its full
  history. ATrade now requests at most `364 D` for each 1-day request
  (`docs/architecture/market_data.md` section 8.3).
- The documented pacing violations apply to bars of 30 seconds or less:
  - identical requests within 15 seconds,
  - 6 or more requests for the same contract, exchange, and tick type within
    2 seconds,
  - more than 60 requests within any 10 minutes.
- All API requests have a general limit: market data lines divided by 2, per
  second. The default is 100 lines, so 50 requests per second.
- IBKR does not keep data "for securities which are no longer trading". It
  can also lose the data before an exchange move, for example SOXX before
  15 Oct 2010.
- Historical volume is filtered and can differ from the live volume. IBKR
  can adjust data later, so the same request can return different values on
  different days.
- IBKR has no API call that lists all instruments of an exchange.
  `reqMatchingSymbols` returns a short list of matches for one query. A
  full-market universe needs a list from another source.
- Estimate (not measured): with one request for each instrument and 0.5
  seconds between requests, 10,000 instruments take about 1.5 hours. IBKR
  can be slower than the documented limits. Measure this before you depend
  on it.

### Result for IBKR

| Need | US | Hong Kong |
|---|---|---|
| Daily bars of listed instruments | Yes | Yes |
| Daily bars of delisted instruments | No | No |
| Fundamentals through the API | No (removed in 10.47) | No |
| Universe list through the API | No | No |
| Live screen | Scanner, 50 results | Scanner, 50 results |

## Vendors

### Comparison

Prices read on 2026-10-28. "PIT" means point-in-time fundamentals.

| Vendor | Personal price | US bars | HK bars | Fundamentals | Delisted | PIT | History | Rate limit |
|---|---|---|---|---|---|---|---|---|
| Sharadar | Bundle full history USD 69/mo or USD 499/yr. Prices only from USD 9/mo. Fundamentals only from USD 19/mo | Yes (SEP) | No | US, from 1998 | Yes | Yes (AR dimensions) | Prices from Dec 1997 | Bulk files. API limit not stated |
| Tiingo | Power USD 30/mo or USD 300/yr. Fundamentals add-on price not listed | Yes | No (US and Chinese stocks) | US and ADRs, add-on | Yes (permaTicker, `isActive`) | Not stated | EOD 30+ years. Fundamentals 15+ years | 10,000 requests/hour, 100,000/day, 40 GB/month |
| Massive (Polygon.io) | Starter USD 29, Developer USD 79, Advanced USD 199 per month. Financials only USD 29/mo | Yes | No (US only) | US, in Advanced or Financials add-on | Yes (`active=false`, `delisted_utc`) | No | 5, 10, 20+ years by plan | Unlimited calls on paid plans. Flat files from Starter |
| EODHD | EOD EUR 19.99/mo. Fundamentals EUR 59.99/mo. All-in-one EUR 99.99/mo | Yes | No (no HK exchange listed) | US from 1985, non-US from 2000 | Yes, full data only for delistings after 2018 | No (`filing_date` only) | 30+ years | 100,000 calls/day, 1,000/min. A fundamentals call costs 10 |
| FMP | Starter USD 29, Premium USD 69, Ultimate USD 139 per month (annual: USD 19, 49, 99 per month) | Yes | Ultimate only ("Global Coverage") | Yes, plus "as reported" statements | Delisted list endpoint | Not stated | Starter 5 years. Premium and Ultimate 30+ years | 300, 750, 3,000 calls/min. Bandwidth 20, 50, 150 GB per 30 days |
| Norgate | US Platinum USD 630/yr, Diamond USD 787.50/yr. 6- or 12-month terms only | Yes | No (US, Australia, Canada) | Current values only | Yes (Platinum, Diamond) | No | From 1990 or 1950 | Windows database, not a web API |
| Alpha Vantage | USD 49.99 to USD 249.99 per month | Yes | Not stated | Yes | Not stated | Not stated | Not stated | Free: 25/day. Paid: 75 to 1,200/min |
| Yahoo Finance (yfinance) | Free, unofficial | Yes | Yes | Current and recent only | No | No | Varies | Not documented. Terms forbid automated access |
| Tushare Pro | HK financial reports CNY 500/yr. US daily CNY 2,000/yr. HK daily price not listed | Yes | Yes (separate permission) | HK and US from 2000 | Not stated | Not stated | US daily "full history" | 500 calls/min for the paid permissions |
| Futu / moomoo OpenAPI | Free with an account | Yes | Yes | Not checked | Not stated | Not stated | Not checked | Bars for 100 to 2,000 instruments in 7 days, by account tier |

### Sharadar

Sources: [sharadar.com](https://sharadar.com/),
[Subscribe](https://sharadar.com/subscribe),
[Fundamentals docs](https://sharadar.com/docs/fundamentals),
[Stocks docs](https://sharadar.com/docs/stocks),
[Personal Use License Terms](https://sharadar.com/terms).

- Sharadar now sells personal plans directly. Nasdaq Data Link sells the
  commercial licence.
- The `fundamentals` table (SF1) covers "nearly 18,000 active and delisted
  US public companies" from January 1998. It is "99% survivorship bias
  free".
- Point-in-time: the AR dimensions (ARQ, ARY, ART) exclude restatements.
  They are indexed to the date when the company sent the filing to the SEC.
  The MR dimensions (MRQ, MRY, MRT) show the most recent values.
- The `stocks` table (SEP) has daily bars from December 1997 for about
  21,000 tickers, including delisted tickers.
- Bulk downloads match the purchased history tier.
- Licence: personal, non-professional use only. No redistribution. After the
  subscription ends, you must remove the data within 30 days. You can keep
  "backtest results, models, summary statistics, trade logs, and similar
  derived works" that cannot reproduce the data.

### Tiingo

Sources: [Pricing](https://www.tiingo.com/about/pricing),
[Fundamentals docs](https://www.tiingo.com/documentation/fundamentals),
[End-of-day docs](https://www.tiingo.com/documentation/end-of-day).

- Power: USD 30 per month or USD 300 per year. 10,000 requests per hour,
  100,000 per day, 110,400 symbols per month, 40 GB per month.
- The plan counts "US & Chinese Stocks". The docs do not mention Hong Kong.
- Fundamentals are an add-on for "US Equities and ADRs". The page gives no
  add-on price. The docs describe an `asReported` dimension but do not say
  that the data is point-in-time.
- Licence: "Internal use means you may only use the data for your own
  personal use and you may not display or share the data with another
  person or organization."

### Massive (formerly Polygon.io)

Sources: [Pricing](https://massive.com/pricing?product=stocks),
[All Tickers](https://massive.com/docs/rest/stocks/tickers/all-tickers.md),
[Income statements](https://massive.com/docs/rest/stocks/fundamentals/income-statements.md),
[Terms](https://massive.com/legal/terms).

- Plans: Basic USD 0 (5 calls per minute, 2 years, end-of-day). Starter
  USD 29 (5 years). Developer USD 79 (10 years). Advanced USD 199 (20+ years,
  includes Financials & Ratios). Annual billing saves 20%.
- All plans are "Individual use only". Coverage is "All US Stocks Tickers".
- Delisted: the tickers endpoint has `active=false` and `delisted_utc`.
- Flat files (from Starter) give day bars for all US stocks in one file for
  each day.
- Not point-in-time: the `filing_date` of a financial record is the latest
  filing that contains the period, not the first one. A restatement replaces
  the earlier values.

### EODHD

Sources: [Pricing](https://eodhd.com/pricing),
[List of stock markets](https://eodhd.com/list-of-stock-markets),
[EOD API](https://eodhd.com/financial-apis/api-for-historical-data-and-volumes),
[Fundamentals API](https://eodhd.com/financial-apis/stock-etfs-fundamental-data-feeds),
[Delisted data](https://eodhd.com/financial-apis/delisted-stock-companies-data),
[Terms](https://eodhd.com/financial-apis/terms-conditions).

- Plans in EUR: EOD EUR 19.99, EOD + intraday EUR 29.99, Fundamentals
  EUR 59.99, All-in-one EUR 99.99 per month. 100,000 calls per day and
  1,000 per minute.
- The list of stock markets has Shanghai and Shenzhen but no Hong Kong
  exchange. `https://eodhd.com/exchange/HK` returns "page not found".
- Delisted: full data (bars, fundamentals, dividends, splits) for
  instruments delisted after 2018. Bars only for delistings before 2018.
- Fundamentals have a `filing_date` field. The docs do not say that the
  values are point-in-time.
- The site footer says that EODHD does not use exchange data feeds for
  prices. It aggregates "OTC, peer to peer trades and trading platforms over
  100+ sources" with a VWAP method.
- Licence: non-professional users can "store, manipulate, and analyze the
  data for private, non-commercial purposes".

### Financial Modeling Prep (FMP)

Sources: [Pricing plans](https://site.financialmodelingprep.com/pricing-plans),
[API docs](https://site.financialmodelingprep.com/developer/docs/stable).

- Personal plans: Starter USD 29 (5 years, US), Premium USD 69 (30+ years,
  US, UK, Canada), Ultimate USD 139 (Global Coverage, bulk and batch).
  Annual billing: USD 19, 49, 99 per month.
- Ultimate is the only surveyed API plan that states coverage beyond the
  US, UK, and Canada. The pricing page does not name Hong Kong. Test `.HK`
  instruments with a free key before you buy.
- Endpoints: `delisted-companies`, `income-statement-as-reported`,
  `eod-bulk` (all bars for one date), `income-statement-bulk`.
- The docs do not say that the statements are point-in-time.
- Licence: "Displaying or redistributing data sourced from FMP requires a
  specific Data Display and Licensing Agreement."

### Norgate Data

Sources: [Overview](https://norgatedata.com/),
[Stock market packages](https://norgatedata.com/stockmarketpackages.php).

- US packages: Platinum (from 1990, delisted, historical index members)
  USD 630 per year. Diamond (from 1950) USD 787.50 per year. 6-month and
  12-month terms only.
- Fundamentals are "Current Fundamentals" only.
- The data is in a database on Windows. Access to the database stops when
  the subscription ends. ATrade runs on Linux in Docker, so Norgate needs a
  Windows machine or a Windows virtual machine.
- No Hong Kong data.

### Alpha Vantage

Source: [Premium](https://www.alphavantage.co/premium/).

- USD 49.99 (75 per minute) to USD 249.99 (1,200 per minute) per month.
  The free plan allows 25 requests per day.
- The page does not state coverage by market, delisted data, or history
  length.

### Yahoo Finance (unofficial, through yfinance)

Sources: [yfinance README](https://github.com/ranaroussi/yfinance),
[Yahoo terms](https://legal.yahoo.com/us/en/yahoo/terms/otos/index.html).

- No official API. yfinance says: "the Yahoo! finance API is intended for
  personal use only."
- The Yahoo terms forbid collecting data "using any automated means ...
  for any purpose without our express, prior permission".
- No delisted instruments and no point-in-time fundamentals.
- Use it only for manual checks, not as a data source for ATrade.

### Vendors with Hong Kong data

- **Tushare Pro** ([price table](https://tushare.pro/document/1?doc_id=290),
  [hk_daily](https://tushare.pro/document/2?doc_id=192)): HK daily bars need
  a separate permission. The price table does not list its price. HK
  financial reports cost CNY 500 per year, from 2000. The organization price
  is 10 times the individual price. Delisted coverage and point-in-time
  status are not stated.
- **Futu / moomoo OpenAPI**
  ([quote rights](https://openapi.futunn.com/futu-api-doc/en/intro/authority.html)):
  free HK L1 quotes. An account under HKD 10,000 gets bars for 100
  instruments in 7 days. A large account gets bars for up to 2,000. This is
  too low for a full HK universe. Issue 43 did not find out if a Netherlands
  resident can open an account.
- **Twelve Data** ([pricing](https://twelvedata.com/pricing)): Grow USD 79,
  Pro USD 229 per month. The page does not say which plan includes HKEX.
  Not checked further.
- **Yahoo Finance**: has HK bars, but see the terms above.

## Recommended combinations

Monthly cost uses the annual price where one exists. Prices read on
2026-10-28.

### 1. IBKR only (USD 0 to 14.50 per month)

- Bars: IBKR for US and HK, listed instruments only.
- Universe: a list from outside the API (for example exchange listing
  files), saved in PostgreSQL.
- Fundamentals: none. Screens use only bars (price, volume, indicators).
- Live screen: the IBKR scanner, 50 results for each scan.
- Cost: US bundle USD 10.00 (waived at USD 30 commissions) plus USD 4.50
  streaming. HK L1 is waived.
- Limit: survivorship bias in all backtests of a screen. No fundamentals.

### 2. Sharadar for US, IBKR for HK (about USD 42 to 69 per month)

- US: Sharadar Bundle Full History, USD 499 per year (about USD 42 per
  month) or USD 69 per month. Delisted instruments, point-in-time
  fundamentals from 1998, bars from 1997, bulk files.
- HK: IBKR bars for listed instruments. No HK fundamentals.
- Optional: Tushare HK financial reports, CNY 500 per year (about USD 6 per
  month). Check its licence and point-in-time status first.
- Limit: HK screens have survivorship bias and no point-in-time
  fundamentals.

### 3. FMP Ultimate for both markets (about USD 99 to 139 per month)

- One API for US and HK bars and fundamentals, if a test shows HK
  coverage. Bulk endpoints load a full market for one date.
- Plus IBKR bars where they are needed for the same price source as paper
  orders.
- Limit: FMP does not state point-in-time fundamentals. A delisted list
  exists, but bar coverage for delisted HK instruments is not confirmed.

Recommendation: start with combination 1. Add Sharadar (combination 2) when
a US screen needs fundamentals or a backtest without survivorship bias.
Test FMP Ultimate with a free key only if HK fundamentals become a need.

## Unconfirmed

- The exact scanner location codes, scan codes, and filters for US and HK.
  Run `reqScannerParameters` on the paper account to get them.
- The real speed of full-market daily bar requests from IBKR. Measure it.
- The FMP coverage of `.HK` instruments, of delisted HK instruments, and of
  point-in-time values.
- The Tiingo fundamentals add-on price.
- The Tushare HK daily bar price, its licence for personal use, and its
  delisted coverage.
- A vendor with point-in-time fundamentals and delisted instruments for
  Hong Kong at a personal price. This survey found none.
