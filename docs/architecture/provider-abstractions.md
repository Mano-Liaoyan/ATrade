---
status: active
owner: maintainer
updated: 2026-04-29
summary: Provider-neutral broker and market-data contract for swapping ATrade providers without changing API or frontend payloads.
see_also:
  - ../INDEX.md
  - overview.md
  - modules.md
  - paper-trading-workspace.md
  - ../../README.md
  - ../../PLAN.md
---

# Provider Abstractions

ATrade composes broker and market-data implementations behind provider-neutral
contracts. The API and frontend must depend on ATrade contracts and payloads,
not on the concrete IBKR Gateway/iBeam runtime, deterministic mocks, Polygon,
or any future analysis engine.

This document is the authoritative switching contract for the current provider
seams introduced in `TP-019`.

## 1. Goals

- Allow broker status providers to change without rewriting API endpoint code.
- Allow market-data providers to change without changing HTTP/SignalR payloads.
- Keep paper-only safety explicit: real order placement is not supported by the
  current contract.
- Keep provider unavailable and not-configured states explicit so follow-on
  tasks return safe errors instead of silently falling back to fake data.
- Keep deterministic mocked market data only as temporary compatibility until
  the real provider task replaces it.

## 2. Broker Provider Contract

Provider-neutral broker contracts live in `src/ATrade.Brokers`.

Core types:

- `IBrokerProvider` — API-facing broker seam with provider `Identity`,
  `Capabilities`, and `GetStatusAsync`.
- `BrokerProviderIdentity` — stable provider id plus display name.
- `BrokerProviderCapabilities` — flags for session status, read-only market
  data support, broker order placement, credential persistence, execution
  persistence, and official-API usage.
- `BrokerProviderStatus` — provider id, state, account mode, safe connection
  booleans, message, observation time, and capabilities.
- `BrokerAccountModes` and `BrokerProviderStates` — canonical string values for
  payload-safe account modes and status states.

Current implementation:

- `ATrade.Brokers.Ibkr` implements `IBrokerProvider` through the existing
  paper-safe IBKR status service.
- `GET /api/broker/ibkr/status` resolves `IBrokerProvider`, not the concrete
  IBKR status service, and preserves the existing JSON shape.
- `ATrade.Ibkr.Worker` consumes the same provider-neutral status object while
  still composing the concrete IBKR adapter.

Safety constraints:

- `SupportsBrokerOrderPlacement` is `false` in the current paper-safe IBKR
  capability set.
- Live mode is rejected before any broker call.
- Credential persistence and execution persistence remain unsupported until a
  separately reviewed task adds them.
- Provider implementations must not leak gateway URLs, account identifiers,
  secrets, tokens, or session cookies through status payloads.

## 3. Market-Data Provider Contract

Market-data provider contracts live in `src/ATrade.MarketData`.

Core types:

- `IMarketDataProvider` — provider seam for trending/scanner results, symbol
  lookup, symbol-search readiness, historical candles, indicators, and latest
  snapshots.
- `IMarketDataStreamingProvider` — streaming snapshot/group-name seam used by
  the SignalR compatibility layer.
- `MarketDataProviderIdentity` — stable provider id plus display name.
- `MarketDataProviderCapabilities` — flags for trending scanner, historical
  candles, indicators, streaming snapshots, symbol search, and mock-data usage.
- `MarketDataProviderStatus` — provider id, `available` / `not-configured` /
  `unavailable` state, message, observation time, and capabilities.
- `MarketDataSymbolIdentity`, `OhlcvCandle`, `CandleSeriesResponse`,
  `IndicatorResponse`, `MarketDataUpdate`, and trending response records — the
  payload-safe domain shapes providers must emit.

Compatibility layer:

- `IMarketDataService` remains the HTTP-facing compatibility service used by
  existing endpoints.
- `MarketDataService` composes `IMarketDataProvider` and preserves current
  endpoint payload behavior.
- `IMarketDataStreamingService` remains the SignalR-facing compatibility
  service; `MarketDataStreamingService` composes `IMarketDataStreamingProvider`.
- `MockMarketDataService` and `MockMarketDataStreamingService` are temporary
  provider implementations only. They keep the current deterministic MVP
  behavior until the real IBKR/iBeam provider work lands.

Unavailable handling:

- Providers report status through `MarketDataProviderStatus`.
- `not-configured` maps to `provider-not-configured`.
- `unavailable` maps to `provider-unavailable`.
- Compatibility services return these safe errors for request/response methods
  that already expose `MarketDataError`; provider tasks must not silently fall
  back to mock data when a real provider is missing.

## 4. Composition Rules

- API endpoint handlers may depend on provider-neutral contracts such as
  `IBrokerProvider`, `IMarketDataService`, and SignalR-facing market-data
  services.
- API endpoint handlers must not instantiate concrete providers such as the
  IBKR Gateway client or mocked market-data services.
- Concrete providers are registered in module composition methods and can be
  swapped by changing DI registration, not endpoint code.
- Workers may compose concrete provider modules, but worker-to-API state must be
  normalized through provider-neutral status/event shapes before reaching the
  browser.

## 5. Future Provider Plug-ins

- `TP-021` may add local iBeam/Gateway runtime wiring, but it must remain a
  concrete provider implementation detail behind the broker/market-data seams.
- `TP-022` may replace the temporary mocked market-data provider with an
  IBKR/iBeam provider. If local runtime or credentials are missing, it must use
  `not-configured` or `unavailable` instead of falling back to mocked data.
- `TP-023` may use the market-data symbol-search hook for pin-any-symbol
  workflows.
- LEAN remains a future analysis-engine provider seam; it must consume
  normalized market-data/signal contracts rather than becoming an API or UI
  assumption.

## 6. Change Control

Changes that add provider capabilities, expose new provider states, or weaken
paper-only guardrails must update this document, `modules.md`, and
`paper-trading-workspace.md` in the same change.
