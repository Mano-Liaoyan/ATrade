# Free and low-cost data sources for the trial period

Research for [issue 143](https://github.com/Mano-Liaoyan/ATrade/issues/143),
part of the map [issue 129](https://github.com/Mano-Liaoyan/ATrade/issues/129).
This document continues
[issue 134](https://github.com/Mano-Liaoyan/ATrade/issues/134) and its file
[`screen-data-sources.md`](https://github.com/Mano-Liaoyan/ATrade/blob/research/screen-data-sources/docs/research/screen-data-sources.md).
That file covers IBKR, Sharadar, the paid vendor plans, and the Yahoo terms.
This document does not repeat them. It examines the sources that cost
USD 0 to 15 per month.

All prices, limits, and maintenance dates were read on 2026-10-28, unless a
line gives a different date. Vendors change prices and terms often. Read the
cited page again before you depend on it.

Terms have the meaning that [`GLOSSARY.md`](../../GLOSSARY.md) gives them.
In this document:

- **Universe**: all instruments of one market that a screen examines.
- **Survivorship bias**: an error in a backtest that occurs when the data
  contains only instruments that are still listed today.
- **Look-ahead bias**: an error in a backtest that occurs when the test uses
  a value before the date when the value was public.
- **Point-in-time (PIT) fundamentals**: financial statement values as they
  were known on a given date, before restatements.
- **Filing date**: the date when the SEC received a filing. EDGAR calls it
  `filed`.

## Short answer

1. The trial-period combination costs USD 0 to 14.50 per month. This is the
   IBKR market data fee from issue 134. All other parts are free:
   - **IBKR** for bars of listed US and HK instruments: full history, recent
     bars, and live bars. It is the same price source as paper orders.
   - **SEC EDGAR XBRL** (`companyfacts.zip`, nightly) for US fundamentals
     from 2009. The first `filed` date of each value gives near point-in-time
     fundamentals.
   - **Nasdaq Data Link WIKI Prices** (public domain, frozen in 2018) for US
     research on the years 1996 to 2018. It contains some instruments that
     were delisted before 2018.
   - **Tiingo `supported_tickers.csv`** (free, updated daily) as a list of
     US symbols with start and end dates, including 8,220 US stock symbols
     that stopped trading. It measures the size of the survivorship bias. It
     gives no bars.
2. No free source gives bars of delisted instruments after 2018. No free
   source gives HK point-in-time fundamentals. Backtests of a screen after
   2018 have survivorship bias in this combination.
3. Stooq bulk files (US and HK, daily, hourly, 5-minute) were the best free
   bulk source until March 2026. Since then, Stooq requires an API key that a
   person gets through a CAPTCHA, and the bulk page shows a browser check. Use
   it only as a manual download, if at all.
4. Do not use Yahoo (yfinance), AKShare, or Tushare free endpoints as stored
   ATrade data. Yahoo terms forbid automated collection. AKShare scrapes web
   pages and says that its data is for academic research. HKEX and HKEXnews
   terms forbid programmatic access.
5. Compared with Sharadar, the user loses delisted bars from 1997, curated
   PIT fundamentals from 1998, daily valuation metrics, and index membership
   history. The user must build the EDGAR fundamentals tables.

## Price and bar sources

### Comparison

"Delisted" means that the source has bars of instruments that stopped
trading. "Licence" is for personal use and local storage.

| Source | Markets | Bars | History | Delisted | Update | Cost and limit | Licence | Status (2026-10-28) |
|---|---|---|---|---|---|---|---|---|
| Stooq bulk files | US, HK, UK, JP, PL, others | Daily, hourly, 5-minute | Daily from first listing (not checked per instrument). Hourly and 5-minute are short | No (listed only) | Daily files, manual download | Free. CAPTCHA per file. API key since March 2026 | No terms page found | Bulk page behind a browser check since June 2026 |
| Nasdaq Data Link WIKI Prices | US | Daily, raw and adjusted | 1996 (per dataset page) to 2018-03-27 | Partial (instruments delisted before 2018) | None. Frozen | Free API key | Public domain | Frozen since 2018 |
| Kaggle "Huge Stock Market Dataset" | US | Daily, adjusted | To 2017-11-10 | No | None | Free | CC0 | Frozen since 2017 |
| Kaggle "Stock Market Dataset" | US (Nasdaq-traded) | Daily (from Yahoo) | To 2020-04-01 | No | None | Free | CC0 on Kaggle. Source is Yahoo | Frozen since 2020 |
| Yahoo via yfinance | US, HK | Daily, intraday | Varies | No | On request | Free. No documented limit | Yahoo terms forbid automated collection | yfinance 1.7.0, 2026-08-26 |
| Tiingo free (Starter) | US (and China A-shares) | Daily | 30+ years | Yes, but 500 symbols per month | API | 50 requests/hour, 1,000/day, 500 symbols/month, 1 GB/month | Internal, personal use | Active |
| Alpha Vantage free | US (HK not stated) | Daily (`compact`, last 100 bars) | 100 bars on free key | Not stated | API | 25 requests/day. `outputsize=full` and adjusted series are premium | Not checked | Active |
| FMP Basic (free) | US | Daily | 5 years | Delisted list endpoint | API | 250 calls/day, 500 MB per 30 days | Display or redistribution needs an agreement | Active |
| EODHD free | No HK | Daily | 1 year | Not on free plan | API | 20 calls/day | Private, non-commercial | Active |
| HKEX Daily Quotations | HK | One report per day (all instruments) | About the last 3 months | Instruments of that day | Daily | Free | Personal use. No programmatic access | Active |
| AKShare `stock_hk_hist` / `stock_hk_daily` | HK (also US) | Daily, raw, qfq, hfq | "All data that Sina has" | Not stated | On request (web scraping) | Free. No documented limit | "Academic research" | v1.20.2, 2026-10-28 |
| Tushare `hk_daily` | HK | Daily | Not stated | Not stated | API | Separate permission. Price not listed | Not checked | Python package 1.4.29, 2026-03-25 |
| IBKR (issue 134) | US, HK | Daily, intraday | Up to `68 Y` per daily request | No | API | USD 0 to 14.50 per month | Your own account data | Active |

### Stooq bulk downloads

Sources: [Stooq historical data page](https://stooq.com/db/h/) (archived
copies from
[2025-12-30](https://web.archive.org/web/20251230121126/https://stooq.com/db/h/)
and [2026-03-12](https://web.archive.org/web/20260312005131/https://stooq.com/db/h/)),
[pandas-datareader issue 1012](https://github.com/pydata/pandas-datareader/issues/1012).

- The page offered ZIP files in ASCII and MetaStock formats for daily,
  hourly, and 5-minute bars. "Last update: 11 Mar 2026" in the March copy.
- Sizes on 2026-03-11: U.S. daily 508 MB, hourly 395 MB, 5-minute 576 MB.
  Hong Kong daily 100 MB, hourly 37 MB, 5-minute 49 MB.
- Folder counts on 2025-12-30: US NASDAQ stocks 4,666, NYSE stocks 3,594,
  NYSE MKT stocks 311, NASDAQ ETFs 950, NYSE ETFs 2,571. HK: HKEX stocks
  2,848, HKEX ETFs 195, plus warrants (7,251) and CBBCs (6,254).
- The files contain listed instruments only. The page has no folder for
  delisted instruments. Survivorship bias is present.
- Each download needed a CAPTCHA code. The page has a code field ("Rewrite
  the above code").
- Since March 2026, single-symbol CSV requests return a page that asks for
  an API key. The key comes from a `get_apikey` page with a CAPTCHA
  (issue 1012, opened 2026-04-13).
- On 2026-10-28, a plain HTTP request to `https://stooq.com/db/h/` returned
  a JavaScript proof-of-work browser check. Archived copies from 2026-06-08
  onwards are the same 1 KB check page.
- This survey did not pass the check. A person in a normal browser can
  probably still download the files. This is not confirmed.
- This survey found no terms page that grants storage or reuse rights.
- Not checked: if Stooq adjusts the bars for splits and dividends, and the
  symbol format for HK instruments in the files.
- Result: Stooq is a manual, one-time bulk source at most. Do not automate
  it. Do not build a recurring ATrade job on it.

### Nasdaq Data Link WIKI Prices

Sources: [WIKIP database page](https://data.nasdaq.com/databases/WIKIP),
[Kaggle mirror description](https://www.kaggle.com/datasets/marketneutral/quandl-wiki-prices-us-equites).

- The dataset page describes end-of-day prices, dividends, and splits for
  3,000 US companies, "curated by the Quandl community and released into the
  public domain". It gives January 1996 as the start.
- The community stopped the updates in 2018. Sources give 2018-03-27 (the
  last full day) or 2018-04-11 (the last update). Treat 2018-03-27 as the
  end.
- On 2026-10-28, the dataset page still existed (archived 2026-10-15). The
  API `datatables/WIKI/PRICES` returned "A valid API key is required". A
  free Nasdaq Data Link account gives a key.
- Columns: raw `open`, `high`, `low`, `close`, `volume`, plus `ex-dividend`,
  `split_ratio`, and `adj_*` columns. The raw columns and the event columns
  let you compute your own adjustment.
- Delisted: the set contains instruments that stopped trading before 2018.
  The coverage of delisted instruments is not complete and is not measured.
- Bias: survivorship bias is smaller than in a list of current instruments,
  but it is present. Community curation can contain errors.
- Licence: public domain. Local storage is allowed.
- A Kaggle mirror (`marketneutral/quandl-wiki-prices-us-equites`, 463 MB)
  exists. Its licence field says "Unknown". Use the Nasdaq Data Link file.

### Kaggle and academic datasets

Source: the Kaggle dataset API (`/api/v1/datasets/view/<ref>`), read on
2026-10-28.

| Dataset | Content | End | Licence | Delisted |
|---|---|---|---|---|
| [`borismarjanovic/price-volume-data-for-all-us-stocks-etfs`](https://www.kaggle.com/datasets/borismarjanovic/price-volume-data-for-all-us-stocks-etfs) | Daily bars of US stocks and ETFs on NYSE, NASDAQ, NYSE MKT. Adjusted for dividends and splits | 2017-11-10 | CC0 | No (listed in 2017) |
| [`jacksoncrow/stock-market-dataset`](https://www.kaggle.com/datasets/jacksoncrow/stock-market-dataset) | Daily bars of instruments that traded on NASDAQ in 2020, from Yahoo | 2020-04-01 | CC0 on Kaggle | No |
| [`eren2222/hongkong-daily-historical-stock-market-2000-2024`](https://www.kaggle.com/datasets/eren2222/hongkong-daily-historical-stock-market-2000-2024) | 1,580 HK companies, 2000-01-04 to 2024-05-23. The description also says "Japan" and "285 companies" | 2024-05-23 | Apache 2.0 | Not stated |

- A Kaggle search for "delisted stocks" and "survivorship bias free" on
  2026-10-28 returned no US or HK set with delisted bars.
- The Kaggle sets copy data from Yahoo, Stooq, or unknown sources. The CC0
  label on Kaggle does not prove that the uploader had the right to give
  the data away.
- The academic standard for US delisted bars is CRSP. CRSP needs an
  institutional subscription (for example through WRDS). It is not a
  personal option. This survey did not check CRSP prices.
- Result: the Kaggle sets add nothing that WIKI and IBKR do not give. The HK
  set has a contradictory description. Do not use them.

### Yahoo Finance through yfinance

Sources: [yfinance README](https://github.com/ranaroussi/yfinance),
[yfinance `multi.py`](https://github.com/ranaroussi/yfinance/blob/main/yfinance/multi.py).
Issue 134 gives the Yahoo terms.

- yfinance 1.7.0 was released on 2026-08-26. The repository had a push on
  2026-10-27. It is maintained.
- The README says: "the Yahoo! finance API is intended for personal use
  only." The Yahoo terms forbid automated collection without permission.
- `download()` has `auto_adjust=True` as the default. The OHLC values are
  then adjusted for splits and dividends. This differs from IBKR `TRADES`.
- Yahoo gives no bars of delisted instruments. Survivorship bias is present.
- Result: same as issue 134. Use it for manual checks only.

### Tiingo, Alpha Vantage, FMP, and EODHD free tiers

Sources: [Tiingo pricing](https://www.tiingo.com/about/pricing),
[Tiingo supported tickers](https://apimedia.tiingo.com/docs/tiingo/daily/supported_tickers.zip),
[Tiingo terms](https://app.tiingo.com/tos/),
[Alpha Vantage premium](https://www.alphavantage.co/premium/),
[Alpha Vantage documentation](https://www.alphavantage.co/documentation/),
[FMP pricing](https://site.financialmodelingprep.com/pricing-plans),
[EODHD pricing](https://eodhd.com/pricing).

**Tiingo Starter (free)**

- 50 requests per hour, 1,000 per day, 500 unique symbols per month,
  1 GB per month. Price history 30+ years. Fundamentals 5 years.
- Licence: "Internal use means you may only use the data for your own
  personal use".
- The Tiingo terms are dated 2026-10-06. This survey read them only through
  a search excerpt. They require you to delete all Tiingo data after a paid
  plan ends or after a downgrade to Starter. Thus you cannot buy one month,
  download all history, cancel, and keep the data.
- `supported_tickers.zip` is a public file without a key. On 2026-10-28 it
  had 109,151 rows with `ticker`, `exchange`, `assetType`, `priceCurrency`,
  `startDate`, `endDate`. It had 16,317 stock rows on NYSE, NASDAQ, AMEX,
  NYSE ARCA, and NYSE MKT. Of these, 8,220 had an `endDate` before
  2026-10-01, which means that they stopped trading.
- Use: the list gives a history of the US universe. It shows how many
  instruments a backtest misses in each year. The free bars cover only 500
  symbols per month. It has no HK rows.

**Alpha Vantage free**

- 25 requests per day.
- `TIME_SERIES_DAILY` with `outputsize=compact` gives the last 100 bars on a
  free key. `outputsize=full` (20+ years) is premium.
  `TIME_SERIES_DAILY_ADJUSTED` is premium.
- Result: not usable for history.

**FMP Basic (free)**

- USD 0. 250 calls per day. 5 years of history. US coverage. "End of Day
  Historical Data" and "Profile and Reference Data". Bandwidth 500 MB per
  30 days. The cheapest paid plan (Starter) is USD 29 per month or USD 19
  per month billed annually. It is above the USD 15 budget.
- Use: a free key can test FMP coverage of `.HK` instruments before the user
  pays for Ultimate (issue 134). It is not a history source.

**EODHD free**

- 20 calls per day. 1 year of history. EODHD has no HK exchange (issue 134).
  The cheapest paid plan is EUR 19.99 per month (EUR 199.90 per year).
- Result: not usable.

### HKEX public data

Sources: [Daily Quotations (Main Board)](https://www.hkex.com.hk/eng/stat/smstat/dayquot/qtn.asp),
[HKEX Terms of Use](https://www.hkex.com.hk/Global/Exchange/Terms-of-Use?sc_lang=en),
[HKEXnews Terms of Use](https://www2.hkexnews.hk/Global/Exchange/Terms-of-Use?sc_lang=en),
[List of Securities](https://www.hkex.com.hk/eng/services/trading/securities/securitieslists/ListOfSecurities.xlsx).

- The Daily Quotations report `dYYMMDDe.htm` has the quotations and the
  sales records of all Main Board instruments for one day. The report for
  2026-10-27 is 21 MB.
- The archive is short. On 2026-10-28, the reports for 2026-08-31 and later
  returned HTTP 200. The reports for 2026-08-03 and earlier returned HTTP
  404.
- `ListOfSecurities.xlsx` lists the instruments that are listed today. It
  is a universe list for HK. It does not list delisted instruments.
- HKEX terms permit you to "download, print, store temporarily, retrieve
  and display Information" for personal use. They do not permit storage "on
  any server or other storage device connected to a network".
- HKEX terms forbid "any programmatic, scripted or other mechanical means
  to access this Website". HKEXnews terms forbid "text or data mining or web
  scraping".
- Result: HKEX pages are for manual checks. A manual download of
  `ListOfSecurities.xlsx` can seed the HK universe. Do not let an ATrade job
  get HKEX or HKEXnews pages.

### AKShare and Tushare for Hong Kong

Sources: [AKShare repository](https://github.com/akfamily/akshare),
[AKShare introduction](https://github.com/akfamily/akshare/blob/main/docs/introduction.md),
[AKShare stock quote docs](https://github.com/akfamily/akshare/blob/main/docs/data/stock/stock_quote.md),
[AKShare stock finance docs](https://github.com/akfamily/akshare/blob/main/docs/data/stock/stock_finance.md),
[Tushare `hk_daily`](https://tushare.pro/document/2?doc_id=192),
[Tushare price table](https://tushare.pro/document/1?doc_id=290).

**AKShare**

- MIT licence for the code. Release v1.20.2 on 2026-10-28. It is very
  active, because the scraped web pages change often.
- AKShare collects data from web pages, for example Eastmoney and Sina. The
  introduction says that the data is "仅用于学术研究" (for academic research
  only) and warns about commercial risk.
- `stock_hk_hist`: Eastmoney daily, weekly, and monthly bars. `adjust` is
  `""`, `qfq` (forward-adjusted), or `hfq` (backward-adjusted).
- `stock_hk_daily`: Sina daily bars and adjustment factors (`qfq-factor`,
  `hfq-factor`). The docs say that the data is all the data that Sina has,
  "并不等于该股票从上市至今的数据" (not always the full history since
  listing).
- `stock_hk_hist_min_em`: Eastmoney minute bars.
- `stock_financial_hk_report_em`: HK balance sheet, income statement, and
  cash flow statement from Eastmoney. The output has `REPORT_DATE` and
  `STD_REPORT_DATE`, which are period dates. It has no publication date. The
  values are not point-in-time.
- The universe comes from `stock_hk_spot_em`, which lists instruments that
  trade today. Delisted coverage is not stated.
- Result: AKShare can fill gaps for a manual check. It is not a licensed
  source. Its endpoints break when the web pages change.

**Tushare Pro**

- `hk_daily` needs a separate permission ("本接口数据需单独开通权限").
  The price table does not list its price. One call returns at most 5,000
  rows. The page does not state the start date, the adjustment, or delisted
  coverage.
- HK financial reports cost CNY 500 per year, from 2000 (issue 134).
- The GitHub repository `waditu/tushare` had its last push on 2024-03-13.
  The Python package 1.4.29 was released on 2026-03-25. The Tushare Pro
  service is active.
- Result: not free. Ask Tushare for the `hk_daily` price if HK delisted bars
  become a need.

### OpenBB

Sources: [OpenBB repository](https://github.com/OpenBB-finance/OpenBB),
PyPI pages of `openbb`, `openbb-sec`, `openbb-yfinance`, `openbb-fmp`,
`openbb-tiingo`.

- OpenBB is an aggregator. It gives one Python interface to many providers.
  It supplies no data of its own. Each provider needs its own key and has
  its own terms.
- `openbb` 5.0.0 was released on 2026-09-29 (Apache 2.0). The core
  repository has providers such as `sec`, `nasdaq`, `cboe`, `fred`,
  `famafrench`, and `finra`.
- The yfinance, FMP, and Tiingo providers are separate packages under
  AGPL-3.0 (`openbb-yfinance` 2.0.0, `openbb-fmp` 1.6.1, `openbb-tiingo`
  1.6.1).
- Result: OpenBB does not remove any limit or bias of the providers. ATrade
  already has its own IBKR adapter. OpenBB adds a large dependency for no new
  data. Do not use it.

## Fundamentals: SEC EDGAR XBRL

Sources: [EDGAR APIs](https://www.sec.gov/search-filings/edgar-application-programming-interfaces),
[Financial Statement Data Sets](https://www.sec.gov/data-research/sec-markets-data/financial-statement-data-sets),
[Data set documentation (PDF)](https://www.sec.gov/files/aqfs.pdf),
[Accessing EDGAR data](https://www.sec.gov/search-filings/edgar-search-assistance/accessing-edgar-data),
[Developer resources](https://www.sec.gov/about/developer-resources).

### What it gives

- **companyfacts API and `companyfacts.zip`**: all XBRL facts of each
  company. The ZIP file is "updated and republished nightly at approximately
  3:00 a.m. ET". No API key.
- **companyconcept API**: one concept (for example `us-gaap/NetIncomeLoss`)
  of one company.
- **frames API**: one fact for each company for one calendar period, for
  example `CY2024` or `CY2024Q3I`. The page says that it takes the fact that
  is "last filed".
- **Financial Statement Data Sets**: quarterly ZIP files from 2009 Q1. The
  latest file on 2026-10-28 was 2026 Q3 (62 MB). The `SUB` table has `filed`
  (the filing date) and `accepted` (the acceptance time). "accepted after
  5:30pm EST are considered filed on the following business day." The `NUM`
  table has `ddate` (period end) and `qtrs` (the number of quarters).
- Rate limit: "Current max request rate: 10 requests/second." Declare a
  User-Agent header with a name and an e-mail address.
- Licence: "Anyone can access and download this information for free".
  Local storage is allowed.

### Near point-in-time values from the filing date

Each fact in companyfacts has `val`, `start`, `end`, `accn`, `form`, `fy`,
`fp`, `filed`, and sometimes `frame`. A later filing repeats the earlier
periods with its own `filed` date. Example, read on 2026-10-28 from
`companyconcept/CIK0000320193/us-gaap/NetIncomeLoss.json` (Apple):

| Period | `filed` | `form` | `val` (USD) |
|---|---|---|---|
| 2021-09-26 to 2022-09-24 | 2022-10-28 | 10-K | 99,803,000,000 |
| 2021-09-26 to 2022-09-24 | 2023-11-03 | 10-K | 99,803,000,000 |
| 2021-09-26 to 2022-09-24 | 2024-11-01 | 10-K | 99,803,000,000 |

Procedure for a near point-in-time table:

1. Load `companyfacts.zip` into PostgreSQL. Keep every fact row with its
   `filed` and `accn`.
2. For each company, concept, and period, keep the row with the earliest
   `filed`. This is the value as first reported.
3. Keep the later rows as restatements, with their own `filed` dates.
4. In a backtest on date D, use only rows with `filed` earlier than D. Use
   the next trading day after `filed` as the first day of use. This avoids a
   filing that the SEC accepted after the close.

Do not use the frames API for backtests. It gives the "last filed" value.
Example: the `CY2024` frame for `NetIncomeLoss` gives AAR Corp. a value from
accession `0001140361-26-031078`, which is a 2026 filing. A backtest in
2025 cannot know that value.

### Limits of EDGAR

- Only US SEC filers. No HK companies, except those that file with the SEC
  (for example some ADR issuers that file 20-F).
- XBRL starts in 2009 for large filers and about 2011 for all filers. No
  fundamentals before 2009.
- Companies use different tags for the same item. For example, revenue can
  be `Revenues`, `RevenueFromContractWithCustomerExcludingAssessedTax`, or
  `SalesRevenueNet`. You must map the tags to your own fields.
- Delisted companies stay in companyfacts by CIK. Example: CIK 886158
  (Bed Bath & Beyond, now "20230930-DK-BUTTERFLY-1, INC.") is present. Its
  `NetIncomeLoss` facts have `filed` dates from 2020-10-01 to 2023-06-14.
  This example shows that the coverage of one tag can be shorter than the
  life of the company.
- No prices, no market capitalization. Market capitalization needs shares
  outstanding (`dei:EntityCommonStockSharesOutstanding`) and a bar close.
- The CIK-to-symbol file of the SEC lists current symbols only. For old
  symbols, use the `tickers` and former names in `submissions.zip`, and
  check them by hand.
- "The SEC does not allow botnets or automated tools to crawl the site."
  Use the nightly ZIP files, not one request for each company.

### HK fundamentals

- HKEXnews holds all HK results announcements with their publication time.
  These times are the HK filing dates. The terms forbid scraping, so ATrade
  cannot collect them automatically.
- AKShare `stock_financial_hk_report_em` gives HK statements without a
  publication date.
- Tushare HK financial reports cost CNY 500 per year. Point-in-time status
  is not stated (issue 134).
- Result: no free HK point-in-time fundamentals exist in this survey.

## Join an old dataset with IBKR bars

### Instrument mapping

ATrade identifies an instrument by symbol, exchange, and currency
(`GLOSSARY.md`). Each source uses a different code.

| Source | US example | HK example |
|---|---|---|
| ATrade / IBKR | `AAPL / NASDAQ / USD` | `700 / SEHK / HKD` |
| WIKI, Tiingo | `AAPL` | none |
| Stooq | `aapl.us` | not checked |
| Yahoo | `AAPL` | `0700.HK` |
| AKShare | `AAPL` (US endpoints) | `00700` |
| Tushare | `AAPL` | `00700.HK` |
| SEC EDGAR | CIK `0000320193` | none |

Rules for a mapping table:

1. Store one row for each pair of an instrument and a source code, with a
   valid-from and a valid-to date.
2. Store the IBKR `conId` with each instrument. A symbol can change (FB to
   META) or go to a new company. The `conId` is stable for one contract.
3. Map an old symbol to a current instrument only when the dates and the
   company name agree. A symbol in WIKI from 2005 can be a different company
   from the same symbol today.
4. Leave delisted instruments of an old dataset without an IBKR `conId`.
   They have history only in the old dataset.

### Adjustment differences

Source: [IBKR Historical Bars](https://www.interactivebrokers.com/docs/tws-api/doc/md/historical-bars).

| Source | Splits | Dividends |
|---|---|---|
| IBKR `TRADES` (ATrade uses it, `backend/src/atrade/ibkr/historical_bars.py`) | Adjusted | Not adjusted |
| IBKR `ADJUSTED_LAST` | Adjusted | Adjusted |
| WIKI raw columns | Not adjusted | Not adjusted |
| WIKI `adj_*` columns | Adjusted | Adjusted |
| yfinance `download()` default | Adjusted | Adjusted |
| AKShare `adjust=""` / `qfq` / `hfq` | No / forward / backward | No / forward / backward |
| Stooq bulk | Not confirmed | Not confirmed |

IBKR docs say: "TRADES data is adjusted for splits, but not dividends." and
"ADJUSTED_LAST data is adjusted for splits and dividends."

Rules:

1. Store bars as split-adjusted and not dividend-adjusted. This agrees with
   IBKR `TRADES`, the source of paper orders.
2. For WIKI, compute this form from the raw columns and `split_ratio`.
3. Store dividends and splits as separate events. Compute a total-return
   series from the events when a strategy needs it.
4. IBKR adjusts the split-adjusted history again after each new split. Load
   the overlap window again after a split.

### Overlap comparison

Use one overlap window of at least 60 trading days for each instrument. For
WIKI, the window must end on 2018-03-27.

1. Request IBKR `TRADES` daily bars for the window.
2. Align the two series on the exchange-local trade date.
3. Count the dates that only one source has. Missing dates show holidays,
   halts, or errors.
4. Compute the ratio of the IBKR close to the old close on each date.
5. When the ratio is constant within 0.1%, the difference is an adjustment
   factor. Multiply the old series by the median ratio.
6. When the ratio changes in one step on one date, a split or a dividend
   occurred there. Check the event table, then correct the old series.
7. When the ratio is noisy, the sources disagree on prices. Do not join the
   series. Mark the instrument as "IBKR only".
8. Compare volume as a ratio only. IBKR says that its historical volume is
   filtered, so volume does not match other sources.
9. Use IBKR bars from the first date of the window onwards. Use old bars
   only before that date.
10. Store the source of each bar. A backtest result must show which source
    gave its bars.

## Recommended trial-period combination

Cost read on 2026-10-28.

| Part | Source | Monthly cost |
|---|---|---|
| US and HK bars, listed instruments, full history and live | IBKR | USD 10.00 (waived at USD 30 commissions) plus USD 4.50. HK L1 waived |
| US fundamentals from 2009, near point-in-time | SEC EDGAR `companyfacts.zip` and Financial Statement Data Sets | USD 0 |
| US research bars 1996 to 2018, with some delisted instruments | Nasdaq Data Link WIKI Prices | USD 0 |
| US universe history (start and end dates of symbols) | Tiingo `supported_tickers.csv` | USD 0 |
| HK universe | IBKR plus a manual download of `ListOfSecurities.xlsx` | USD 0 |
| **Total** | | **USD 0 to 14.50** |

Weaknesses:

- Survivorship bias in all backtests of a screen after 2018-03-27. Tiingo's
  symbol list shows its size, but it does not remove it.
- HK has no fundamentals and no delisted bars.
- EDGAR fundamentals start in 2009. The tag mapping is your own work and
  has errors that you must find.
- WIKI is frozen, community-curated, and incomplete for delisted
  instruments.
- IBKR full-market downloads are slow (issue 134 estimate: about 1.5 hours
  for 10,000 instruments, not measured).

### What the user loses compared with Sharadar

| Item | Sharadar (issue 134) | Trial combination |
|---|---|---|
| Delisted US bars | From December 1997, about 21,000 symbols | WIKI to 2018 only, partial |
| PIT fundamentals | SF1 AR dimensions from 1998, standardized fields | EDGAR from 2009, your own tag mapping |
| Daily valuation metrics (market cap, P/E) | Ready | Compute from shares and bars |
| Symbol history, sector, delist dates | Ready (`tickers` table) | Tiingo dates only. No sector |
| Index membership history | Ready (S&P 500 table) | None |
| Corporate actions | Ready | From IBKR and WIKI, partial |
| Engineering work | Load bulk files | Build EDGAR and mapping pipelines |
| Cost | About USD 42 per month (annual) | USD 0 beyond IBKR data |

When the trial shows that a US screen needs fundamentals before 2009 or a
backtest without survivorship bias, add Sharadar (combination 2 of
issue 134).

## Unconfirmed

- If a person in a normal browser can still download the Stooq bulk files
  after June 2026. Check by hand.
- The Stooq adjustment method and its HK symbol format.
- The Stooq terms for storage and reuse.
- The number of delisted instruments in WIKI. Count the symbols whose last
  bar is before 2018-03-27.
- The full text of the Tiingo terms. This survey read only a search excerpt.
  The page `app.tiingo.com/tos/` returned HTTP 403 to the survey tool.
- The Tushare `hk_daily` price, start date, and delisted coverage.
- The exact start of the HKEX Daily Quotations archive window. The survey
  tested only some dates.
