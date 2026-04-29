---
status: active
owner: maintainer
updated: 2026-04-29
summary: Provider-neutral analysis engine contract for backtesting, signal, and metric providers without coupling API/frontend payloads to LEAN.
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
current implementation defines the contract and API surface only; it does not
run LEAN or any other production analysis runtime yet.

The seam exists so LEAN can be the first implementation while the API,
frontend, and persisted payloads stay independent from LEAN-specific types.
Future engines must plug in behind the same `ATrade.Analysis` contracts.

## 1. Goals

- Keep browser-facing analysis discovery and run payloads stable across LEAN
  and future engines.
- Feed analysis engines with ATrade-normalized market-data shapes, not runtime-
  specific quote/bar objects.
- Include engine and source metadata in every result so the UI can explain
  where a signal, metric, or backtest summary came from.
- Return an explicit `analysis-engine-not-configured` result when no provider
  is configured instead of fake production signals.
- Keep API and core contracts free of LEAN package references until a concrete
  provider module is added by a later task.

## 2. Module And Contracts

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

`ATrade.Api` composes `AddAnalysisModule()` and exposes:

- `GET /api/analysis/engines` — returns available engine descriptors. With no
  configured provider, it returns a single `not-configured` descriptor whose
  capabilities do not claim production analysis support.
- `POST /api/analysis/run` — accepts `AnalysisRequest` and returns
  `AnalysisResult`. With no configured provider, it returns HTTP 503 with
  `status = "not-configured"`, error code `analysis-engine-not-configured`, and
  no signals, metrics, or backtest summary.

These endpoints are the API contract that the frontend should bind to. They are
not LEAN endpoints, and they should not expose LEAN terminology in request or
response shapes.

## 4. Source And Engine Metadata

Every `AnalysisResult` carries two metadata blocks:

- `engine` identifies the analysis provider/runtime that produced the result,
  including provider id, display name, version, state, and message.
- `source` identifies the source of the result payload, such as
  `analysis-engine-not-configured` today or a future provider-specific source id
  emitted by a concrete analysis engine.

Frontend surfaces should display this metadata similarly to market-data source
metadata. The metadata is required even for errors so operators can distinguish
between no configured engine, an unavailable runtime, and future successful
provider output.

## 5. No-Configured-Engine Behavior

The default module registration does not fabricate analysis. Until a concrete
engine is registered, discovery and run requests make the missing provider
explicit:

- discovery shows `engineId = "not-configured"` and state `not-configured`
- run requests return `analysis-engine-not-configured`
- signal, metric, and backtest arrays stay empty/null
- HTTP callers receive a 503 rather than a successful fake analysis payload

This behavior is part of the safety contract. Future providers may replace the
fallback by registering an `IAnalysisEngine`; they must still preserve explicit
unavailable/not-configured errors when their runtime cannot execute.

## 6. LEAN Integration Boundary

LEAN is expected to become the first concrete analysis engine in a follow-up
module, but only behind this seam. The provider module may depend on LEAN, adapt
LEAN inputs/outputs, and emit provider/source metadata. `ATrade.Api`,
`ATrade.Analysis`, market-data contracts, frontend components, and persisted
analysis payloads must remain provider-neutral.

Future LEAN work should therefore:

- consume `AnalysisRequest` and normalized `OhlcvCandle` bars
- translate provider/runtime errors into `AnalysisError` codes and safe states
- emit `AnalysisResult` with accurate engine/source metadata
- avoid introducing real order placement or live-trading behavior
- update this document, `modules.md`, and `paper-trading-workspace.md` when the
  concrete provider lands

## 7. Verification

The contract is verified by:

- `tests/ATrade.Analysis.Tests/` for contract and fallback behavior
- `tests/apphost/analysis-engine-contract-tests.sh` for solution/project/API
  wiring, no-engine HTTP behavior, and absence of LEAN references in API/core
  contracts

The full repository verification suite should include the analysis contract
script alongside the existing provider, apphost, and frontend checks.

## 8. Change Control

Changes that add engine capabilities, alter request/result payloads, introduce a
concrete runtime dependency, or weaken the no-configured-engine behavior must
update this document and the linked active architecture docs in the same change.
