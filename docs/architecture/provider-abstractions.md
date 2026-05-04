---
status: active
owner: maintainer
updated: 2026-05-02
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

- `ATrade.Brokers.Ibkr` implements `IBrokerProvider` by evaluating a shared
  IBKR/iBeam readiness result and projecting it into the paper-safe broker
  status contract.
- `GET /api/broker/ibkr/status` resolves `IBrokerProvider`, not the concrete
  IBKR status service, and preserves the existing JSON shape.
- `ATrade.Ibkr.Worker` consumes the same shared IBKR/iBeam readiness module for
  monitoring while API broker status projects that readiness into the
  provider-neutral status object.

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

- `IMarketDataProvider` — async provider seam for trending/scanner results,
  stock search, symbol lookup, historical candles, indicators, and latest
  snapshots. Read methods accept cancellation tokens and return
  `MarketDataReadResult<T>` so provider errors stay in the same payload-safe
  shape instead of forcing callers to inspect status first or catch unavailable
  exceptions.
- `IMarketDataStreamingProvider` — async streaming snapshot/group-name seam used
  by the SignalR compatibility layer.
- `MarketDataProviderIdentity` — stable provider id plus display name.
- `MarketDataProviderCapabilities` — flags for trending scanner, historical
  candles, indicators, streaming snapshots, symbol search, and mock-data usage.
- `MarketDataProviderStatus` — provider id, `available` / `not-configured` /
  `unavailable` state, message, observation time, and capabilities.
- `ChartRangePresets`, `ExactInstrumentIdentity`, `MarketDataSymbolIdentity`,
  `MarketDataSymbolSearchResult`, `MarketDataSymbolSearchResponse`,
  `OhlcvCandle`, `CandleSeriesResponse`, `IndicatorResponse`,
  `MarketDataUpdate`, and trending response records — the payload-safe domain
  shapes providers must emit. `ChartRangePresets` defines the supported chart
  lookback ranges from now: `1min`, `5mins`, `1h`, `6h`, `1D`, `1m`, `6m`,
  `1y`, `5y`, and `all` / All time. The legacy model property and method name
  `timeframe` remains a compatibility alias in payloads and API methods, but the
  value is normalized as a chart range; `1m` means one month and one-minute reads
  use `1min`. `ExactInstrumentIdentity` is the backend-owned
  normalization/key/equality helper for provider, provider symbol id, symbol,
  exchange, currency, and asset class; for IBKR the provider symbol id is the
  Client Portal `conid`. Search results, trending symbols, candle series,
  indicators, and latest updates carry `MarketDataSymbolIdentity` where provider
  metadata is available while preserving the existing symbol/source fields for
  callers that only know a bare symbol. Downstream watchlist pins must treat this
  provider/market tuple as the exact instrument identity rather than collapsing
  results to a bare symbol or display name; `ATrade.Workspaces` delegates key
  construction to the backend identity helper and exposes the normalized tuple as
  `instrumentKey` and `pinKey` when a result is persisted. Other payloads include
  source metadata such as `ibkr-ibeam-history`, `ibkr-ibeam-snapshot`, scanner
  source ids, or `timescale-cache:{originalSource}` when a fresh persisted
  Timescale row serves the API response, including after a full AppHost restart
  when the row remains inside the configured freshness window on the
  volume-backed TimescaleDB data directory. The Timescale persistence layer
  stores provider metadata generically as `provider`, `provider_symbol_id`,
  symbol, exchange, currency, asset class, source, and timestamps, and exact
  read filters can use that metadata without changing the legacy
  `/api/market-data/{symbol}/...` paths; it must not persist frontend-only or
  IBKR-only API types.

Compatibility layer:

- `IMarketDataService` is the async HTTP-facing read seam used by market-data
  endpoints, SignalR-adjacent callers, and `ATrade.Analysis` request intake.
  Trending, search, symbol lookup, candle, indicator, and latest-update reads all
  return `MarketDataReadResult<T>` with the same `MarketDataError` codes the
  browser already understands.
- `MarketDataService` composes `IMarketDataProvider`, validates stock search
  query length/asset class/result limit before provider calls, normalizes chart
  range values before candle/indicator/latest reads, forwards optional exact
  identity metadata, and preserves endpoint payload/status behavior for callers
  that only supply a symbol. HTTP callers should send `range` / `chartRange`;
  legacy `timeframe` query parameters are still accepted as aliases.
- `IMarketDataStreamingService` remains the SignalR-facing compatibility
  service; `MarketDataStreamingService` composes `IMarketDataStreamingProvider`
  asynchronously and owns provider-status checks so hubs do not duplicate that
  logic.
- Production provider composition is now `ATrade.MarketData.Ibkr`; the former
  production market-data mock providers and catalog fallback have been removed.
- `ATrade.MarketData.Timescale` is a storage/cache-aside module, not a market-data
  provider. In `ATrade.Api` it wraps the concrete provider-backed
  `MarketDataService` behind `IMarketDataService`, awaits fresh Timescale rows
  before provider calls for trending/candle/indicator inputs, keys candle rows by
  normalized chart range, rejects stale or cadence-incompatible legacy range rows,
  persists provider responses after cache misses, and preserves provider-neutral
  endpoint payloads.
  AppHost supplies `ConnectionStrings:timescaledb` from a volume-backed
  `timescaledb` resource so fresh persisted rows can survive full local AppHost
  reboots without changing API/frontend payloads.

Unavailable handling:

- Providers report status through `MarketDataProviderStatus`.
- `not-configured` maps to `provider-not-configured`.
- `unavailable` maps to `provider-unavailable`.
- rejected Client Portal requests caused by unauthenticated iBeam sessions may
  surface `authentication-required` while still avoiding fake data.
- Async read services return these safe errors through `MarketDataReadResult<T>`;
  provider tasks must not silently fall back to synthetic data when iBeam is
  unavailable.
- Timescale cache-aside is allowed to return a fresh persisted response while the
  provider is unavailable, including after an AppHost reboot, because the payload
  is still within the configured freshness window, uses the requested normalized
  chart range, satisfies that range's lookback semantics, and its source is
  labeled as cache-backed. Stale, mismatched-range, or missing rows must not be
  presented as successful fresh data when provider refresh fails.

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
  `IBrokerProvider`, `IMarketDataService`, `IAnalysisEngineRegistry`,
  `IAnalysisRequestIntake`, `IWorkspaceWatchlistIntake`, and SignalR-facing
  market-data services.
- API endpoint handlers must not instantiate concrete providers such as the
  IBKR Gateway client or any market-data provider implementation.
- Concrete providers are registered in module composition methods and can be
  swapped by changing DI registration/configuration, not endpoint paths or
  frontend type names. The current API composes `AddMarketDataModule()`,
  `AddTimescaleMarketDataPersistence(builder.Configuration)`,
  `AddIbkrMarketDataProvider()`, `AddTimescaleMarketDataCacheAside()`,
  `AddAnalysisModule()`, and `AddLeanAnalysisEngine(...)`; LEAN only becomes
  active when configuration selects it. Endpoint handlers still depend only on
  provider-neutral services while the Timescale decorator owns cache-aside reads,
  writes, freshness checks, and storage-unavailable fallback, `ATrade.Analysis`
  intake owns analysis request construction/engine handoff, and
  `ATrade.Workspaces` intake owns watchlist request normalization/storage error
  shaping.
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
  the paper-only guard. Broker status, market-data status/read guards, and
  worker monitoring consume the same normalized IBKR/iBeam readiness result so
  disabled, credentials-missing, not-configured, transport timeout/unreachable,
  unauthenticated, authenticated, degraded, error, and rejected-live outcomes
  stay consistent across provider projections.
- It translates Client Portal contract search (`/iserver/secdef/search`) plus
  contract detail (`/iserver/secdef/info`) when available, snapshots
  (`/iserver/marketdata/snapshot`), historical bars (`/iserver/marketdata/history`),
  and scanner results (`/iserver/scanner/run`) into provider-neutral ATrade
  payloads. IBKR symbol text is canonicalized into the `ExactInstrumentIdentity`
  safe symbol alphabet before search, snapshot, scanner, and watchlist payloads
  are created, so provider variants such as class separators with spaces are
  projected as stable legacy path-safe codes (for example, `BRK B` to `BRK.B`)
  while retaining provider symbol id/IBKR `conid` as the exact identity. If
  Client Portal returns the stock detail endpoint's derivative-oriented `month
  required` validation error, search falls back to the search contract payload
  instead of failing the provider request.
- Search returns stock results with symbol, display name, asset class, exchange,
  currency, provider id, and provider symbol id/IBKR `conid`; no production
  hard-coded stock allowlist is used. Search UIs and watchlist persistence must
  preserve enough provider/market identity to distinguish same-symbol or
  same-name results from different exchanges.
- Trending uses the scanner source `ibkr-ibeam-scanner:STK.US.MAJOR:TOP_PERC_GAIN`
  rather than a hard-coded symbol catalog. The scanner call must be a buffered
  `POST /v1/api/iserver/scanner/run` JSON request with `Content-Type:
  application/json`, the top-percent-gainer stock payload (`instrument=STK`,
  `location=STK.US.MAJOR`, `type=TOP_PERC_GAIN`, empty `filter`), an explicit
  positive `Content-Length`, and no chunked transfer; Client Portal/iBeam edge
  handling may reject streaming or missing-length scanner bodies with `411
  Length Required`.
- Missing local runtime, placeholder credentials, unauthenticated sessions,
  HTTPS transport/certificate failures, unreachable gateway, or rejected live
  mode return `not-configured` / `unavailable` states and
  `provider-not-configured` / `provider-unavailable` /
  `authentication-required` errors rather than fallback data. Diagnostics may
  tell developers to verify local HTTPS iBeam transport and authentication, but
  must not echo gateway URLs, usernames, passwords, account ids, session ids,
  cookies, or tokens.

Future plug-ins:

- The current Next.js workspace uses a frontend symbol-search workflow over the
  `ATrade.Api` market-data search endpoint for pin-any-symbol workflows while
  persisting exact provider/market instrument metadata through
  `ATrade.Workspaces`; browser cache state remains a legacy symbol-only
  migration/read-only fallback and is not an identity authority.
- Polygon or another market-data provider may be added later behind the same
  contracts and source metadata rules, reusing the Timescale storage fields for
  provider/source/symbol identity instead of introducing provider-specific
  persistence columns.
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
