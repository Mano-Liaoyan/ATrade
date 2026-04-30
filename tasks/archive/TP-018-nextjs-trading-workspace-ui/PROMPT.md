# Task: TP-018 - Build TradingView-like Next.js market workspace and watchlist

**Created:** 2026-04-29
**Size:** L

## Review Level: 2 (Plan and Code)

**Assessment:** This adds the first substantial frontend feature slice, new frontend dependencies, API/SignalR client code, local preference persistence, and docs/tests. It is UI-heavy and novel for the repo, but does not touch backend auth, secrets, trading execution, or database schema.
**Score:** 4/8 — Blast radius: 1, Pattern novelty: 2, Security: 0, Reversibility: 1

## Canonical Task Folder

```text
tasks/TP-018-nextjs-trading-workspace-ui/
├── PROMPT.md   ← This file (immutable above --- divider)
├── STATUS.md   ← Execution state (worker updates this)
├── .reviews/   ← Reviewer output (created by the orchestrator runtime)
└── .DONE       ← Created when complete
```

## Mission

Build the Next.js frontend slice for the paper-trading workspace. Users should see a list of trending stocks and ETFs, click a symbol to open an interactive TradingView-like chart, switch timeframes, view simple indicators, and pin/favorite symbols into a local watchlist. The UI should consume the mocked backend market-data APIs and SignalR stream from TP-017, surface IBKR paper-mode status from TP-016 where useful, and persist user preferences through browser local storage for the MVP.

## Dependencies

- **Task:** TP-016 (safe IBKR paper Gateway backend/status and order simulation guard must exist first)
- **Task:** TP-017 (mocked market-data HTTP endpoints and SignalR hub must exist first)

## Context to Read First

> Only load these files unless implementation reveals a directly related missing prerequisite.

**Tier 2 (area context):**
- `tasks/CONTEXT.md`

**Tier 3 (load only if needed):**
- `docs/architecture/paper-trading-workspace.md` — UI/data-flow, charting, SignalR, and preference-storage contract
- `docs/architecture/modules.md` — frontend and API module boundaries
- `scripts/README.md` — frontend/AppHost startup contract and environment rules
- `.env.template` — frontend API base URL placeholder from TP-015
- `frontend/package.json` — current frontend scripts and dependency baseline
- `frontend/package-lock.json` — npm lockfile to update when dependencies are added
- `frontend/app/page.tsx` — current home page slice
- `frontend/app/layout.tsx` — current app layout
- `frontend/app/globals.css` — current global styling
- `tests/apphost/frontend-nextjs-bootstrap-tests.sh` — frontend smoke-test pattern
- `tests/apphost/market-data-feature-tests.sh` — backend API contract from TP-017
- `tests/apphost/ibkr-paper-safety-tests.sh` — broker status/simulation contract from TP-016

## Environment

- **Workspace:** `frontend/` plus project-root tests/docs
- **Services required:** Direct frontend tests may start the Next.js dev server. Integration smoke tests may start `ATrade.Api` locally. No IBKR Gateway, real market-data provider, LEAN runtime, database, Redis, NATS, or real broker credentials may be required.

## File Scope

> This task depends on TP-016 and TP-017 because it consumes their backend contracts.

- `frontend/package.json`
- `frontend/package-lock.json`
- `frontend/app/*`
- `frontend/components/*` (new)
- `frontend/lib/*` (new)
- `frontend/types/*` (new if useful)
- `frontend/next.config.ts` (only if environment/runtime config requires it)
- `.env.template` (only if frontend-safe public variables need adjustment)
- `tests/apphost/frontend-trading-workspace-tests.sh` (new)
- `tests/apphost/frontend-nextjs-bootstrap-tests.sh` (only if shared frontend smoke markers change)
- `docs/architecture/paper-trading-workspace.md`
- `docs/architecture/modules.md`
- `scripts/README.md`
- `README.md`

## Steps

> **Hydration:** STATUS.md tracks outcomes, not individual code changes. Workers expand steps when runtime discoveries warrant it.

### Step 0: Preflight

- [ ] Required files and paths exist
- [ ] Dependencies satisfied
- [ ] Confirm TP-016 broker status/simulation endpoints exist before consuming them
- [ ] Confirm TP-017 market-data HTTP endpoints and SignalR hub exist before consuming them
- [ ] Confirm the frontend still builds or document pre-existing failure before changes

### Step 1: Add frontend data clients and charting dependencies

- [ ] Add `lightweight-charts` for the chart MVP and `@microsoft/signalr` for streaming client support; update `frontend/package-lock.json`
- [ ] Add typed frontend models and API client helpers for trending symbols, candles, indicators, broker status, and optional SignalR updates
- [ ] Read frontend-safe API base URL from `NEXT_PUBLIC_ATRADE_API_BASE_URL` or the TP-015 equivalent, with a safe local default for development
- [ ] Do not add the proprietary TradingView Charting Library or any package requiring unapproved licensing
- [ ] Run targeted frontend install/build check: `cd frontend && npm install && npm run build`

**Artifacts:**
- `frontend/package.json` (modified)
- `frontend/package-lock.json` (modified)
- `frontend/lib/marketDataClient.ts` (new or equivalent)
- `frontend/lib/marketDataStream.ts` (new or equivalent)
- `frontend/lib/brokerStatusClient.ts` (new or equivalent)
- `frontend/types/marketData.ts` (new or equivalent)

### Step 2: Build the trending list, symbol navigation, and watchlist UX

- [ ] Replace or extend the home page with a trading workspace landing view that shows trending stocks and ETFs from the backend
- [ ] Let users click a trending symbol to open a dedicated chart view or symbol-specific panel
- [ ] Implement pin/favorite behavior and a personal watchlist using browser local storage for the MVP
- [ ] Provide empty/loading/error states that make backend unavailability clear without pretending live data exists
- [ ] Preserve stable visible markers needed by existing frontend smoke tests or update those tests intentionally
- [ ] Run targeted frontend build: `cd frontend && npm run build`

**Artifacts:**
- `frontend/app/page.tsx` (modified)
- `frontend/app/symbols/[symbol]/page.tsx` (new or equivalent)
- `frontend/components/TrendingList.tsx` (new or equivalent)
- `frontend/components/Watchlist.tsx` (new or equivalent)
- `frontend/lib/watchlistStorage.ts` (new or equivalent)
- `frontend/app/globals.css` (modified)

### Step 3: Build the interactive candlestick chart view

- [ ] Render OHLC candlestick charts with `lightweight-charts`
- [ ] Add timeframe switching for at least `1m`, `5m`, `1h`, and `1D`
- [ ] Add simple indicator support for moving averages, RSI, and MACD using backend payloads or deterministic frontend calculations documented in code
- [ ] Enable or preserve chart zooming, panning, crosshair, and tooltip/legend behavior supported by the chart library
- [ ] Connect to the SignalR market-data stream where available and fall back to HTTP refresh/polling if the stream is unavailable
- [ ] Avoid any UI that submits real broker orders; if showing order simulation, label it unambiguously as simulation and call only the TP-016 simulation endpoint
- [ ] Run targeted frontend build: `cd frontend && npm run build`

**Artifacts:**
- `frontend/components/CandlestickChart.tsx` (new or equivalent)
- `frontend/components/TimeframeSelector.tsx` (new or equivalent)
- `frontend/components/IndicatorPanel.tsx` (new or equivalent)
- `frontend/components/SymbolChartView.tsx` (new or equivalent)
- `frontend/components/BrokerPaperStatus.tsx` (new or equivalent)
- `frontend/app/symbols/[symbol]/page.tsx` (modified)

### Step 4: Add frontend trading-workspace verification

- [ ] Create `tests/apphost/frontend-trading-workspace-tests.sh`
- [ ] Verify frontend dependencies include `lightweight-charts` and `@microsoft/signalr`
- [ ] Verify source contains local-storage watchlist persistence and no proprietary TradingView Charting Library dependency
- [ ] Run `cd frontend && npm run build`
- [ ] Start the API and frontend when feasible, then assert stable page markers for trending list, chart workspace, timeframe controls, and watchlist UI
- [ ] Verify existing frontend bootstrap smoke test still passes or update it intentionally for new markers
- [ ] Run targeted test: `bash tests/apphost/frontend-trading-workspace-tests.sh`

**Artifacts:**
- `tests/apphost/frontend-trading-workspace-tests.sh` (new)
- `tests/apphost/frontend-nextjs-bootstrap-tests.sh` (modified only if existing markers change)

### Step 5: Update docs for the frontend workspace

- [ ] Update `docs/architecture/paper-trading-workspace.md` with implemented frontend routes/components, chart library usage, watchlist persistence, SignalR fallback behavior, and simulation/no-real-trades UI guardrails
- [ ] Update `docs/architecture/modules.md` so the Next.js current-state note describes the trading workspace slice without overstating real market data, live broker trading, or backend DB preferences
- [ ] Update `scripts/README.md` if frontend environment variables, direct startup verification, or AppHost-managed frontend behavior changed
- [ ] Update `README.md` only if current-status wording would otherwise be stale

**Artifacts:**
- `docs/architecture/paper-trading-workspace.md` (modified)
- `docs/architecture/modules.md` (modified)
- `scripts/README.md` (modified if affected)
- `README.md` (modified if affected)

### Step 6: Testing & Verification

> ZERO test failures allowed. This step runs the full available repository verification suite as the quality gate.

- [ ] Run FULL test suite: `dotnet build ATrade.sln --nologo --verbosity minimal && bash tests/start-contract/start-wrapper-tests.sh && bash tests/scaffolding/project-shells-tests.sh && bash tests/apphost/api-bootstrap-tests.sh && bash tests/apphost/accounts-feature-bootstrap-tests.sh && bash tests/apphost/ibkr-paper-safety-tests.sh && bash tests/apphost/market-data-feature-tests.sh && bash tests/apphost/frontend-nextjs-bootstrap-tests.sh && bash tests/apphost/frontend-trading-workspace-tests.sh && bash tests/apphost/apphost-infrastructure-manifest-tests.sh && bash tests/apphost/apphost-worker-resource-wiring-tests.sh && bash tests/apphost/local-port-contract-tests.sh && bash tests/apphost/paper-trading-config-contract-tests.sh && bash tests/apphost/apphost-infrastructure-runtime-tests.sh`
- [ ] Confirm `apphost-infrastructure-runtime-tests.sh` passes or cleanly skips when no Docker-compatible engine is available
- [ ] Fix all failures
- [ ] Frontend build passes: `cd frontend && npm run build`
- [ ] Solution build passes: `dotnet build ATrade.sln --nologo --verbosity minimal`

### Step 7: Documentation & Delivery

- [ ] "Must Update" docs modified
- [ ] "Check If Affected" docs reviewed
- [ ] Discoveries logged in STATUS.md

## Documentation Requirements

**Must Update:**
- `docs/architecture/paper-trading-workspace.md` — record implemented frontend chart/watchlist behavior, persistence model, and streaming fallback
- `docs/architecture/modules.md` — update Next.js frontend current-state note

**Check If Affected:**
- `scripts/README.md` — update if frontend environment/startup verification changes
- `README.md` — update if current-status wording becomes stale
- `docs/INDEX.md` — update only if new indexed docs are added (none expected)
- `.env.template` — update only if frontend-safe public variable names change

## Completion Criteria

- [ ] Next.js UI shows trending stocks and ETFs from the backend and supports symbol navigation
- [ ] Users can pin/favorite symbols and maintain a watchlist persisted in local storage
- [ ] Chart view renders OHLC candlesticks, timeframe switching, simple indicators, zoom/pan/crosshair, and tooltip/legend behavior
- [ ] UI consumes backend HTTP data and uses SignalR updates where available with a safe fallback
- [ ] No UI path places or implies real trades; any simulation is clearly labeled and calls only the simulation endpoint
- [ ] Frontend build and trading-workspace smoke tests pass
- [ ] Active docs accurately describe frontend behavior and remaining limitations

## Git Commit Convention

Commits happen at **step boundaries** (not after every checkbox). All commits for this task MUST include the task ID for traceability:

- **Step completion:** `feat(TP-018): complete Step N — description`
- **Bug fixes:** `fix(TP-018): description`
- **Tests:** `test(TP-018): description`
- **Hydration:** `hydrate: TP-018 expand Step N checkboxes`

## Do NOT

- Use the proprietary TradingView Charting Library without explicit licensing approval
- Add real broker order placement, live-trading UI, or ambiguous buy/sell actions that could be mistaken for real execution
- Store secrets, broker account identifiers, or tokens in local storage or committed frontend files
- Require IBKR Gateway, Polygon, LEAN, databases, Redis, NATS, or real credentials for frontend tests
- Break existing AppHost-managed frontend startup, direct frontend startup, or stable smoke-test markers without updating tests and docs
- Load docs not listed in "Context to Read First" unless a missing prerequisite is discovered and recorded

---

## Amendments (Added During Execution)

<!-- Workers add amendments here if issues discovered during execution.
     Format:
     ### Amendment N — YYYY-MM-DD HH:MM
     **Issue:** [what was wrong]
     **Resolution:** [what was changed] -->
