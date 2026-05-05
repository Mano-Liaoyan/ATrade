---
status: active
owner: maintainer
updated: 2026-05-06
summary: Authoritative contract for the provider-neutral saved backtesting backend module and REST API.
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
creating, listing, reading, cancelling, and retrying saved runs while later runner
work can attach execution/result production behind the same persisted run IDs.

## Module Responsibilities

- Validate single-symbol backtest creation requests before persistence.
- Allow only built-in strategy IDs: `sma-crossover`, `rsi-mean-reversion`, and
  `breakout`.
- Use the shared market-data chart range presets (`1min`, `5mins`, `1h`, `6h`,
  `1D`, `1m`, `6m`, `1y`, `5y`, and `all`) and `MarketDataSymbolIdentity`.
- Snapshot effective paper capital from `ATrade.Accounts.IPaperCapitalService`
  at run creation time.
- Persist saved runs in Postgres under the namespaced
  `atrade_backtesting.saved_backtest_runs` table.
- Keep all API and persisted payloads provider-neutral; LEAN or any future runner
  must remain an implementation detail rather than a route name or frontend type.

## Saved Run Contract

A saved run envelope contains:

- `id` — server-generated `bt_...` run id.
- `status` — one of `queued`, `running`, `completed`, `failed`, or `cancelled`.
- `sourceRunId` — populated only for retry-created runs.
- `request` — normalized request snapshot with symbol identity, built-in strategy
  id, JSON parameter bag, chart range, cost model, slippage bps, and benchmark
  mode.
- `capital` — `initialCapital`, `currency`, and `capitalSource` captured at
  creation time.
- timestamps for creation/update/start/completion.
- safe `error` details and an optional provider-neutral `result` JSON placeholder.

Created runs start as `queued`. Runner tasks in later work may transition to
`running`, `completed`, `failed`, or `cancelled`. `POST /api/backtests/{id}/cancel`
performs best-effort contract-level cancellation for `queued` or `running` runs.
`POST /api/backtests/{id}/retry` is allowed only for `failed` or `cancelled`
runs and creates a new queued run from the saved source request snapshot instead
of mutating the source run.

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

Backtests load market-data bars on the server in later runner work. The browser
must submit only provider-neutral identity, built-in strategy id, bounded JSON
parameters, chart range, cost/slippage settings, and benchmark mode.

## Verification

Primary verification entry points:

```bash
dotnet test tests/ATrade.Backtesting.Tests/ATrade.Backtesting.Tests.csproj --nologo --verbosity minimal
bash tests/apphost/backtesting-api-contract-tests.sh
dotnet test ATrade.slnx --nologo --verbosity minimal
```

The apphost contract test covers successful queued creation, validation failures,
missing capital, not-found responses, cancel/retry behavior, and redaction of
sensitive values from API responses and persisted saved-run rows.
