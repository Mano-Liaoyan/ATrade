# UI references: screens, rule builder, and AI assistant

Research ticket: [#135](https://github.com/Mano-Liaoyan/ATrade/issues/135).
Map: [#129](https://github.com/Mano-Liaoyan/ATrade/issues/129).
Date of the research: 2026-10-28.

## Question

How do leading products design these 4 areas?

- (a) The editor of screen conditions and the screen result table.
- (b) A no-code rule builder for entry rules and exit rules.
- (c) The comparison of strategy results, parameter optimization, and
  walk-forward displays.
- (d) An AI assistant conversation that changes strategy code and runs
  backtests.

Which patterns fit a Carbon v11 workbench in ATrade?

## Terms

This document uses the terms of `GLOSSARY.md`: strategy, strategy version,
backtest, metric, workbench, panel, side column, splitter. It also uses the
terms that map #129 names but that `GLOSSARY.md` does not have yet:

- **Indicator** (指标): a calculated series, for example RSI(14).
- **Screen** (选股条件): a saved set of conditions on instruments.
- **Screen result** (选股结果): the instruments that match a screen now.
- **Rule**: one condition of a strategy, for example "close above SMA(50)".

## Method and source quality

- Each fact comes from an official help page, an official documentation
  page, or an official product announcement. The links are in each section.
- Some help pages do not describe a part of the UI. The text says so. It
  does not fill the gap with a guess.
- Portfolio123 and Koyfin give no public help page for the screen editor or
  the ranking editor. Only release notes and blog posts of the vendor were
  available. The text marks these facts as "vendor blog" or "not verified".
- Screenshots are not copied into the repo. The links go to the image files
  that the vendors publish on their help pages. The links can change.

## Summary

1. **Screens.** All products put the conditions above or beside one result
   table. Each condition is a small token ("pill") that opens a small editor.
   Each condition can add its column to the table. Column sets ("views")
   change the columns but keep the conditions. Presets and saved screens are
   in one menu. A result can go to the watchlist.
2. **Rule builder.** The common model is a vertical list of blocks: entry
   conditions, exit conditions, and fixed exits (take profit, stop loss,
   trailing stop, N bars). One condition is one row: left operand,
   comparator, right operand. Groups use "All of" or "Any of". TrendSpider
   and Composer also put an AI button in the condition block.
3. **Results.** Products show one run with a metric row, an equity chart,
   and a trade list. For comparison, QuantConnect overlays the equity curves
   of many runs and shows a sortable table of runs. For parameters, it
   shows a scatter (1 parameter), a heat map (2 parameters), or a 3D plot
   (3 parameters). Walk-forward displays (MultiCharts, StrategyQuant) show
   in-sample and out-of-sample windows and a robustness result.
4. **AI assistant.** The assistant is a chat panel at the side of the code
   editor (QuantConnect "Ask Mia"). It reads the project, changes files,
   compiles, runs backtests, and repeats. Code editors (VS Code agent mode)
   show each change as a pending diff with Keep and Undo. Composer and
   TrendSpider state that the user approves before anything trades.
5. **Fit for ATrade.** All 4 areas fit the current workbench: a side column,
   a main panel, a lower panel with tabs, and a splitter. Carbon v11 has
   the parts: data table with toolbar and batch actions, tags, dropdown,
   number input, tile, structured list, inline notification, AI label. The
   AI chat itself has no Carbon component in `@carbon/styles`, so ATrade
   writes it from Carbon tiles, text areas, and code snippets.

## (a) Screen conditions and the screen result table

### TradingView Stock Screener

Sources:
[How to use filters in screener](https://www.tradingview.com/support/solutions/43000718745-how-to-use-filters-in-screener/),
[TradingView screeners walkthrough](https://www.tradingview.com/support/solutions/43000718885-tradingview-screeners-walkthrough/),
[Pine Screener overview](https://www.tradingview.com/support/solutions/43000742435-what-is-pine-screener-quick-overview-of-the-screener-s-functionality).

- The filter panel is a horizontal bar above the table. The user can hide
  it (Shift + H).
- The "+" button (Shift + F) adds a filter. The user selects a filter from
  a list, or types the condition as text. The filter applies at once.
- A click on a filter opens a small dialog. Some filters have only preset
  values. Other filters have "Manual setup" with free values.
- A filter can stay on the bar as inactive. The reset menu has 3 items:
  reset all filters, remove inactive filters, remove all filters.
- The screens menu (click on the screen name) has Save screen, Make a copy,
  Rename, Export screen results (CSV), Create new screen, Recently used, and
  Open screen (saved screens and preset screens).
- The table has column sets. Each column set shows the assets from one
  view, for example performance or risk. A "+" adds a column. A click on a
  column header sorts. The column context menu moves, changes, or removes a
  column.
- Settings: auto refresh (10 seconds, 1 minute, or never) and the currency
  of the financial data.
- The Pine Screener runs one Pine indicator on a watchlist. It needs a
  Premium plan.

Screenshots (TradingView help center images):

- [Add a filter](https://s3.amazonaws.com/cdn.freshdesk.com/data/helpdesk/attachments/production/43613437707/original/7XhTTnP3IQ4P-dqRyORREnmF5OwHkKNDow.jpeg)
- [Add a condition](https://s3.amazonaws.com/cdn.freshdesk.com/data/helpdesk/attachments/production/43613437706/original/CHTuHSqtA9douB2C6dvIEVx3uUxUbEf8UA.jpeg)
- [Reset menu](https://s3.amazonaws.com/cdn.freshdesk.com/data/helpdesk/attachments/production/43622432244/original/wcsXlwvzo1zuJJComOmcdKsmU0H03ijyUQ.png)
- [Filter panel (GIF)](https://s3.amazonaws.com/cdn.freshdesk.com/data/helpdesk/attachments/production/43588269618/original/pov7Pz7uC-SPjJAPcUSICPZM3xGbpWruDg.gif)
- [Screens menu (GIF)](https://s3.amazonaws.com/cdn.freshdesk.com/data/helpdesk/attachments/production/43588270708/original/hrcsoUYUzq1lI0NRJ2y8cWHhzvkYnQAbzw.gif)

### Finviz screener

Source: [Finviz screener help](https://finviz.com/help/screener.ashx).

- A "filters" button expands and collapses the filter area. Each filter is
  one dropdown, for example Exchange, Sector, Market Cap, P/E, RSI (14).
- "Signals" are preset event screens, for example Top Gainers, New High,
  Unusual Volume, Oversold.
- The user saves a filter combination as a preset.
- Views (Overview, Fundamental, Ownership, Performance, Financial,
  Technical, Snapshot) change the columns of the result table. The filters
  stay the same. The help page tells for each filter which views show it.
- Many columns can sort. The result can export to CSV.

### IBKR (TWS Mosaic Market Scanner, IBKR Desktop, Client Portal)

Sources:
[Market scanners lesson (IBKR Campus)](https://www.interactivebrokers.com/campus/trading-lessons/market-scanners/),
[Mosaic Market Scanner lesson](https://www.interactivebrokers.com/campus/trading-lessons/mosaic-market-scanner/),
[IBKR Desktop market screeners lesson](https://www.interactivebrokers.com/campus/trading-lessons/ibkr-desktop-market-screeners/),
[TWS API market scanner](https://www.interactivebrokers.com/docs/tws-api/doc/market-scanner/introduction.md),
[Web API scanner parameters](https://www.interactivebrokers.com/docs/web-api/v1/endpoints/scanner/iserver-scanner-parameters.md).

- The user first sets the universe: product, region, exchange, instrument
  type, and optional industry.
- Then the user selects one scan type (the sort, for example "Top % gainers")
  and adds filters. Many filters can apply, but only one sort.
- "Fields & Filters" controls the columns and the filters. The default
  columns are Financial Instrument, Last, Change, and Change %.
- The user can start from a predefined scanner or build a custom scanner.
- IBKR Desktop "MultiSort" screener: up to 10 factors. For each factor, the
  user selects if a lower value or a higher value is better. This is a
  simple ranking, not only a filter.
- Client Portal: run, refresh, save as a watchlist, reset.
- The API gives at most 50 results for each scan. The available filters
  come from `reqScannerParameters` (an XML document by asset class).

### Koyfin (vendor release notes and blog, not the help center)

Sources:
[Koyfin v3.16 release notes: Equity Screener](https://www.koyfin.com/help/release-notes/release-v3-16/),
[Koyfin blog: custom screener](https://www.koyfin.com/blog/find-best-stocks-with-screener/).

- The steps are: set the universe (country, exchange, sector), add
  criteria, set the sort, then save the screen. The result can become a
  watchlist.
- The release notes state that each metric that the user adds as a
  criterion also shows as a column in the table. This removes one step.

### Portfolio123 (not verified on an official help page)

Sources:
[AAII: Creating and Testing a Value Strategy With Portfolio123](https://www.aaii.com/journal/article/creating-and-testing-a-value-strategy-with-portfolio123).

- The workflow is screen, then ranking system, then simulation. A ranking
  system gives each stock a score from weighted factors.
- A screen can mix rules from a wizard and free-text rules in the same
  screen.
- No official help page about the editor was found. Check it in the
  product before a design decision uses it.

### Common patterns (a)

| Pattern | Products | Fit for ATrade |
|---|---|---|
| Conditions in a bar above the table, each as a token that opens a small editor | TradingView, Finviz | Carbon dismissible `Tag` for each condition, Bits UI Popover for the editor |
| Universe first, then conditions | IBKR, Koyfin | One `Select` or `Combobox` "Universe" at the start of the bar |
| A condition adds its column to the table | Koyfin | Good default. Fewer clicks. |
| Column sets (views) separate from conditions | TradingView, Finviz | `ContentSwitcher` above the table |
| Presets and saved screens in one menu | TradingView, Finviz, IBKR | Side column list of screens (like the strategy list) |
| A score from weighted factors | IBKR MultiSort, Portfolio123 | A "Score" number column, sorted by default |
| Result to watchlist, CSV export | All | Carbon batch action bar on selected rows |

## (b) No-code rule builder for entry rules and exit rules

### TrendSpider Strategy Tester

Sources:
[Creating a new strategy](https://help.trendspider.com/articles/accessing-and-using-the-strategy-tester),
[Strategy Tester FAQ](https://help.trendspider.com/kb/strategy-tester/strategy-tester-faq-markdown-html),
[Entry conditions invalidated option](https://trendspider.com/blog/software-update-new-strategy-tester-entry-conditions-invalidated-option/).

- The Strategy Tester is a panel below the chart. It has a Maximize toggle.
- Step 2 is the settings: name, timeframe, depth, chart type, extended
  hours, direction, trade cost %.
- Step 3 is the entry: a Script (a visual condition editor) or a List of
  Signals. The same visual editor builds alerts and scanner conditions.
- Step 4 is the exit. The user can select more than one: Script, Take
  Profit, Stop Loss, Trailing Stop, Entry Invalidated, # Candles Passed,
  List of Signals.
- "Entry Invalidated" closes the trade when the entry condition is no longer
  true. The user does not write a second rule.
- Limits: one entry at a time, and an exit closes 100 % of the position.
- An AI button at the top right of each Script box writes the conditions
  from text or voice.
- Step 5 is Run. The help page tells the user to Save after each change.

Screenshots (TrendSpider help images):

- [Entry conditions](https://trendspider.reamaze.com/attachments/228495501?token=7c4ab7f7336adac93dbce21c0e3d6abd03bcf9b1bcb2a6061efa0847e7c05fcf)
- [Exit conditions](https://trendspider.reamaze.com/attachments/228508374?token=2b54dbbf081ff71d7f7b3708423383a52428056116c1ea8edfb5e7a287500d80)
- [Overview](https://trendspider.reamaze.com/attachments/228519013?token=b032045bdb03b676552071ff839d0e330e0139493bd4bbb82df6b6866bd5530e)

### Composer (symphony editor)

Sources:
[How do Any/All conditions work in the symphony editor](https://help.composer.trade/article/253-how-do-any-all-conditions-work-in-the-symphony-editor),
[Tutorial: Building a Symphony](https://help.composer.trade/article/91-tutorial-building-a-symphony),
[Create with AI](https://help.composer.trade/article/108-create-with-ai).

- A strategy ("symphony") is a tree of blocks. If/Else blocks hold
  conditions, and weight blocks set the allocation.
- An If/Else block has an "Any of" / "All of" button. It joins more than one
  condition in one block.
- A "clean up" icon changes old single conditions to Any/All blocks in one
  click. It keeps the out-of-sample date of the backtest.
- "Create with AI" is on the block with the symphony name. "Insert &
  backtest" writes the blocks and runs a backtest.
- The tutorial page is a video. The text does not describe the condition
  fields.

### Code-first products for contrast

- TradingView strategies are Pine Script code in the Pine Editor
  ([How to work with Pine Editor](https://in.tradingview.com/support/solutions/43000763320-how-to-work-with-pine-editor)).
  No official no-code builder was found.
- QuantConnect strategies are Python or C# code in the Algorithm Lab. No
  no-code builder was found.

### Common patterns (b)

| Pattern | Products | Fit for ATrade |
|---|---|---|
| Separate blocks: entry, exit, settings | TrendSpider | One Carbon tile for each block, in one scroll region |
| One condition is one row: operand, comparator, operand | TrendSpider, Composer, alert builders | `Combobox` (indicator), `Select` (comparator), `Combobox` or number input (value). Row height 32px (size sm). |
| Group with "All of" / "Any of" | Composer | `ContentSwitcher` size sm at the top of the group |
| Fixed exits as check boxes with one value | TrendSpider | `Checkbox` with a number input (%, bars) |
| "Exit when the entry is no longer true" | TrendSpider | One check box. No second rule. |
| AI button in the block | TrendSpider, Composer | Out of the rule builder at first. The AI assistant writes code (map #129). |
| Builder output is code | Map #129 rule | The builder writes a normal strategy version. The editor shows the code. |

ATrade note: map #129 states that the rule builder writes a normal strategy
version. A good pattern is "builder → code, one way". The rule builder can
show the code that it writes in the read-only `CodeDiff`. The user then
saves it as a strategy version. Two-way editing (code back to blocks) is not
in any of the products found.

## (c) Comparison of results, parameter optimization, walk-forward

### TradingView Strategy Report

Source:
[TradingView Strategy Report: how to start](https://www.tradingview.com/support/solutions/43000764138-tradingview-strategy-report-how-to-start/).

- The report opens below the chart. One strategy runs on one chart.
- Metrics tab: equity chart, date range, total P&L, max drawdown,
  profitable trades %, profit factor. A Buy & hold toggle adds a second
  line. A toggle shows the run-up and drawdown of each trade.
- Performance analysis: Breakdown, Periodical, Benchmarking, Margin usage,
  Growth and decline.
- Trades analysis: Distribution (histogram), Streaks, Time patterns (by
  hour, weekday, month).
- List of trades: Trade #, Type, Date/Time, Signal, Price, Position size,
  Net P&L, Run-up, Drawdown, Cumulative P&L.
- The help page has no parameter optimization and no comparison of 2 runs.
  Only browser extensions of other vendors add an optimizer.

Screenshots:
[1](https://s3.amazonaws.com/cdn.freshdesk.com/data/helpdesk/attachments/production/43642481956/original/7nFmvtSp2bOnQEbhjPufklykkAS_o5KzNg.png),
[2](https://s3.amazonaws.com/cdn.freshdesk.com/data/helpdesk/attachments/production/43642481798/original/QZGJQqN8OK7Qg3KIMRv6qlOMlLbDCpTTBQ.png),
[3](https://s3.amazonaws.com/cdn.freshdesk.com/data/helpdesk/attachments/production/43642484688/original/GofmxOMk7RfgvUr4__eIXZ1DRS3b-L_AFQ.png).

### QuantConnect backtest results and optimization results

Sources:
[Backtest results](https://www.quantconnect.com/docs/v2/cloud-platform/backtesting/results),
[Optimization results](https://www.quantconnect.com/docs/v2/cloud-platform/optimization/results),
[Walk forward optimization](https://www.quantconnect.com/docs/v2/writing-algorithms/optimization/walk-forward-optimization).

Backtest results:

- A banner shows the runtime statistics. The Overview tab has Overall
  Statistics and Rolling Statistics. Other tabs: Orders, Logs, Report.
- The user can turn charts and series on and off and change the period.

Optimization results:

- A banner shows the job counts: Completed, Failed, Running, In Queue,
  Average Length, Total Runtime, Total. It updates while the job runs.
- "Strategy Equities" overlays the equity curves of all backtests of the
  job.
- Parameter charts: 1 parameter gives a scatter plot for each objective. 2
  parameters give a heat map. 3 parameters give a 3D plot. In a heat map,
  near cells with the same color show a stable parameter region.
- The user adds a parameter chart with "+": objective (Sharpe ratio, net
  profit, drawdown, win rate, and more) and parameter fields.
- The Backtests table has one row for each backtest: parameter values and
  objective values. The user sorts by a column, filters with Filters (a
  column, an operation, a value), and shows or hides columns. A click on a
  row opens the full backtest results.
- Closing the page does not stop the job.

Walk-forward: QuantConnect does it in the algorithm code (a scheduled
optimization on a trailing window). The documentation page shows no
special walk-forward display.

Screenshots (QuantConnect documentation images):

- [Optimization results page](https://cdn.quantconnect.com/i/tu/optimization-results-page.png)
- [Runtime statistics](https://cdn.quantconnect.com/i/tu/optimization-runtime-statistics.png)
- [Strategy equities](https://cdn.quantconnect.com/i/tu/optimization-equity-curves-1.png)
- [Parameter charts](https://cdn.quantconnect.com/i/tu/parameter-optimization-charts.png)
- [Stable parameters](https://cdn.quantconnect.com/i/tu/stable-parameters.png)
- [Backtests table](https://cdn.quantconnect.com/i/tu/optimization-results-table-202306.png)
- [Table filter (GIF)](https://cdn.quantconnect.com/i/tu/filter-optimization-results-table-202306.gif)

### Walk-forward displays (MultiCharts, StrategyQuant, TradeStation)

Sources:
[MultiCharts: Strategy Robustness](https://www.multicharts.com/trading-software/index.php/Strategy_Robustness),
[MultiCharts: walk-forward](https://multicharts.com/features/walk-forward/),
[StrategyQuant: walk-forward matrix](https://strategyquant.com/doc/walk-forward-matrix/),
[StrategyQuant: walk-forward optimization](https://strategyquant.com/doc/strategyquant/walk-forward-optimization/),
[TradeStation: walk-forward optimization](https://help.tradestation.com/10_00/eng/tradestationhelp/optimize/walk_forward.htm).

- The data splits into segments. Each segment has an in-sample part (the
  optimizer selects the parameters) and an out-of-sample part (the test).
- MultiCharts has a rolling mode and an anchored mode (the in-sample window
  grows).
- MultiCharts sets robustness criteria before the run, for example
  walk-forward efficiency. The report shows the pass or fail result in its
  lower part. A change of criteria applies without a new optimization.
- StrategyQuant shows a matrix: number of runs × out-of-sample %. Each cell
  is one walk-forward optimization. Green shows a pass, a red circle shows a
  fail. A 3×3 group with at least 7 passes is outlined. One such group makes
  the strategy robust. A click on a cell shows its results and its equity
  curve.
- The TradeStation link is for reference only. This research did not read
  its details.

### Common patterns (c)

| Pattern | Products | Fit for ATrade |
|---|---|---|
| One metric row over one equity chart over a trades table | TradingView, QuantConnect | ATrade has it: `KeyMetricRow`, `EquityDrawdownChart`, Trades tab |
| Overlay of equity curves of many runs | QuantConnect | `EquityDrawdownChart` takes 2 curves now. More curves need a curve key. |
| A sortable, filterable table of runs: parameters + metrics | QuantConnect | `DataTable` with number columns right-aligned. A click opens the backtest page. |
| Heat map for 2 parameters | QuantConnect, StrategyQuant | A table of cells with a Carbon sequential color and the value as text (not color only) |
| Scatter for 1 parameter | QuantConnect | A line or point chart in `ChartFrame` |
| Live job counts while the job runs | QuantConnect | `StatusIndicator` + counts in the panel header line |
| Walk-forward: segments as a timeline with in-sample and out-of-sample | MultiCharts, StrategyQuant | A table with one row for each segment, plus a pass/fail `StatusIndicator` |
| Buy & hold as a second line | TradingView | Fits the second curve of `EquityDrawdownChart` |

ATrade note: 3D plots do not fit Carbon flat surfaces and are hard to read.
A heat map with a selector for the 3rd parameter is a better fit.

## (d) AI assistant conversation that changes code and runs backtests

### QuantConnect Mia

Sources:
[Mia (predefined agent)](https://www.quantconnect.com/docs/v2/ai-assistance/predefined-agents/mia),
[AI assistance: getting started](https://www.quantconnect.com/docs/v2/ai-assistance/getting-started),
[Announcement: your AI quant developer](https://www.quantconnect.com/announcements/19846/your-ai-quant-developer/).

- "Ask Mia" is a tab at the right side of the Algorithm Lab IDE. The user
  writes a strategy description there.
- Mia can read and write the project files. It writes code, compiles, fixes
  compile errors, runs a backtest, reads runtime errors and logs, changes
  the code, and runs again.
- Its tools include backtest, optimization, live algorithm, notebook, and
  notification tools. The page states that the decision about live capital
  stays with the user.
- In the Research Pipeline, the user adds a card, writes the idea, selects
  the agent "Mia", and clicks "Deploy Mia". "Open Project" at the top of the
  conversation opens the project.
- The documentation does not show how a code change shows in the chat
  (diff or no diff), or how a tool call shows.
- Cost: tokens of the support plan, then QuantConnect Credit.

Screenshots (QuantConnect documentation images):

- [Add a card](https://cdn.quantconnect.com/i/tu/pipeline-img-2.webp)
- [Select the agent](https://cdn.quantconnect.com/i/tu/pipeline-img-4.webp)
- [Prompt the agent](https://cdn.quantconnect.com/i/tu/pipeline-img-5.webp)
- [Open project](https://cdn.quantconnect.com/i/tu/pipeline-img-7.webp)

### Composer: Create with AI and Trade with AI

Sources:
[Create with AI](https://help.composer.trade/article/108-create-with-ai),
[What is Trade with AI?](https://help.composer.trade/article/254-what-is-trade-with-ai).

- Trade with AI is on the Discover page. One input is both the chat start
  and the search field.
- The AI asks some questions and builds a symphony. Each result shows its
  logic, its instruments, its backtest, and its risk statistics.
- The user can change the result in the normal editor.
- Nothing trades without the approval of the user.
- Usage has a weekly token allowance.

### TrendSpider Sidekick

Sources:
[Strategy Tester FAQ](https://help.trendspider.com/kb/strategy-tester/strategy-tester-faq-markdown-html),
[Sidekick](https://help.trendspider.com/kb/sidekick-ai/trendspider-sidekick).

- The AI button in a condition box writes or changes the conditions.
- "AI Explain" at the right of the Strategy Tester explains the backtest
  results and suggests changes.
- Sidekick can write custom indicators as code and scan in natural
  language.

### Code editor agents (pattern for code changes)

Source:
[VS Code: review and revert agent changes](https://code.visualstudio.com/docs/agents/run/review-code-edits).

- The agent edits go into a set of pending changes. Each changed file shows
  its diff. The user selects Keep or Undo for each change, for each file, or
  for all files.
- A checkpoint is saved before each request. "Restore Checkpoint" sets the
  files back and removes the later turns.
- An edit of a sensitive file can need an approval before it is saved.

### Carbon for AI

Sources:
[Carbon for AI](https://carbondesignsystem.com/guidelines/carbon-for-ai/),
[AI label usage](https://carbondesignsystem.com/components/ai-label/usage/),
[Carbon AI Chat](https://chat.carbondesignsystem.com/tag/latest/docs/documents/Demo_and_Examples.html).

- Carbon v11 has an AI label component. It marks content that AI made. The
  usage page shows one label on the full conversation and one label on a
  single message.
- Carbon AI Chat (`@carbon/ai-chat`) is a separate chat framework. It is
  not part of `@carbon/styles`. ATrade does not use Carbon React or web
  components (`docs/architecture.md` section 13), so ATrade must write the
  chat panel itself from Carbon tiles, text area, buttons, and code
  snippets.

### Common patterns (d)

| Pattern | Products | Fit for ATrade |
|---|---|---|
| Chat as a side panel of the code editor | QuantConnect, VS Code | A right `SideColumn` "Assistant" on the strategy page. It collapses to a 32px rail. |
| The agent loop: write, check, backtest, read errors, change | QuantConnect Mia | Show each step as one line with a `StatusIndicator` in the conversation |
| Code changes as a pending diff with Keep and Undo | VS Code | ATrade has `CodeDiff`. Show the diff in the chat or in the editor panel. "Keep" saves a new strategy version. |
| A result card with metrics and a link to the run | Composer | A Carbon tile with `KeyMetricRow` values and a link to the backtest page |
| The user approves actions with real effect | Composer, QuantConnect, VS Code | Map #129: the assistant never sends a paper order or starts a forward test. Each save and each backtest is visible in the chat. |
| AI label on AI content | Carbon for AI | Carbon AI label on each assistant message |
| "Explain these results" from the results panel | TrendSpider | A button in the backtest panel that opens the assistant with the backtest as context |

## Proposed layout for ATrade (for the grilling tickets)

These are options, not decisions. The grilling tickets of map #129 decide.

1. **Screen page** (`/screens/<id>`): side column "Screens" (saved screens
   and presets). Main panel: header line with the screen name and a "Run
   screen" button. Under it, a condition bar of Carbon tags with a "+"
   button. Under it, the screen result `DataTable` with a `ContentSwitcher`
   for column sets and a batch action bar ("Add to watchlist", "Backtest
   selected").
2. **Rule builder**: a tab of the editor panel on the strategy page, next
   to `strategy.py`. Blocks Entry, Exit, and Settings as Carbon tiles. Each
   condition is a 32px row. The output is code. "Save version" saves it as a
   normal strategy version.
3. **Parameter sweep and walk-forward**: a workbench like the backtest page.
   Side column with the jobs. Main panel: job status line, heat map or
   scatter, and the overlay of equity curves. Lower panel: tabs "Runs"
   (table of parameter values and metrics) and "Walk-forward" (one row for
   each segment).
4. **AI assistant**: a right side column on the strategy page. Each message
   has the AI label. Each code change shows as a `CodeDiff` with "Keep as
   new version" and "Discard". Each backtest that the assistant starts shows
   as a status line and then as a metric tile row with a link.

## Facts not verified

- The current Koyfin screen editor UI. Only 2022 release notes and a blog
  post were available.
- The Portfolio123 screen, ranking, and simulation editors. No official help
  page was found.
- How QuantConnect Mia shows a code change and a tool call in the chat.
  The documentation does not describe it.
- An official TradingView AI assistant in the Pine Editor. No official page
  was found.
