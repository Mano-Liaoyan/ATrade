# Task: TP-028 - Fix IBKR scanner 411 Length Required for trending

**Created:** 2026-04-30
**Size:** M

## Review Level: 2 (Plan and Code)

**Assessment:** This is a focused runtime fix in the IBKR/iBeam market-data provider, but it affects the home-page `/api/market-data/trending` path, authenticated Client Portal transport, provider error handling, tests, and active docs. It must preserve no-secrets diagnostics and no mocked market-data fallback.
**Score:** 4/8 — Blast radius: 1, Pattern novelty: 1, Security: 1, Reversibility: 1

## Canonical Task Folder

```text
tasks/TP-028-ibkr-scanner-content-length-fix/
├── PROMPT.md   ← This file (immutable above --- divider)
├── STATUS.md   ← Execution state (worker updates this)
├── .reviews/   ← Reviewer output (created by the orchestrator runtime)
└── .DONE       ← Created when complete
```

## Mission

Fix the frontend home-page failure where loading trending market data calls `/api/market-data/trending` and the IBKR/iBeam scanner request fails with `411 Length Required` and an HTML Akamai/edge error body. The IBKR scanner call must send a Client Portal-compatible request with an explicit request body length, return real provider-backed trending data when iBeam is authenticated, and continue to surface safe provider-unavailable/authentication-required states when iBeam is not ready.

## Dependencies

- **None**

## Context to Read First

> Only load these files unless implementation reveals a directly related missing prerequisite. Do **not** read, print, or commit the ignored repo-root `.env` file.

**Tier 2 (area context):**
- `tasks/CONTEXT.md`

**Tier 3 (load only if needed):**
- `docs/architecture/provider-abstractions.md` — IBKR market-data provider and no-fallback contract
- `docs/architecture/paper-trading-workspace.md` — home-page trending and iBeam runtime contract
- `docs/architecture/modules.md` — MarketData and frontend module ownership
- `src/ATrade.MarketData.Ibkr/IbkrMarketDataClient.cs` — scanner request implementation and error mapping
- `src/ATrade.MarketData.Ibkr/IbkrMarketDataProvider.cs` — trending composition and safe provider errors
- `src/ATrade.MarketData.Ibkr/IbkrMarketDataModels.cs` — scanner/provider model shapes if needed
- `tests/ATrade.MarketData.Ibkr.Tests/IbkrMarketDataProviderTests.cs` — existing provider test style
- `tests/apphost/ibkr-market-data-provider-tests.sh` — provider smoke/source contract
- `tests/apphost/market-data-feature-tests.sh` — `/api/market-data/trending` behavior
- `tests/apphost/frontend-trading-workspace-tests.sh` — home-page market-data UX checks
- `frontend/components/TradingWorkspace.tsx` and `frontend/lib/marketDataClient.ts` — update only if backend-safe errors still render poorly

## Environment

- **Workspace:** Repository root
- **Services required:** Automated tests must not require real IBKR credentials. Optional manual verification may use `./start run` and ignored local `.env` values if already configured; it must be skipped cleanly when local iBeam/authentication is unavailable.

## File Scope

> The orchestrator uses this to avoid merge conflicts. Keep changes inside this scope unless `STATUS.md` records a discovered prerequisite.

- `src/ATrade.MarketData.Ibkr/IbkrMarketDataClient.cs`
- `src/ATrade.MarketData.Ibkr/IbkrMarketDataModels.cs` (only if typed scanner request/response models move here)
- `src/ATrade.MarketData.Ibkr/IbkrMarketDataProvider.cs` (only if provider error mapping or trending source metadata needs adjustment)
- `tests/ATrade.MarketData.Ibkr.Tests/IbkrScannerRequestContractTests.cs` (new, or equivalent new focused test file)
- `tests/ATrade.MarketData.Ibkr.Tests/IbkrMarketDataProviderTests.cs`
- `tests/apphost/ibkr-market-data-provider-tests.sh`
- `tests/apphost/market-data-feature-tests.sh`
- `tests/apphost/frontend-trading-workspace-tests.sh` (only if frontend error rendering changes)
- `frontend/components/TradingWorkspace.tsx` (only if UX copy/state changes)
- `frontend/lib/marketDataClient.ts` (only if safe error formatting changes)
- `docs/architecture/provider-abstractions.md`
- `docs/architecture/paper-trading-workspace.md`
- `docs/architecture/modules.md` (only if module responsibilities change)
- `tasks/TP-028-ibkr-scanner-content-length-fix/STATUS.md`

## Steps

> **Hydration:** STATUS.md tracks outcomes, not individual code changes. Workers expand steps when runtime discoveries warrant it.

### Step 0: Preflight and failure classification

- [ ] Record the sanitized observed failure in `STATUS.md`: `/api/market-data/trending` fails because iBeam scanner returns `411 Length Required` with an HTML edge error body
- [ ] Inspect the current scanner request implementation and identify whether it uses chunked transfer, missing `Content-Length`, wrong HTTP method, wrong content type, or another Client Portal-incompatible shape
- [ ] Confirm the fix can be covered with fake HTTP handlers without real IBKR credentials, and document any optional real-iBeam verification as skipped or redacted

**Artifacts:**
- `tasks/TP-028-ibkr-scanner-content-length-fix/STATUS.md` (modified)

### Step 1: Send a Client Portal-compatible scanner request

- [ ] Replace the scanner call with an explicit `HttpRequestMessage` or equivalent implementation that sends `POST /v1/api/iserver/scanner/run` with JSON content, `Content-Type: application/json`, a non-empty request body, and an explicit `Content-Length`; it must not use chunked transfer for this endpoint
- [ ] Keep the scanner payload semantics equivalent to the current top-percent-gainer stock scanner (`instrument=STK`, `location=STK.US.MAJOR`, `type=TOP_PERC_GAIN`, empty filter) unless source evidence requires a corrected official payload shape
- [ ] Preserve safe provider error mapping for 401/403/authentication-required and provider-unavailable responses, while avoiding secrets, account ids, session ids, cookies, tokens, or raw credentials in logs or API responses
- [ ] Ensure the scanner response parser still maps valid fake IBKR scanner responses to provider-neutral trending symbols with source metadata
- [ ] Run targeted market-data provider tests affected by the request-shape change

**Artifacts:**
- `src/ATrade.MarketData.Ibkr/IbkrMarketDataClient.cs` (modified)
- `src/ATrade.MarketData.Ibkr/IbkrMarketDataModels.cs` (modified only if typed request models are added)
- `src/ATrade.MarketData.Ibkr/IbkrMarketDataProvider.cs` (modified only if needed)

### Step 2: Add scanner request-shape regression coverage

- [ ] Create a new focused test file such as `tests/ATrade.MarketData.Ibkr.Tests/IbkrScannerRequestContractTests.cs` that asserts scanner requests use `POST`, include JSON content, set a positive `Content-Length`, and do not set chunked transfer
- [ ] Add or update tests for scanner error mapping so a fake `411 Length Required` response becomes a safe provider-unavailable error without leaking raw credentials or local secrets
- [ ] Update apphost/source contract scripts if they currently cannot detect a regression to chunked/missing-length scanner requests
- [ ] Run targeted tests/scripts changed by this step

**Artifacts:**
- `tests/ATrade.MarketData.Ibkr.Tests/IbkrScannerRequestContractTests.cs` (new)
- `tests/ATrade.MarketData.Ibkr.Tests/IbkrMarketDataProviderTests.cs` (modified if needed)
- `tests/apphost/ibkr-market-data-provider-tests.sh` (modified if source-contract checks are added)
- `tests/apphost/market-data-feature-tests.sh` (modified if endpoint assertions change)

### Step 3: Verify home-page trending behavior

- [ ] Verify `GET /api/market-data/trending` still returns safe `503` provider errors when iBeam is disabled, missing credentials, unreachable, or unauthenticated
- [ ] Verify fake authenticated scanner responses flow through `/api/market-data/trending` to frontend-compatible `TrendingSymbolsResponse` JSON
- [ ] If a local authenticated iBeam runtime is available, run a manual redacted smoke check that no longer receives `411 Length Required`; otherwise record the skip rationale in `STATUS.md`
- [ ] Update frontend error copy only if the backend now emits a better safe diagnostic that the UI should display differently

**Artifacts:**
- `tests/apphost/market-data-feature-tests.sh` (modified if needed)
- `tests/apphost/frontend-trading-workspace-tests.sh` (modified only if frontend behavior changes)
- `frontend/components/TradingWorkspace.tsx` (modified only if frontend behavior changes)
- `frontend/lib/marketDataClient.ts` (modified only if frontend behavior changes)

### Step 4: Testing & Verification

> ZERO unexpected test failures allowed. Runtime-dependent checks must pass or cleanly skip according to existing contracts.

- [ ] Run `dotnet test tests/ATrade.MarketData.Ibkr.Tests/ATrade.MarketData.Ibkr.Tests.csproj --nologo --verbosity minimal`
- [ ] Run `bash tests/apphost/ibkr-market-data-provider-tests.sh`
- [ ] Run `bash tests/apphost/market-data-feature-tests.sh`
- [ ] If frontend files changed, run `bash tests/apphost/frontend-trading-workspace-tests.sh`
- [ ] Run FULL test suite: `dotnet test ATrade.slnx --nologo --verbosity minimal`
- [ ] If frontend files changed, run frontend build: `cd frontend && npm run build`
- [ ] Run solution build: `dotnet build ATrade.slnx --nologo --verbosity minimal`
- [ ] Fix all failures or record pre-existing unrelated failures with evidence in `STATUS.md`

### Step 5: Documentation & Delivery

- [ ] "Must Update" docs describe the corrected scanner request/body-length contract and the user-facing `/trending` fix where relevant
- [ ] "Check If Affected" docs reviewed and updated only where relevant
- [ ] `STATUS.md` Discoveries record the root cause, regression coverage, and optional real-iBeam verification result or skip rationale

## Documentation Requirements

**Must Update:**
- `docs/architecture/provider-abstractions.md` — document any scanner request-shape constraint that belongs to the IBKR provider contract
- `docs/architecture/paper-trading-workspace.md` — update trending/iBeam troubleshooting language if the 411 root cause or retry guidance changes

**Check If Affected:**
- `docs/architecture/modules.md` — update only if responsibilities or module boundaries change
- `README.md` — update only if the current runtime surface or troubleshooting summary changes
- `scripts/README.md` — update only if local iBeam startup guidance changes
- `docs/INDEX.md` — update only if new active docs are introduced

## Completion Criteria

- [ ] The scanner/trending request no longer uses a missing-length/chunked request shape that can trigger iBeam `411 Length Required`
- [ ] `GET /api/market-data/trending` still returns safe provider errors when iBeam is unavailable and real provider data when authenticated
- [ ] Regression tests assert the scanner request has explicit JSON content length and safe error mapping
- [ ] No production mock market-data fallback is introduced
- [ ] Active docs reflect any durable scanner/iBeam contract change

## Git Commit Convention

Commits happen at **step boundaries** (not after every checkbox). All commits for this task MUST include the task ID for traceability:

- **Step completion:** `fix(TP-028): complete Step N — description`
- **Bug fixes:** `fix(TP-028): description`
- **Tests:** `test(TP-028): description`
- **Hydration:** `hydrate: TP-028 expand Step N checkboxes`

## Do NOT

- Read, print, or commit ignored `.env` values, IBKR credentials, account ids, session cookies, or tokens
- Reintroduce production mock market data or hard-coded production symbol catalogs
- Change the iBeam gateway URL/scheme/certificate contract unless a recorded prerequisite proves it is directly required
- Hide provider-unavailable/authentication-required states behind stale success responses
- Skip tests or commit without the task ID prefix

---

## Amendments (Added During Execution)

<!-- Workers add amendments here if issues discovered during execution.
     Format:
     ### Amendment N — YYYY-MM-DD HH:MM
     **Issue:** [what was wrong]
     **Resolution:** [what was changed] -->
