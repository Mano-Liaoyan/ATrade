# Task: TP-020 - Persist pinned stock watchlists in Postgres

**Created:** 2026-04-29
**Size:** L

## Review Level: 2 (Plan and Code)

**Assessment:** This adds the first backend-owned workspace preference store and changes the watchlist from browser-local state to Postgres-backed state. It touches a new persistence module, API endpoints, frontend state flow, database verification, and docs, but does not handle secrets or broker trading.
**Score:** 5/8 — Blast radius: 2, Pattern novelty: 1, Security: 0, Reversibility: 2

## Canonical Task Folder

```text
tasks/TP-020-postgres-pinned-watchlist/
├── PROMPT.md   ← This file (immutable above --- divider)
├── STATUS.md   ← Execution state (worker updates this)
├── .reviews/   ← Reviewer output (created by the orchestrator runtime)
└── .DONE       ← Created when complete
```

## Mission

Make pinned stocks/watchlists persistent after API/server restarts by moving the authoritative watchlist state from browser `localStorage` into the AppHost-managed Postgres database. The frontend may keep a short-lived browser cache or one-time migration path, but the backend must become the source of truth for pinned symbols. This task should also prepare the schema for later IBKR search metadata (`conid`, exchange, currency, asset class, provider) so TP-023 can pin any IBKR-searchable stock without a disruptive migration.

## Dependencies

- **Task:** TP-018 (current Next.js watchlist UI must exist)
- **Task:** TP-019 (provider-neutral symbol/market-data contracts must exist)

## Context to Read First

> Only load these files unless implementation reveals a directly related missing prerequisite.

**Tier 2 (area context):**
- `tasks/CONTEXT.md`

**Tier 3 (load only if needed):**
- `docs/architecture/paper-trading-workspace.md` — preference storage and frontend/backend ownership contract
- `docs/architecture/modules.md` — module boundaries and Postgres ownership expectations
- `docs/architecture/overview.md` — Postgres role and AppHost resource graph
- `docs/architecture/provider-abstractions.md` — provider-neutral symbol identity contract from TP-019
- `src/ATrade.Api/Program.cs` — endpoint and DI registration style
- `src/ATrade.AppHost/Program.cs` — current Postgres reference wiring
- `frontend/components/TradingWorkspace.tsx` — current local watchlist state flow
- `frontend/components/Watchlist.tsx` — current watchlist UI
- `frontend/components/TrendingList.tsx` — current pin/unpin UI
- `frontend/lib/watchlistStorage.ts` — current localStorage helper to replace as authority
- `tests/apphost/frontend-trading-workspace-tests.sh` — frontend watchlist smoke-test baseline
- `tests/apphost/apphost-infrastructure-runtime-tests.sh` — Docker-dependent test skip pattern

## Environment

- **Workspace:** Project root plus `frontend/`
- **Services required:** Automated unit tests must not require external services. The Postgres persistence integration test may start a disposable local Postgres container or AppHost-managed Postgres and must cleanly skip with a clear message when no Docker-compatible runtime is available.

## File Scope

> This task overlaps API/frontend watchlist files and should serialize with search/UI work.

- `ATrade.sln`
- `src/ATrade.Workspaces/*` (new)
- `src/ATrade.Api/ATrade.Api.csproj`
- `src/ATrade.Api/Program.cs`
- `src/ATrade.AppHost/Program.cs` (only if API Postgres wiring requires adjustment)
- `frontend/lib/watchlistClient.ts` (new)
- `frontend/lib/watchlistStorage.ts`
- `frontend/components/TradingWorkspace.tsx`
- `frontend/components/Watchlist.tsx`
- `frontend/components/TrendingList.tsx`
- `frontend/types/marketData.ts` (only if symbol metadata types move here)
- `tests/ATrade.Workspaces.Tests/*` (new)
- `tests/apphost/postgres-watchlist-persistence-tests.sh` (new)
- `tests/apphost/frontend-trading-workspace-tests.sh`
- `docs/architecture/paper-trading-workspace.md`
- `docs/architecture/modules.md`
- `docs/architecture/overview.md`
- `README.md`

## Steps

> **Hydration:** STATUS.md tracks outcomes, not individual code changes. Workers expand steps when runtime discoveries warrant it.

### Step 0: Preflight

- [ ] Required files and paths exist
- [ ] Dependencies satisfied
- [ ] Confirm current frontend watchlist is authoritative in `localStorage` before changing it
- [ ] Confirm `ATrade.Api` already receives the AppHost Postgres connection string through `WithReference(postgres)`

### Step 1: Add the workspace persistence module and schema

- [ ] Create `src/ATrade.Workspaces/ATrade.Workspaces.csproj`, add it to `ATrade.sln`, and reference it from `ATrade.Api`
- [ ] Add a minimal Postgres repository for pinned symbols/watchlists using the existing AppHost connection string (`ConnectionStrings:postgres`) and a narrow dependency such as `Npgsql`; do not introduce a second database
- [ ] Add an idempotent schema initializer for tables that persist a local user/workspace id, symbol, provider, optional IBKR `conid`, name, exchange, currency, asset class, sort order, and timestamps
- [ ] Use a safe default user/workspace id until real authentication exists, and make that temporary seam explicit in code/docs
- [ ] Add unit tests for symbol normalization, duplicate prevention, ordering, and repository SQL shape without requiring a real database
- [ ] Run targeted tests/build: `dotnet test tests/ATrade.Workspaces.Tests/ATrade.Workspaces.Tests.csproj --nologo --verbosity minimal && dotnet build src/ATrade.Workspaces/ATrade.Workspaces.csproj --nologo --verbosity minimal`

**Artifacts:**
- `src/ATrade.Workspaces/ATrade.Workspaces.csproj` (new)
- `src/ATrade.Workspaces/WorkspaceWatchlist*.cs` (new or equivalent)
- `src/ATrade.Workspaces/PostgresWatchlist*.cs` (new or equivalent)
- `src/ATrade.Workspaces/WorkspaceModuleServiceCollectionExtensions.cs` (new)
- `tests/ATrade.Workspaces.Tests/*` (new)
- `ATrade.sln` (modified)

### Step 2: Expose backend watchlist API endpoints

- [ ] Register the Workspaces module and schema initializer in `src/ATrade.Api/Program.cs`
- [ ] Add endpoints for reading and mutating the current workspace watchlist, e.g. `GET /api/workspace/watchlist`, `PUT /api/workspace/watchlist`, `POST /api/workspace/watchlist`, and `DELETE /api/workspace/watchlist/{symbol}`
- [ ] Validate and normalize symbols using the provider-neutral symbol contract from TP-019 when possible, while allowing TP-023 to enrich metadata from IBKR search later
- [ ] Return stable JSON payloads with symbol metadata and clear errors for invalid requests or unavailable Postgres
- [ ] Preserve existing health, accounts, broker, orders, market-data, and SignalR endpoints
- [ ] Run targeted API smoke checks against the new watchlist endpoints

**Artifacts:**
- `src/ATrade.Api/ATrade.Api.csproj` (modified)
- `src/ATrade.Api/Program.cs` (modified)
- `src/ATrade.Workspaces/*` (modified)

### Step 3: Move the frontend watchlist to the backend source of truth

- [ ] Add a frontend watchlist API client that uses `NEXT_PUBLIC_ATRADE_API_BASE_URL` through the existing API base helper
- [ ] Update `TradingWorkspace`, `TrendingList`, and `Watchlist` so pin/unpin operations call the backend and render the backend watchlist response
- [ ] Keep `localStorage` only as a non-authoritative cache or one-time migration source; the UI must no longer label the watchlist as `localStorage`
- [ ] On first successful backend load, migrate any existing localStorage symbols into Postgres once, then render the backend response
- [ ] Show clear loading/error states when the backend or database is unavailable without pretending pins were saved
- [ ] Run targeted frontend build: `cd frontend && npm run build`

**Artifacts:**
- `frontend/lib/watchlistClient.ts` (new)
- `frontend/lib/watchlistStorage.ts` (modified)
- `frontend/components/TradingWorkspace.tsx` (modified)
- `frontend/components/Watchlist.tsx` (modified)
- `frontend/components/TrendingList.tsx` (modified)

### Step 4: Add restart-persistence verification

- [ ] Create `tests/apphost/postgres-watchlist-persistence-tests.sh`
- [ ] Verify the API can initialize the watchlist schema against Postgres
- [ ] Start the API against the same Postgres database, pin symbols, stop the API, restart it, and verify the pins survive the API/server restart
- [ ] Verify duplicate pins are de-duplicated and invalid symbols return stable errors
- [ ] Update `tests/apphost/frontend-trading-workspace-tests.sh` so it asserts backend-persisted watchlist language and no longer expects `localStorage` to be authoritative
- [ ] Run targeted tests: `bash tests/apphost/postgres-watchlist-persistence-tests.sh && bash tests/apphost/frontend-trading-workspace-tests.sh`

**Artifacts:**
- `tests/apphost/postgres-watchlist-persistence-tests.sh` (new)
- `tests/apphost/frontend-trading-workspace-tests.sh` (modified)

### Step 5: Update docs for backend-owned preferences

- [ ] Update `docs/architecture/paper-trading-workspace.md` so watchlists/pinned symbols are current-state Postgres-backed backend preferences, not only future work
- [ ] Update `docs/architecture/modules.md` with the new Workspaces module and frontend/API responsibilities
- [ ] Update `docs/architecture/overview.md` if the current Postgres usage statement changes materially
- [ ] Update `README.md` only if current-status wording becomes stale

**Artifacts:**
- `docs/architecture/paper-trading-workspace.md` (modified)
- `docs/architecture/modules.md` (modified)
- `docs/architecture/overview.md` (modified if affected)
- `README.md` (modified if affected)

### Step 6: Testing & Verification

> ZERO test failures allowed. This step runs the full available repository verification suite as the quality gate.

- [ ] Run FULL test suite: `dotnet test ATrade.sln --nologo --verbosity minimal && bash tests/start-contract/start-wrapper-tests.sh && bash tests/scaffolding/project-shells-tests.sh && bash tests/apphost/api-bootstrap-tests.sh && bash tests/apphost/accounts-feature-bootstrap-tests.sh && bash tests/apphost/ibkr-paper-safety-tests.sh && bash tests/apphost/market-data-feature-tests.sh && bash tests/apphost/provider-abstraction-contract-tests.sh && bash tests/apphost/postgres-watchlist-persistence-tests.sh && bash tests/apphost/frontend-nextjs-bootstrap-tests.sh && bash tests/apphost/frontend-trading-workspace-tests.sh && bash tests/apphost/apphost-infrastructure-manifest-tests.sh && bash tests/apphost/apphost-worker-resource-wiring-tests.sh && bash tests/apphost/local-port-contract-tests.sh && bash tests/apphost/paper-trading-config-contract-tests.sh && bash tests/apphost/apphost-infrastructure-runtime-tests.sh`
- [ ] Confirm Docker-dependent Postgres/runtime tests pass or cleanly skip when no Docker-compatible engine is available
- [ ] Fix all failures
- [ ] Frontend build passes: `cd frontend && npm run build`
- [ ] Solution build passes: `dotnet build ATrade.sln --nologo --verbosity minimal`

### Step 7: Documentation & Delivery

- [ ] "Must Update" docs modified
- [ ] "Check If Affected" docs reviewed
- [ ] Discoveries logged in STATUS.md

## Documentation Requirements

**Must Update:**
- `docs/architecture/paper-trading-workspace.md` — record Postgres-backed watchlists as implemented current state
- `docs/architecture/modules.md` — add/update Workspaces, API, and frontend responsibilities for backend-owned preferences

**Check If Affected:**
- `docs/architecture/overview.md` — update if Postgres current usage changes
- `README.md` — update if user-facing current status becomes stale
- `docs/INDEX.md` — update only if a new indexed document is added (none expected)

## Completion Criteria

- [ ] Pinned symbols are stored in Postgres and survive API/server restarts
- [ ] Frontend pin/unpin flows use backend API state as the source of truth
- [ ] Existing localStorage pins migrate safely or remain only as a non-authoritative cache/fallback
- [ ] Tests prove persistence across restart, duplicate handling, and frontend/backend integration
- [ ] Active docs accurately describe backend-owned watchlist persistence and the temporary no-auth local-user seam

## Git Commit Convention

Commits happen at **step boundaries** (not after every checkbox). All commits for this task MUST include the task ID for traceability:

- **Step completion:** `feat(TP-020): complete Step N — description`
- **Bug fixes:** `fix(TP-020): description`
- **Tests:** `test(TP-020): description`
- **Hydration:** `hydrate: TP-020 expand Step N checkboxes`

## Do NOT

- Keep browser `localStorage` as the authoritative watchlist store
- Store secrets, broker credentials, or account identifiers in watchlist rows or localStorage
- Introduce a database other than the existing AppHost-managed Postgres resource
- Require a real IBKR/iBeam session for watchlist persistence tests
- Add real order placement, live trading, or LEAN behavior in this task
- Load docs not listed in "Context to Read First" unless a missing prerequisite is discovered and recorded

---

## Amendments (Added During Execution)

<!-- Workers add amendments here if issues discovered during execution.
     Format:
     ### Amendment N — YYYY-MM-DD HH:MM
     **Issue:** [what was wrong]
     **Resolution:** [what was changed] -->
