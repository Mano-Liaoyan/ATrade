---
status: active
owner: maintainer
updated: 2026-04-30
summary: Provider-neutral analysis engine contract and the LEAN provider implementation for backtesting, signal, and metric providers without coupling API/frontend payloads to LEAN.
see_also:
  - ../INDEX.md
  - overview.md
  - modules.md
  - provider-abstractions.md
  - paper-trading-workspace.md
  - ../../README.md
  - ../../PLAN.md
---

# Analysis Engine Abstraction

ATrade analysis engines are provider-neutral strategy/backtest providers. The
current implementation ships the core `ATrade.Analysis` contract plus
`ATrade.Analysis.Lean`, the first concrete provider. LEAN is invoked only behind
that provider seam; API and frontend payloads continue to use ATrade request and
result records instead of QuantConnect/LEAN types.

## 1. Goals

- Keep browser-facing analysis discovery and run payloads stable across LEAN
  and future engines.
- Feed analysis engines with ATrade-normalized market-data shapes, not runtime-
  specific quote/bar objects.
- Include engine and source metadata in every result so the UI can explain
  where a signal, metric, or backtest summary came from.
- Return an explicit `analysis-engine-not-configured` result when no provider
  is configured instead of fake production signals.
- Keep concrete runtime packages and process details isolated in provider
  modules such as `ATrade.Analysis.Lean`.
- Preserve the paper-trading safety rule: analysis engines may generate
  signals/metrics, but they must not route brokerage orders or enable live
  trading.

## 2. Provider-Neutral Contracts

Provider-neutral analysis contracts live in `src/ATrade.Analysis`.

Core types:

- `IAnalysisEngine` — concrete provider seam with `Metadata`, `Capabilities`,
  and `AnalyzeAsync`.
- `IAnalysisEngineRegistry` — API-facing discovery/run seam that chooses a
  configured engine or falls back to the no-engine result.
- `AnalysisEngineMetadata` — stable engine id, display name, provider label,
  version, state, and optional message.
- `AnalysisEngineCapabilities` — flags for signals, backtests, metrics,
  optimization, and external-runtime requirements.
- `AnalysisRequest` — normalized request containing `MarketDataSymbolIdentity`,
  timeframe, requested time, and `IReadOnlyList<OhlcvCandle>` bars from
  `ATrade.MarketData`.
- `AnalysisResult` — status, engine metadata, source metadata, normalized
  symbol/timeframe, generated time, signals, metrics, optional backtest summary,
  and optional error.
- `AnalysisSignal`, `AnalysisMetric`, and `BacktestSummary` — provider-neutral
  output shapes for UI display and later persistence.
- `NoConfiguredAnalysisEngine` — safe fallback implementation returning
  `analysis-engine-not-configured` with empty signals/metrics/backtest output.

The contract intentionally references `ATrade.MarketData` normalized records
such as `MarketDataSymbolIdentity` and `OhlcvCandle`. It must not accept or
return engine-runtime-specific objects.

## 3. API Surface

`ATrade.Api` composes `AddAnalysisModule()` and `AddLeanAnalysisEngine(...)`.
The LEAN provider is registered only when configuration selects it.

- `GET /api/analysis/engines` — returns available engine descriptors. With no
  configured provider, it returns a single `not-configured` descriptor whose
  capabilities do not claim production analysis support. With LEAN selected, it
  returns `engineId = "lean"` with signal/backtest/metric capabilities and
  `requiresExternalRuntime = true`.
- `POST /api/analysis/run` — accepts a provider-neutral analysis request. When
  callers supply only `symbolCode` + `timeframe`, the API obtains candles from
  the configured `IMarketDataService` and builds an `AnalysisRequest` over those
  normalized bars. With no configured provider, it returns HTTP 503 with
  `status = "not-configured"`, error code `analysis-engine-not-configured`, and
  no signals, metrics, or backtest summary. With LEAN selected, it forwards the
  normalized bars to `ATrade.Analysis.Lean`.

These endpoints are not LEAN endpoints. They must not expose QuantConnect types,
LEAN project files, or provider-specific DTO names.

## 4. LEAN Provider Implementation

`src/ATrade.Analysis.Lean` is the first concrete analysis provider. The chosen
integration approach is an official LEAN runtime process boundary:

1. ATrade converts normalized `OhlcvCandle` bars into a temporary LEAN project
   workspace containing `atrade-bars.csv`, `main.py`, a minimal project
   `config.json`, and, for managed Docker execution, a generated
   `lean-engine-config.json` launcher configuration.
2. `main.py` defines an analysis-only `QCAlgorithm` that reads the ATrade CSV,
   calculates a moving-average crossover signal set, risk/return metrics, and a
   backtest summary, and emits a single `ATRADE_ANALYSIS_RESULT:` JSON marker.
3. `LeanRuntimeExecutor` supports two explicit runtime paths. CLI mode invokes
   the configured official LEAN CLI command (`lean backtest ...`) and therefore
   inherits any local QuantConnect CLI/account requirements. Docker mode avoids
   the paid CLI workspace path: when `ATRADE_LEAN_RUNTIME_MODE=docker` is
   selected through the AppHost contract, Aspire declares a visible
   `lean-engine` container from the configured LEAN engine image, mounts the
   shared LEAN workspace root, and passes managed-container metadata into
   `ATrade.Api`; the executor then runs `dotnet QuantConnect.Lean.Launcher.dll
   --config <generated-config>` through `docker exec` against that managed
   container instead of calling `lean backtest` or starting a hidden `docker run`
   container.
4. `LeanAnalysisResultParser` maps the emitted marker into provider-neutral
   `AnalysisResult`, `AnalysisSignal`, `AnalysisMetric`, and `BacktestSummary`
   records.
5. Runtime absence, timeouts, non-zero exits, and parse failures return explicit
   `analysis-engine-unavailable` errors rather than fake successful analysis.

The provider includes guardrails that reject generated algorithm source
containing brokerage/order-routing tokens such as `MarketOrder`,
`SetBrokerageModel`, `SetLiveMode`, or `/api/orders`. The generated algorithm
sets cash for backtest accounting but does not add brokerage models, route
orders, call IBKR order endpoints, or enable live mode.

## 5. Configuration Contract

Committed templates keep analysis disabled by default and expose only safe,
non-secret placeholders:

```text
ATRADE_ANALYSIS_ENGINE=none
ATRADE_LEAN_RUNTIME_MODE=cli
ATRADE_LEAN_CLI_COMMAND=lean
ATRADE_LEAN_DOCKER_COMMAND=docker
ATRADE_LEAN_DOCKER_IMAGE=quantconnect/lean:latest
ATRADE_LEAN_WORKSPACE_ROOT=artifacts/lean-workspaces
ATRADE_LEAN_TIMEOUT_SECONDS=45
ATRADE_LEAN_KEEP_WORKSPACE=false
ATRADE_LEAN_MANAGED_CONTAINER_NAME=atrade-lean-engine
ATRADE_LEAN_CONTAINER_WORKSPACE_ROOT=/workspace
```

To enable LEAN locally, copy `.env.template` to ignored `.env` and set
`ATRADE_ANALYSIS_ENGINE=Lean`. For the no-paid-account local path, use AppHost-managed Docker mode: set
`ATRADE_ANALYSIS_ENGINE=Lean`, set `ATRADE_LEAN_RUNTIME_MODE=docker`, keep or
override `ATRADE_LEAN_DOCKER_IMAGE` with a LEAN engine image such as
`quantconnect/lean:latest`, and start through `./start run`; the Aspire graph
then shows a `lean-engine` resource and mounts `ATRADE_LEAN_WORKSPACE_ROOT` into
that container at `ATRADE_LEAN_CONTAINER_WORKSPACE_ROOT`. The API receives only
these non-secret LEAN settings and invokes the engine launcher directly inside
the managed container. CLI mode remains available for users who already have a
usable LEAN CLI workspace by keeping `ATRADE_LEAN_RUNTIME_MODE=cli`, installing
or configuring the official `lean` command, and ensuring
`ATRADE_LEAN_WORKSPACE_ROOT` is at or under an initialized LEAN workspace
containing `lean.json` from `lean init`. If Docker mode is selected but the
managed container metadata is absent, the container is not running, the Docker
command or engine image is unavailable, the runtime exits non-zero, or the
runtime times out, `/api/analysis/run` returns HTTP 503 with
`analysis-engine-unavailable`, empty signals/metrics, and no backtest summary.
No LEAN setting may contain broker credentials or account identifiers.

Automated tests do not require LEAN to be installed. Unit tests exercise the
adapter through deterministic runtime fixtures; AppHost verification publishes
LEAN-enabled manifests, verifies `GET /api/analysis/engines` from the AppHost
configuration handoff, proves explicit unavailable failures, and reports a clean
skip for the optional managed-runtime smoke when Docker or the configured image
is unavailable.

## 6. Result Shape

A successful LEAN run returns the same provider-neutral result shape any future
engine must return:

- `status = "completed"`
- `engine.engineId = "lean"` and provider/display/version metadata
- `source.provider = "LEAN"` plus runtime/workspace source text
- the input `MarketDataSymbolIdentity` and timeframe
- zero or more `AnalysisSignal` entries, currently moving-average crossover
  signals with direction, confidence, time, and rationale
- `AnalysisMetric` entries such as total return, max drawdown, and signal count
- `BacktestSummary` with start/end window, initial capital, final equity, total
  return, trade count, and win rate

Errors use the same `AnalysisResult` envelope with `status = "failed"` or
`not-configured`, an `AnalysisError`, and empty signal/metric/backtest payloads
where appropriate.

## 7. Replacing Or Adding Engines

Another engine should replace or complement LEAN by implementing `IAnalysisEngine`
in a separate provider module and registering that module conditionally through
configuration. It must:

- consume `AnalysisRequest` over normalized ATrade bars
- emit `AnalysisResult` without provider-specific DTOs
- translate runtime errors into `AnalysisError` codes and safe states
- avoid live trading, brokerage routing, and automatic order placement
- update this document and provider/module/workspace docs when its runtime and
  configuration contract are introduced

The API/frontend should not change when engines swap. Provider selection belongs
in DI/configuration and `engineId`, not in endpoint paths or frontend type names.

## 8. Verification

The contract and LEAN provider are verified by:

- `tests/ATrade.Analysis.Tests/` for core contract and fallback behavior
- `tests/ATrade.Analysis.Lean.Tests/` for input conversion, managed-runtime
  option binding, CLI/managed-Docker command construction, service registration,
  result parsing, timeout/error handling, and no-order guardrails
- `tests/apphost/analysis-engine-contract-tests.sh` for provider-neutral API
  contract and no-engine HTTP behavior
- `tests/apphost/lean-analysis-engine-tests.sh` for LEAN registration,
  managed-runtime configuration placeholders, provider-neutral boundaries,
  optional runtime skip behavior, and no trading side effects
- `tests/apphost/lean-aspire-runtime-tests.sh` for disabled-default AppHost
  manifests, Docker-mode `lean-engine` manifest/resource assertions, API engine
  discovery from AppHost handoff, explicit unavailable runtime responses, and
  optional managed-runtime smoke skipping
- `tests/apphost/frontend-trading-workspace-tests.sh` for analysis panel source
  markers in the paper-trading UI

## 9. Change Control

Changes that add engine capabilities, alter request/result payloads, introduce a
new runtime dependency, or weaken no-configured/unavailable/no-order behavior
must update this document and the linked active architecture docs in the same
change.
