# Task: TP-031 - Fix watchlist persistence and market-specific search pins

**Created:** 2026-04-30
**Size:** L

## Review Level: 2 (Plan and Code)

**Assessment:** This fixes durable watchlist behavior and changes watchlist identity from symbol-only to provider/market-specific instrument identity across Postgres, API, frontend state, and tests. It includes a data-model migration and user-facing search UI changes, but does not touch authentication, broker credentials, or order placement.
**Score:** 5/8 — Blast radius: 2, Pattern novelty: 1, Security: 0, Reversibility: 2

## Canonical Task Folder

```text
tasks/TP-031-watchlist-persistence-market-specific-pins/
├── PROMPT.md   ← This file (immutable above --- divider)
├── STATUS.md   ← Execution state (worker updates this)
├── .reviews/   ← Reviewer output (created by the orchestrator runtime)
└── .DONE       ← Created when complete
```

## Mission

Fix the watchlist issue where pinned favorite stocks disappear after service restart, and make search-result pinning exact to the selected market/instrument. Search can return many results with the same symbol or company name from different markets; the UI must explicitly show which market/exchange provides each result with a relevant local logo/badge, and pinning one result must not mark or persist every result with the same symbol/name as pinned.

## Dependencies

- **None**

## Context to Read First

> Only load these files unless implementation reveals a directly related missing prerequisite. Do **not** read, print, or commit the ignored repo-root `.env` file.

**Tier 2 (area context):**
- `tasks/CONTEXT.md`

**Tier 3 (load only if needed):**
- `docs/architecture/paper-trading-workspace.md` — backend-owned watchlists and search-result metadata contract
- `docs/architecture/modules.md` — Workspaces/API/frontend module ownership
- `docs/architecture/provider-abstractions.md` — provider-neutral symbol identity and search metadata
- `src/ATrade.Workspaces/PostgresWorkspaceWatchlistSql.cs` — current watchlist schema and uniqueness rules
- `src/ATrade.Workspaces/PostgresWorkspaceWatchlistRepository.cs` — pin/unpin persistence behavior
- `src/ATrade.Workspaces/WorkspaceWatchlistModels.cs` — API/domain response shapes
- `src/ATrade.Workspaces/WorkspaceWatchlistNormalizer.cs` and `WorkspaceSymbolNormalizer.cs` — identity normalization
- `src/ATrade.Api/Program.cs` — watchlist endpoint handlers and error mapping
- `frontend/components/TradingWorkspace.tsx` — current pin-state and migration flow
- `frontend/components/SymbolSearch.tsx` — search result rendering and pin buttons
- `frontend/components/Watchlist.tsx` — saved pin rendering/removal
- `frontend/components/TrendingList.tsx` — trending pin behavior that must keep working
- `frontend/lib/watchlistClient.ts` and `frontend/lib/watchlistStorage.ts` — frontend watchlist API/cache helpers
- `frontend/types/marketData.ts` — search result identity shape
- `frontend/app/globals.css` — local badge/logo styling if needed
- `tests/ATrade.Workspaces.Tests/*` — Workspaces test patterns
- `tests/apphost/postgres-watchlist-persistence-tests.sh` — restart persistence verification
- `tests/apphost/ibkr-symbol-search-tests.sh` — search workflow verification
- `tests/apphost/frontend-trading-workspace-tests.sh` — frontend source/build/runtime checks

## Environment

- **Workspace:** Repository root plus `frontend/`
- **Services required:** Automated backend/frontend tests must not require real IBKR credentials. Postgres persistence integration may start a disposable database/AppHost-managed Postgres and must cleanly skip with a clear message when no Docker/Podman-compatible runtime is available.

## File Scope

> The orchestrator uses this to avoid merge conflicts. Keep changes inside this scope unless `STATUS.md` records a discovered prerequisite.

- `src/ATrade.Workspaces/*`
- `src/ATrade.Api/Program.cs`
- `frontend/components/MarketLogo.tsx` (new, or equivalent local market/exchange logo component)
- `frontend/components/SymbolSearch.tsx`
- `frontend/components/TradingWorkspace.tsx`
- `frontend/components/Watchlist.tsx`
- `frontend/components/TrendingList.tsx`
- `frontend/lib/watchlistClient.ts`
- `frontend/lib/watchlistStorage.ts`
- `frontend/types/marketData.ts`
- `frontend/app/globals.css`
- `tests/ATrade.Workspaces.Tests/WorkspaceWatchlistInstrumentKeyTests.cs` (new, or equivalent new focused test file)
- `tests/ATrade.Workspaces.Tests/*`
- `tests/apphost/postgres-watchlist-persistence-tests.sh`
- `tests/apphost/ibkr-symbol-search-tests.sh`
- `tests/apphost/frontend-trading-workspace-tests.sh`
- `docs/architecture/paper-trading-workspace.md`
- `docs/architecture/modules.md`
- `docs/architecture/provider-abstractions.md`
- `README.md` (only if current runtime wording changes)
- `tasks/TP-031-watchlist-persistence-market-specific-pins/STATUS.md`

## Steps

> **Hydration:** STATUS.md tracks outcomes, not individual code changes. Workers expand steps when runtime discoveries warrant it.

### Step 0: Diagnose current restart and symbol-only pin behavior

- [ ] Reproduce or inspect the service-restart persistence path: pin a symbol through the backend watchlist API, restart the API/service while keeping the same Postgres database, and confirm whether the pin survives
- [ ] Inspect current watchlist schema/API/frontend state and record where symbol-only identity causes same-symbol or same-name search results to all appear pinned
- [ ] Record the chosen durable instrument identity in `STATUS.md`; it must include provider, provider symbol id / IBKR `conid` when present, symbol, exchange/market, currency, and asset class as needed to distinguish search results from different markets
- [ ] Confirm localStorage remains non-authoritative and cannot be the reason pins appear saved when Postgres did not persist them

**Artifacts:**
- `tasks/TP-031-watchlist-persistence-market-specific-pins/STATUS.md` (modified)

### Step 1: Make backend watchlist persistence durable and instrument-specific

- [ ] Add a stable watchlist `pinKey` / `instrumentKey` (name may vary, but API JSON must expose it) derived from provider identity plus market metadata, not from bare symbol alone
- [ ] Update Postgres schema initialization with an idempotent migration that preserves existing rows while allowing multiple rows with the same symbol/name when provider/market identity differs
- [ ] Update pin/upsert duplicate handling to merge only the exact same instrument key; pinning `AAPL` on one exchange/market must not overwrite or delete `AAPL` from another exchange/market
- [ ] Update unpin behavior to remove by exact instrument key or exact provider/market identity while retaining a backward-compatible symbol-only removal path only when unambiguous
- [ ] Fix any root cause discovered for pins disappearing after service restart, and ensure unavailable database states are surfaced as errors rather than silently treating localStorage as saved state
- [ ] Run targeted Workspaces tests

**Artifacts:**
- `src/ATrade.Workspaces/PostgresWorkspaceWatchlistSql.cs` (modified)
- `src/ATrade.Workspaces/PostgresWorkspaceWatchlistRepository.cs` (modified)
- `src/ATrade.Workspaces/WorkspaceWatchlistModels.cs` (modified)
- `src/ATrade.Workspaces/WorkspaceWatchlistNormalizer.cs` (modified)
- `src/ATrade.Api/Program.cs` (modified)
- `tests/ATrade.Workspaces.Tests/WorkspaceWatchlistInstrumentKeyTests.cs` (new)
- `tests/ATrade.Workspaces.Tests/*` (modified)

### Step 2: Update frontend pin state to use exact instrument identity

- [ ] Update `watchlistClient` types and helpers so responses and mutations carry the backend instrument key / provider-market identity
- [ ] Replace symbol-only pinned/saving state in `TradingWorkspace`, `SymbolSearch`, `TrendingList`, and `Watchlist` with exact instrument keys; pinning one search result must not mark same-symbol results from other markets as pinned
- [ ] Update removal actions to call the exact unpin path when an instrument key/provider identity is present, while preserving manual/trending symbol behavior where exact metadata is unavailable
- [ ] Keep browser `localStorage` cache non-authoritative; if it only stores symbols, treat it as legacy manual migration data and do not use it to infer provider-market pins
- [ ] Run frontend build or targeted frontend tests after the state change

**Artifacts:**
- `frontend/lib/watchlistClient.ts` (modified)
- `frontend/lib/watchlistStorage.ts` (modified if migration/cache behavior changes)
- `frontend/components/TradingWorkspace.tsx` (modified)
- `frontend/components/SymbolSearch.tsx` (modified)
- `frontend/components/TrendingList.tsx` (modified)
- `frontend/components/Watchlist.tsx` (modified)
- `frontend/types/marketData.ts` (modified if shared identity helpers/types are added)

### Step 3: Show market/exchange logos and explicit market metadata in search

- [ ] Add a local `MarketLogo`/exchange badge component or equivalent UI that maps common market/exchange codes to relevant non-proprietary local logos/badges (for example NASDAQ, NYSE, ARCA, LSE, TSX/TSE, HKEX, SMART/IBKR fallback)
- [ ] Render each search result with explicit provider, exchange/market, currency, asset class, and provider symbol id/IBKR `conid` when available
- [ ] Ensure duplicate company-name/symbol results have unique React keys and accessible labels that include market/exchange information
- [ ] Show the same market identity in the saved watchlist so users can distinguish pinned instruments after restart
- [ ] Add/update frontend source/runtime tests for market badges and exact pinned state

**Artifacts:**
- `frontend/components/MarketLogo.tsx` (new, or equivalent)
- `frontend/components/SymbolSearch.tsx` (modified)
- `frontend/components/Watchlist.tsx` (modified)
- `frontend/app/globals.css` (modified)
- `tests/apphost/frontend-trading-workspace-tests.sh` (modified)
- `tests/apphost/ibkr-symbol-search-tests.sh` (modified)

### Step 4: Add restart and duplicate-market regression coverage

- [ ] Extend `tests/apphost/postgres-watchlist-persistence-tests.sh` so it pins provider-backed symbols, restarts the API/service against the same Postgres database, and verifies exact pins survive
- [ ] Add duplicate-market fixtures/tests where two search/watchlist entries share symbol or display name but differ by exchange/provider id/currency; pinning/removing one must not affect the other
- [ ] Ensure frontend tests detect symbol-only pinned-state regressions in `SymbolSearch` and `Watchlist`
- [ ] Verify database-unavailable behavior does not claim pins were persisted when only cached localStorage entries are visible
- [ ] Run targeted backend/frontend tests/scripts changed by this step

**Artifacts:**
- `tests/apphost/postgres-watchlist-persistence-tests.sh` (modified)
- `tests/apphost/ibkr-symbol-search-tests.sh` (modified)
- `tests/apphost/frontend-trading-workspace-tests.sh` (modified)
- `tests/ATrade.Workspaces.Tests/*` (modified)

### Step 5: Testing & Verification

> ZERO unexpected test failures allowed. Runtime-dependent checks must pass or cleanly skip according to existing contracts.

- [ ] Run `dotnet test tests/ATrade.Workspaces.Tests/ATrade.Workspaces.Tests.csproj --nologo --verbosity minimal`
- [ ] Run `bash tests/apphost/postgres-watchlist-persistence-tests.sh`
- [ ] Run `bash tests/apphost/ibkr-symbol-search-tests.sh`
- [ ] Run `bash tests/apphost/frontend-trading-workspace-tests.sh`
- [ ] Run frontend build: `cd frontend && npm run build`
- [ ] Run FULL test suite: `dotnet test ATrade.slnx --nologo --verbosity minimal`
- [ ] Run solution build: `dotnet build ATrade.slnx --nologo --verbosity minimal`
- [ ] Fix all failures or record pre-existing unrelated failures with evidence in `STATUS.md`

### Step 6: Documentation & Delivery

- [ ] "Must Update" docs describe durable backend persistence and exact provider/market pin identity
- [ ] "Check If Affected" docs reviewed and updated only where relevant
- [ ] `STATUS.md` Discoveries record the persistence root cause, identity key semantics, and any migration caveats

## Documentation Requirements

**Must Update:**
- `docs/architecture/paper-trading-workspace.md` — update watchlist persistence, exact market-specific pinning, localStorage caveats, and search UI market-label behavior
- `docs/architecture/modules.md` — update Workspaces/API/frontend responsibilities for instrument-key pins
- `docs/architecture/provider-abstractions.md` — document provider/market identity expectations if search/watchlist identity wording changes

**Check If Affected:**
- `README.md` — update if current runtime surface wording about watchlists/search becomes stale
- `docs/architecture/overview.md` — update only if storage responsibilities materially change
- `docs/INDEX.md` — update only if new active docs are introduced

## Completion Criteria

- [ ] Pinned favorite stocks persist in Postgres and survive API/service restart with the same database
- [ ] Search results explicitly show provider and market/exchange identity with a relevant local logo/badge
- [ ] Pinning a specific search result pins only that exact provider/market instrument, not all results sharing the same symbol or name
- [ ] Unpinning/removing one market-specific pin does not remove other markets' pins for the same symbol/name
- [ ] Browser localStorage remains non-authoritative and cannot mask failed backend persistence
- [ ] Tests cover restart persistence, duplicate-market identity, frontend pinned state, and market badge rendering

## Git Commit Convention

Commits happen at **step boundaries** (not after every checkbox). All commits for this task MUST include the task ID for traceability:

- **Step completion:** `fix(TP-031): complete Step N — description`
- **Bug fixes:** `fix(TP-031): description`
- **Tests:** `test(TP-031): description`
- **Hydration:** `hydrate: TP-031 expand Step N checkboxes`

## Do NOT

- Treat browser localStorage as the authoritative persistence store
- Collapse provider/market identity back to bare symbol or display name
- Introduce remote/proprietary market-logo assets without approval; use local/non-proprietary badges/logos
- Read, print, or commit ignored `.env` values or broker credentials
- Add real order placement or live-trading behavior
- Skip tests or commit without the task ID prefix

---

## Amendments (Added During Execution)

<!-- Workers add amendments here if issues discovered during execution.
     Format:
     ### Amendment N — YYYY-MM-DD HH:MM
     **Issue:** [what was wrong]
     **Resolution:** [what was changed] -->
