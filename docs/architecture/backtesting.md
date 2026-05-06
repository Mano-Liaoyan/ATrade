---
status: active
owner: maintainer
updated: 2026-05-06
summary: Authoritative contract for provider-neutral saved backtesting backend APIs, SignalR updates, and terminal frontend usage.
see_also:
  - ../INDEX.md
  - modules.md
  - paper-trading-workspace.md
  - analysis-engines.md
  - provider-abstractions.md
  - ../../README.md
  - ../../PLAN.md
---

# Backtesting Architecture

`ATrade.Backtesting` is the provider-neutral backend module for saved,
asynchronous paper backtest requests. It owns the browser-facing contract for
creating, listing, reading, cancelling, retrying, executing, and streaming saved
runs while keeping market-data, analysis/LEAN runtime, and persistence details
behind provider-neutral seams.

## Module Responsibilities

- Validate single-symbol backtest creation requests before persistence.
- Allow only built-in strategy IDs: `sma-crossover`, `rsi-mean-reversion`, and
  `breakout`, with server-side defaulting and validation for each strategy's
  bounded parameter set.
- Use the shared market-data chart range presets (`1min`, `5mins`, `1h`, `6h`,
  `1D`, `1m`, `6m`, `1y`, `5y`, and `all`) and `MarketDataSymbolIdentity`.
- Snapshot effective paper capital from `ATrade.Accounts.IPaperCapitalService`
  at run creation time.
- Persist saved runs in Postgres under the namespaced
  `atrade_backtesting.saved_backtest_runs` table.
- Run queued jobs inside the API process with a hosted coordinator that claims
  one queued row at a time, marks it `running`, and finalizes terminal state
  durably.
- Fetch candles server-side through `IMarketDataService`, then invoke
  `IAnalysisEngineRegistry` with the saved strategy and optional engine id.
- Broadcast safe browser-facing job updates over `/hubs/backtests`.
- Keep all API and persisted payloads provider-neutral; LEAN or any future runner
  must remain an implementation detail rather than a route name or frontend type.

## Saved Run Contract

A saved run envelope contains:

- `id` — server-generated `bt_...` run id.
- `status` — one of `queued`, `running`, `completed`, `failed`, or `cancelled`.
- `sourceRunId` — populated only for retry-created runs.
- `request` — normalized request snapshot with symbol identity, built-in strategy
  id, optional analysis engine id, JSON parameter bag, chart range, cost model,
  slippage bps, and benchmark mode.
- `capital` — `initialCapital`, `currency`, and `capitalSource` captured at
  creation time.
- timestamps for creation/update/start/completion.
- safe `error` details and an optional provider-neutral completed `result` JSON
  envelope containing summary metrics, equity curve, simulated trades/signals,
  buy-and-hold benchmark, accounting inputs, source metadata, and engine
  metadata.

Created runs start as `queued`. The hosted runner transitions claimed jobs to
`running`, then to `completed`, `failed`, or `cancelled`. On API startup,
interrupted rows left in `running` are marked `failed` with
`backtest-run-interrupted`; queued rows are preserved for normal execution.
`POST /api/backtests/{id}/cancel` deterministically cancels queued rows and
requests best-effort cancellation for running rows through runner-owned
cancellation tokens before marking the row `cancelled`. `POST /api/backtests/{id}/retry`
is allowed only for `failed` or `cancelled` runs and creates a new queued run
from the saved source request snapshot instead of mutating the source run.

## Capital Snapshot

Backtest creation calls `IPaperCapitalService.GetAsync(...)` and requires a
positive effective capital source. The current source order is inherited from
`ATrade.Accounts`: authenticated IBKR paper balance when available, otherwise the
Postgres-backed local paper ledger, otherwise `unavailable`. Creation is blocked
with `backtest-capital-unavailable` when no positive effective source exists.

The saved run captures the amount, currency, and source string at creation time;
later changes to local fallback capital or broker availability do not rewrite
existing run snapshots. Retry creates a new run and therefore captures current
effective capital for the retry while reusing the original request snapshot.

## Built-In Strategy And Cost Inputs

Saved backtests currently accept only three built-in strategy ids; custom code,
script/workspace fields, order-routing fields, direct bars, and multi-symbol or
portfolio payloads are rejected before persistence and before any LEAN invocation.
The supported strategy catalog is:

| Strategy id | Parameters and defaults | Validation notes |
| --- | --- | --- |
| `sma-crossover` | `shortWindow = 20`, `longWindow = 50` | Integer windows; short is bounded 2-250, long is bounded 3-500, and long must be greater than short. |
| `rsi-mean-reversion` | `rsiPeriod = 14`, `oversoldThreshold = 30`, `overboughtThreshold = 70` | Period is an integer 2-100; thresholds are decimals 1-99, and oversold must be below overbought. |
| `breakout` | `lookbackWindow = 20` | Integer lookback bounded 2-250. |

The cost model is part of the saved request snapshot. `commissionPerTrade`,
`commissionBps`, and `slippageBps` default to `0`, are non-negative, round to 4
decimal places, and are each bounded at `1000` (currency units for per-trade
commission, basis points for commission/slippage). Currency defaults to the
paper-capital currency (`USD` today). Commission and slippage are applied to
internal simulated entry/exit accounting only. They must not route broker orders,
configure LEAN brokerage models, or call ATrade order endpoints.

`benchmarkMode` defaults to `buy-and-hold`; `none` is the only opt-out. The
buy-and-hold benchmark is calculated from the same server-fetched candle window
and initial capital as the strategy result and is labelled separately from the
strategy return.

## REST API

`ATrade.Api` composes `AddBacktestingModule(builder.Configuration)` after the
Accounts module is available and exposes:

| Endpoint | Behavior |
| --- | --- |
| `POST /api/backtests` | Validate the request, snapshot current effective capital, persist a queued run, and return `202 Accepted` with the saved run envelope. |
| `GET /api/backtests?limit=...` | List recent saved runs for the local workspace, newest first. |
| `GET /api/backtests/{id}` | Return one saved run or `404 backtest-run-not-found`. |
| `POST /api/backtests/{id}/cancel` | Cancel a queued/running run at the saved-run contract level; non-cancellable statuses return `409 backtest-invalid-status-transition`. |
| `POST /api/backtests/{id}/retry` | Create a new queued run from a failed/cancelled source run's saved request snapshot; the source run is not mutated. |

Validation failures return safe `BacktestError` payloads. Storage failures return
`503 backtest-storage-unavailable`. Missing capital and invalid status
transitions return `409`.

## Frontend Terminal Workspace Contract

The enabled `BACKTEST` rail module is implemented only through browser-facing
`ATrade.Api` contracts:

- `frontend/types/backtesting.ts` mirrors the safe saved-run, capital, strategy,
  result, error, and SignalR update payloads plus the built-in strategy catalog
  used by the form.
- `frontend/lib/backtestClient.ts` builds all HTTP and SignalR URLs with the
  centralized API base-url helper. It calls only `GET /api/accounts/paper-capital`,
  `PUT /api/accounts/local-paper-capital`, the `/api/backtests` create/list/get,
  cancel, retry endpoints, and `/hubs/backtests`; it must not import or connect
  to Postgres, TimescaleDB, Redis, NATS, IBKR/iBeam, LEAN, or any provider
  runtime.
- `frontend/lib/terminalBacktestWorkflow.ts` owns the terminal state machine for
  loading effective capital, updating local fallback capital, validating a
  single-symbol built-in-strategy draft, creating runs, selecting history/detail,
  selecting only completed runs with persisted result/equity data for comparison,
  projecting comparison metrics/source/capital metadata from saved envelopes,
  normalizing strategy and buy-and-hold benchmark equity curves from saved
  result payloads, cancelling queued/running runs, retrying failed/cancelled runs
  as newly created saved runs, and merging SignalR status/result/error updates.
- SignalR is the live status path. HTTP is used for initial capital/history/detail
  loads, explicit reload actions, run creation/actions, and reconnect recovery;
  the frontend must not invent polling-only success states or fake result
  envelopes when streaming is unavailable.
- `frontend/components/terminal/TerminalBacktestWorkspace.tsx` renders the
  paper-capital panel, strategy/range/cost/benchmark form, live status panel,
  saved history, completed detail summaries/benchmark/trades/signals/source
  metadata, completed-run comparison selection, a side-by-side metric table,
  selected-run cards, and an SVG equity overlay that draws only persisted
  strategy equity curves and persisted buy-and-hold benchmark curves from saved
  result envelopes. Comparison introduces no new backend endpoint: it reuses
  saved `/api/backtests` list/detail result fields for strategy, symbol, range,
  capital source, return, drawdown, win rate, trade count, final equity,
  benchmark return, status, and source metadata. Queued, running, failed, and
  cancelled runs remain visible in history but are not selectable for comparison.
  Create is disabled until a positive effective capital source is available, and
  the UI never shows order tickets, buy/sell controls, broker routing, export
  controls, optimization, account identifiers, direct bars, demo runs, synthetic
  equity curves, or fixture trades.

## Runner Lifecycle And Provider Handling

`BacktestRunHostedService` initializes the schema, fails interrupted `running`
rows on startup, and drains queued rows on a polling loop. `ClaimNextQueuedRun`
uses a Postgres `FOR UPDATE SKIP LOCKED` claim and a status guard so overlapping
service ticks or multiple local API instances do not execute the same run twice.
Terminal runner updates only finalize rows still in `running`, so a concurrent
cancel request cannot be overwritten by a late completion.

The execution pipeline never accepts browser-submitted bars. It uses the saved
`MarketDataSymbolIdentity` and chart range to call `IMarketDataService.GetCandlesAsync(...)`.
Provider-not-configured, provider-unavailable, authentication-required,
unsupported-symbol, unsupported-range, and empty-candle states become failed
saved runs with safe market-data error codes/messages; no synthetic candles or
fake successful results are created.

When candles are available, the runner calls `IAnalysisEngineRegistry.AnalyzeAsync(...)`
with normalized OHLCV bars, the saved optional `engineId`, strategy id,
strategy parameters, and backtest settings. `analysis-engine-not-configured`,
`analysis-engine-unavailable`, and invalid analysis requests become failed saved
runs with generic safe messages. Completed analysis results are persisted as a
provider-neutral `tp-061.backtest-result.v1` JSON envelope containing engine,
symbol, chart range, market-data source, signals, metrics, backtest summary,
equity curve, simulated trades, buy-and-hold benchmark, accounting inputs, and
source metadata. The envelope intentionally omits LEAN workspace paths, process
command lines, credentials, account identifiers, gateway URLs, tokens, cookies,
session details, and raw direct-bar submissions.

## Completed Result Envelope

A completed saved run's `result` uses provider-neutral names rather than LEAN
DTOs:

- `schemaVersion = "tp-061.backtest-result.v1"`, `status`, `strategyId`, and the
  normalized parameter bag used for execution.
- `engine`, `symbol`, `chartRange`, `generatedAtUtc`, and `source` metadata.
- `signals` and `metrics` projected from the analysis result.
- `backtest` summary with `startUtc`, `endUtc`, `initialCapital`, `finalEquity`,
  `totalReturnPercent`, `tradeCount`, `winRatePercent`, `maxDrawdownPercent`,
  and `totalCost`.
- `equityCurve` points with time, equity, and drawdown percent.
- `trades` with entry/exit times, direction, prices, quantity, gross/net P&L,
  return percent, total cost, and exit reason.
- `benchmark` when enabled, currently `mode = "buy-and-hold"`, label, initial
  capital, final equity, total return percent, and benchmark equity curve.
- `accounting` with commission-per-trade, commission bps, slippage bps, and
  currency.

## SignalR Updates

`ATrade.Api` maps `/hubs/backtests` to `BacktestRunsHub`. The runner and REST
handlers publish best-effort events named `backtestRunCreated`,
`backtestRunStatusChanged`, `backtestRunCompleted`, `backtestRunFailed`, and
`backtestRunCancelled`. Payloads include safe run id/status/timestamps,
symbol identity, strategy id, optional engine id, chart range, safe error, and
safe result envelope only; paper-capital amounts, account identifiers,
credentials, gateway URLs, LEAN workspace paths, raw command lines, tokens,
cookies, and sessions are not broadcast. SignalR delivery is best-effort and
HTTP/Postgres state remains authoritative when no clients are connected.

## Persistence And Redaction

The Postgres schema stores local `user_id` / `workspace_id` scope, `run_id`,
optional `source_run_id`, status, canonical `request_json`, capital snapshot,
safe error fields, optional `result_json`, and timestamps. It intentionally has
no columns for account identifiers, credentials, raw gateway URLs, tokens,
cookies, session details, direct candle arrays, or order-routing fields.

Request validation and persistence safety checks reject:

- direct browser-submitted market data (`bars`, `candles`, OHLCV arrays, etc.);
- custom strategy code, scripts, algorithms, LEAN workspace paths, or source
  snippets;
- account identifiers, credentials, gateway URLs, tokens, cookies, sessions, or
  broker/order-routing fields;
- multi-symbol or portfolio payloads.

Backtests load market-data bars on the server. The browser must submit only
provider-neutral identity, built-in strategy id, optional engine id, bounded JSON
parameters, chart range, cost/slippage settings, and benchmark mode.

## Verification

Primary verification entry points:

```bash
dotnet test tests/ATrade.Backtesting.Tests/ATrade.Backtesting.Tests.csproj --nologo --verbosity minimal
bash tests/apphost/backtesting-api-contract-tests.sh
bash tests/apphost/backtesting-runner-signalr-tests.sh
bash tests/apphost/backtesting-strategy-result-tests.sh
bash tests/apphost/frontend-terminal-backtest-workspace-tests.sh
bash tests/apphost/frontend-terminal-backtest-comparison-tests.sh
cd frontend && npm run build
dotnet test ATrade.slnx --nologo --verbosity minimal
```

The apphost contract tests cover successful queued creation with the runner
disabled for REST-only assertions, validation failures, missing capital,
not-found responses, cancel/retry behavior, runner/SignalR source wiring,
built-in strategy/result contract strings, no-custom-code/no-order guardrails,
and redaction of sensitive values from API responses, SignalR payloads, and
persisted saved-run rows. The terminal backtest workspace validation covers the
enabled rail registration, API/hub paths, capital panel, strategy form strings,
history/detail/cancel/retry/status UI, no fake result states, no order controls,
and frontend-only `ATrade.Api` browser boundary. The comparison validation covers
completed-run-only selection, comparison metric labels, strategy/benchmark equity
overlay strings, no export controls, no fake/demo comparison data, and no direct
provider/runtime/database access.
