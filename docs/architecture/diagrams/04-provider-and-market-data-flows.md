---
status: active
owner: maintainer
updated: 2026-05-17
summary: Mermaid provider-neutral broker, account-capital, market-data, Timescale cache-aside, Exact Instrument Identity, and watchlist flows.
see_also:
  - ../provider-abstractions.md
  - ../modules.md
  - ../paper-trading-workspace.md
  - ../backtesting.md
  - ../../INDEX.md
  - ../../../README.md
  - ../../../PLAN.md
---

# Provider And Market-Data Flows

ATrade keeps broker status, account capital, market data, and workspace
watchlists behind provider-neutral contracts. IBKR/iBeam is the first concrete
broker and market-data provider, but the browser sees ATrade payloads and safe
provider states instead of gateway details.

```mermaid
flowchart TD
  UI["Next.js terminal workspace"] -->|"status, capital, search, chart, pins"| API["ATrade.Api"]

  subgraph BrokerCapital["Broker and paper-capital seam"]
    API --> BrokerContract["IBrokerProvider<br/>ATrade.Brokers"]
    API --> CapitalService["IPaperCapitalService<br/>ATrade.Accounts"]
    BrokerContract --> IbkrBroker["ATrade.Brokers.Ibkr<br/>paper status adapter"]
    CapitalService --> LocalCapital[("Postgres<br/>local paper ledger")]
    CapitalService --> IbkrCapital["IIbkrPaperCapitalProvider<br/>safe paper balance read"]
    IbkrCapital --> IbkrBroker
    IbkrBroker -. readiness and authenticated paper balance .-> Ibeam["local iBeam runtime<br/>Client Portal"]
  end

  subgraph MarketData["Market-data read seam"]
    API --> MarketService["IMarketDataService<br/>ATrade.MarketData"]
    MarketService --> ExactIdentity["ExactInstrumentIdentity<br/>provider tuple normalization"]
    MarketService --> CacheAside["ATrade.MarketData.Timescale<br/>freshness-aware decorator"]
    CacheAside --> FreshCheck{"Fresh compatible row?"}
    FreshCheck -->|yes| CacheHit["Return ATrade payload<br/>source timescale-cache"]
    FreshCheck -->|no| IbkrMarket["ATrade.MarketData.Ibkr<br/>IBKR search, scanner, snapshots, bars"]
    IbkrMarket --> IbkrBroker
    IbkrMarket -. provider calls .-> Ibeam
    IbkrMarket --> ProviderPayload["Provider-neutral<br/>search, trending, candles, indicators"]
    ProviderPayload --> PersistTimescale[("TimescaleDB<br/>provider metadata and OHLCV")]
    PersistTimescale --> CacheAside
    CacheAside --> APIPayload["API response with sourceStatus<br/>fresh, stale, or safe error"]
    CacheHit --> APIPayload
  end

  subgraph Watchlists["Workspace watchlist seam"]
    API --> WatchlistIntake["IWorkspaceWatchlistIntake<br/>ATrade.Workspaces"]
    WatchlistIntake --> ExactIdentity
    WatchlistIntake --> WatchlistStore[("Postgres<br/>exact instrument pins")]
    WatchlistStore --> WatchlistPayload["instrumentKey and pinKey<br/>backend authoritative"]
  end

  APIPayload --> UI
  WatchlistPayload --> UI
  BrokerContract --> UI
  CapitalService --> UI

  classDef contract fill:#eef6ff,stroke:#316b9f,color:#102033
  classDef storage fill:#f2f2f2,stroke:#666,color:#111
  classDef provider fill:#fff7e6,stroke:#a86800,color:#2b1b00
  classDef external fill:#f6eefc,stroke:#7a4b9f,color:#201020

  class API,MarketService,ExactIdentity,CacheAside,WatchlistIntake,BrokerContract,CapitalService contract
  class LocalCapital,PersistTimescale,WatchlistStore storage
  class IbkrBroker,IbkrCapital,IbkrMarket,ProviderPayload,APIPayload,WatchlistPayload,CacheHit provider
  class Ibeam external
```

```mermaid
classDiagram
  class ExactInstrumentIdentity {
    provider
    providerSymbolId
    symbol
    exchange
    currency
    assetClass
  }

  class MarketDataSymbolIdentity {
    provider
    providerSymbolId
    symbol
    name
    exchange
    currency
    assetClass
  }

  class WatchlistPin {
    instrumentKey
    pinKey
    displayName
    sortOrder
  }

  class BacktestRequestSnapshot {
    provider
    providerSymbolId
    symbol
    exchange
    currency
    assetClass
    chartRange
  }

  ExactInstrumentIdentity --> MarketDataSymbolIdentity : normalizes
  ExactInstrumentIdentity --> WatchlistPin : derives keys
  ExactInstrumentIdentity --> BacktestRequestSnapshot : saved identity
```

## How To Read It

- The browser calls `ATrade.Api`; it never connects directly to iBeam,
  Postgres, TimescaleDB, Redis, NATS, LEAN, or provider runtimes.
- Exact Instrument Identity is the provider-neutral tuple:
  `provider`, `providerSymbolId`, `symbol`, `exchange`, `currency`, and
  `assetClass`.
- IBKR `conid` is provider metadata and an alias for the IBKR provider symbol id.
  New canonical `instrumentKey` and `pinKey` values do not add a separate
  `ibkrConid` identity segment.
- Timescale cache-aside can return fresh persisted provider rows, including
  after a local AppHost restart when the cache remains inside the freshness
  window. Stale rows are labeled stale only after a safe refresh attempt fails;
  they are not promoted to fresh success.
- Watchlist pins are backend-owned Postgres preferences. Browser local storage
  is only a non-authoritative symbol cache or migration aid.
- Provider gaps surface as safe states such as provider-not-configured,
  provider-unavailable, authentication-required, rate-limited, or storage
  unavailable. They do not trigger fake production symbols, candles, or capital.

## Current Concrete Provider

The current concrete provider family is IBKR through the local iBeam Client
Portal runtime. `ATrade.Brokers.Ibkr` owns paper-only readiness and safe broker
status projection. `ATrade.MarketData.Ibkr` owns stock search, scanner/trending,
snapshots, historical bars, and source metadata. Both consume the same normalized
readiness result so broker status, paper-capital availability, worker monitoring,
and market-data reads agree on disabled, credentials-missing, connecting,
authenticated, degraded, unavailable, and rejected-live states.
