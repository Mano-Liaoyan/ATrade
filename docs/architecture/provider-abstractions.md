---
status: active
owner: maintainer
updated: 2026-04-30
summary: Provider-neutral broker, market-data, and analysis provider contracts for swapping ATrade providers without changing API or frontend payloads.
see_also:
  - ../INDEX.md
  - overview.md
  - modules.md
  - paper-trading-workspace.md
  - analysis-engines.md
  - ../../README.md
  - ../../PLAN.md
---

# Provider Abstractions

ATrade composes broker, market-data, and analysis implementations behind
provider-neutral contracts. The API and frontend must depend on ATrade
contracts and payloads, not on the concrete IBKR Gateway/iBeam runtime,
Polygon, LEAN, or any future provider runtime.

This document is the switching overview for the provider seams introduced in
`TP-019` and extended by the analysis engine contract. The detailed analysis
engine contract lives in `analysis-engines.md`.

## 1. Goals

- Allow broker status providers to change without rewriting API endpoint code.
- Allow market-data providers to change without changing HTTP/SignalR payloads.
- Allow analysis engines to change without changing API/frontend request or result payloads.
- Keep paper-only safety explicit: real order placement is not supported by the
  current contract.
- Keep provider unavailable and not-configured states explicit so runtime,
  credential, or authentication gaps return safe errors instead of silently
  falling back to synthetic data.
- Keep concrete provider implementations replaceable by DI registration while
  preserving provider-neutral HTTP/SignalR payload shapes and source metadata.

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

- `IMarketDataProvider` — provider seam for trending/scanner results, stock
  search, symbol lookup, historical candles, indicators, and latest snapshots.
- `IMarketDataStreamingProvider` — streaming snapshot/group-name seam used by
  the SignalR compatibility layer.
- `MarketDataProviderIdentity` — stable provider id plus display name.
- `MarketDataProviderCapabilities` — flags for trending scanner, historical
  candles, indicators, streaming snapshots, symbol search, and mock-data usage.
- `MarketDataProviderStatus` — provider id, `available` / `not-configured` /
  `unavailable` state, message, observation time, and capabilities.
- `MarketDataSymbolIdentity`, `MarketDataSymbolSearchResult`,
  `MarketDataSymbolSearchResponse`, `OhlcvCandle`, `CandleSeriesResponse`,
  `IndicatorResponse`, `MarketDataUpdate`, and trending response records — the
  payload-safe domain shapes providers must emit. Search identity includes
  `symbol`, `provider`, `providerSymbolId`, `assetClass`, `exchange`, and
  `currency`; for IBKR the provider symbol id is the Client Portal `conid`.
  Other payloads include source metadata such as `ibkr-ibeam-history`,
  `ibkr-ibeam-snapshot`, or scanner source ids.

Compatibility layer:

- `IMarketDataService` remains the HTTP-facing compatibility service used by
  existing endpoints, including `GET /api/market-data/search`.
- `MarketDataService` composes `IMarketDataProvider`, validates stock search
  query length/asset class/result limit, and preserves endpoint payload behavior.
- `IMarketDataStreamingService` remains the SignalR-facing compatibility
  service; `MarketDataStreamingService` composes `IMarketDataStreamingProvider`.
- Production provider composition is now `ATrade.MarketData.Ibkr`; the former
  production market-data mock providers and catalog fallback have been removed.

Unavailable handling:

- Providers report status through `MarketDataProviderStatus`.
- `not-configured` maps to `provider-not-configured`.
- `unavailable` maps to `provider-unavailable`.
- rejected Client Portal requests caused by unauthenticated iBeam sessions may
  surface `authentication-required` while still avoiding fake data.
- Compatibility services return these safe errors for request/response methods
  that already expose `MarketDataError`; provider tasks must not silently fall
  back to synthetic data when iBeam is unavailable.

## 4. Analysis Engine Provider Family

Analysis engine contracts live in `src/ATrade.Analysis`; the first concrete
provider lives in `src/ATrade.Analysis.Lean`. Detailed behavior is documented
in `analysis-engines.md`.

Core rules:

- `IAnalysisEngine` implementations consume `AnalysisRequest`, which contains
  `MarketDataSymbolIdentity` and normalized `OhlcvCandle` bars from
  `ATrade.MarketData`.
- API callers use `GET /api/analysis/engines` and `POST /api/analysis/run`, not
  provider-specific endpoints.
- `AnalysisResult` always carries engine metadata, source metadata, signals,
  metrics, optional backtest summary, and optional error information.
- With no concrete provider configured, the fallback returns the explicit
  `analysis-engine-not-configured` result instead of synthetic signals.
- `ATrade.Analysis.Lean` is selected by `ATRADE_ANALYSIS_ENGINE=Lean`, converts
  ATrade bars into a temporary official-LEAN workspace, invokes the configured
  LEAN CLI/Docker runtime, and maps results back into the provider-neutral
  `AnalysisResult` shape.
- LEAN and future runtimes belong in concrete provider modules; API/core and
  frontend contracts remain provider-neutral.

## 5. Composition Rules

- API endpoint handlers may depend on provider-neutral contracts such as
  `IBrokerProvider`, `IMarketDataService`, `IAnalysisEngineRegistry`, and
  SignalR-facing market-data services.
- API endpoint handlers must not instantiate concrete providers such as the
  IBKR Gateway client or any market-data provider implementation.
- Concrete providers are registered in module composition methods and can be
  swapped by changing DI registration/configuration, not endpoint paths or
  frontend type names. The current API composes `AddMarketDataModule()` plus
  `AddIbkrMarketDataProvider()`, `AddAnalysisModule()`, and
  `AddLeanAnalysisEngine(...)`; LEAN only becomes active when configuration
  selects it.
- Workers may compose concrete provider modules, but worker-to-API state must be
  normalized through provider-neutral status/event shapes before reaching the
  browser.

## 6. Current IBKR Market-Data Provider And Future Plug-ins

Current implementation:

- `ATrade.MarketData.Ibkr` implements `IMarketDataProvider` and
  `IMarketDataStreamingProvider` using the local iBeam/Client Portal Gateway
  base URL and session configuration supplied by `ATrade.Brokers.Ibkr`.
- The shared IBKR gateway transport contract uses HTTPS for the local
  `voyz/ibeam:latest` Client Portal host port (committed default
  `https://127.0.0.1:5000`). AppHost maps the configured host port to iBeam's
  fixed internal Client Portal target port `5000` and mounts a repo-local
  non-secret iBeam inputs `conf.yaml` so Client Portal accepts loopback/private
  Docker bridge source addresses used by Aspire published-port requests; legacy
  loopback HTTP URLs are normalized to HTTPS for local iBeam traffic, shared
  broker/market-data HTTP clients send a stable Client Portal-compatible user
  agent, and self-signed certificate acceptance is scoped to loopback iBeam
  HTTPS only; remote hosts keep normal certificate validation.
- It does not read credential environment variables directly. Credential and
  paper-account presence is evaluated through typed gateway configuration and
  the paper-only guard.
- It translates Client Portal contract search (`/iserver/secdef/search`) plus
  contract detail (`/iserver/secdef/info`), snapshots
  (`/iserver/marketdata/snapshot`), historical bars (`/iserver/marketdata/history`),
  and scanner results (`/iserver/scanner/run`) into provider-neutral ATrade
  payloads.
- Search returns stock results with symbol, display name, asset class, exchange,
  currency, provider id, and provider symbol id/IBKR `conid`; no production
  hard-coded stock allowlist is used.
- Trending uses the scanner source `ibkr-ibeam-scanner:STK.US.MAJOR:TOP_PERC_GAIN`
  rather than a hard-coded symbol catalog.
- Missing local runtime, placeholder credentials, unauthenticated sessions,
  HTTPS transport/certificate failures, unreachable gateway, or rejected live
  mode return `not-configured` / `unavailable` states and
  `provider-not-configured` / `provider-unavailable` /
  `authentication-required` errors rather than fallback data. Diagnostics may
  tell developers to verify local HTTPS iBeam transport and authentication, but
  must not echo gateway URLs, usernames, passwords, account ids, session ids,
  cookies, or tokens.

Future plug-ins:

- The current Next.js workspace uses the market-data search hook for
  pin-any-symbol workflows while persisting provider metadata through
  `ATrade.Workspaces`.
- Polygon or another market-data provider may be added later behind the same
  contracts and source metadata rules.
- LEAN is now the first analysis-engine provider behind `ATrade.Analysis`; it
  consumes normalized market-data/signal contracts and must not become an API or
  UI type assumption. Runtime-unavailable or timeout states surface as explicit
  analysis errors instead of fake results.
- Additional analysis engines can replace or complement LEAN by implementing
  `IAnalysisEngine` in their own provider modules and preserving the same
  request/result contracts.

## 7. Change Control

Changes that add provider capabilities, expose new provider states, or weaken
paper-only guardrails must update this document, `modules.md`, and
`paper-trading-workspace.md` in the same change.
