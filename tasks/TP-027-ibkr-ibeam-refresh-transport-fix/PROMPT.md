# Task: TP-027 - Fix authenticated iBeam refresh transport failures

**Created:** 2026-04-30
**Size:** M

## Review Level: 3 (Full)

**Assessment:** This fix spans the AppHost/iBeam runtime contract, shared broker and market-data HTTP clients, tests, and active setup docs. It is security-sensitive because the likely fix involves the local iBeam transport scheme and possibly self-signed TLS handling, which must stay narrowly scoped and must not weaken credential/session secrecy.
**Score:** 6/8 — Blast radius: 2, Pattern novelty: 1, Security: 2, Reversibility: 1

## Canonical Task Folder

```text
tasks/TP-027-ibkr-ibeam-refresh-transport-fix/
├── PROMPT.md   ← This file (immutable above --- divider)
├── STATUS.md   ← Execution state (worker updates this)
├── .reviews/   ← Reviewer output (created by the orchestrator runtime)
└── .DONE       ← Created when complete
```

## Mission

Fix the failure where clicking **Retry/Refresh IBKR market data** in the Aspire-run workspace returns a safe 503 even though the local `voyz/ibeam:latest` gateway reports that it is running and authenticated. The observed backend calls `GET http://127.0.0.1:<gateway-port>/v1/api/iserver/auth/status`, then both `IIbkrMarketDataClient` and `IIbkrGatewayClient` fail with `HttpRequestException` / `IOException` / `SocketException (104): Connection reset by peer`. The fix must make authenticated local iBeam refreshes work through the provider-neutral API while preserving safe unavailable/not-configured behavior, no-secrets logging, paper-only guardrails, and no mock-data fallback.

## Dependencies

- **None**

## Context to Read First

> Only load these files unless implementation reveals a directly related missing prerequisite. Do **not** read, print, or commit the ignored repo-root `.env` file.

**Tier 1 (repo and task context):**
- `README.md`
- `PLAN.md`
- `docs/INDEX.md`
- `tasks/CONTEXT.md`

**Tier 2 (active architecture/setup docs):**
- `docs/architecture/provider-abstractions.md` — provider-unavailable/not-configured contract and current IBKR provider rules
- `docs/architecture/paper-trading-workspace.md` — authoritative paper-only iBeam workspace contract
- `docs/architecture/modules.md` — module ownership for AppHost, broker, market-data, worker, and frontend
- `scripts/README.md` — local `.env`/AppHost/iBeam startup contract

**Tier 3 (implementation surface):**
- `src/ATrade.AppHost/Program.cs`
- `src/ATrade.Brokers.Ibkr/IbkrGatewayOptions.cs`
- `src/ATrade.Brokers.Ibkr/IbkrServiceCollectionExtensions.cs`
- `src/ATrade.Brokers.Ibkr/IbkrGatewayClient.cs`
- `src/ATrade.Brokers.Ibkr/IbkrBrokerStatusService.cs`
- `src/ATrade.MarketData.Ibkr/IbkrMarketDataClient.cs`
- `src/ATrade.MarketData.Ibkr/IbkrMarketDataProvider.cs`
- `src/ATrade.Api/Program.cs`
- `frontend/components/TradingWorkspace.tsx`
- `frontend/lib/marketDataClient.ts`
- Existing IBKR/AppHost tests under `tests/ATrade.Brokers.Ibkr.Tests/`, `tests/ATrade.MarketData.Ibkr.Tests/`, and `tests/apphost/`
- `.env.template` and `.env.example` (committed templates only; never read ignored `.env`)

## Environment

- **Workspace:** Repository root
- **Services required:** None for automated unit/script tests. Optional real-runtime verification may use `./start run` plus ignored local `.env` values if they are already configured on the developer machine, but the task must pass or cleanly skip real IBKR/iBeam checks when credentials/runtime are unavailable.

## File Scope

> The orchestrator uses this to avoid merge conflicts. Keep changes inside this scope unless `STATUS.md` records a discovered prerequisite.

- `src/ATrade.AppHost/Program.cs`
- `src/ATrade.Brokers.Ibkr/IbkrGatewayOptions.cs`
- `src/ATrade.Brokers.Ibkr/IbkrServiceCollectionExtensions.cs`
- `src/ATrade.Brokers.Ibkr/IbkrGatewayClient.cs`
- `src/ATrade.Brokers.Ibkr/IbkrBrokerStatusService.cs`
- `src/ATrade.Brokers.Ibkr/*Gateway*Http*.cs` (new shared transport helper if useful)
- `src/ATrade.MarketData.Ibkr/IbkrMarketDataClient.cs`
- `src/ATrade.MarketData.Ibkr/IbkrMarketDataProvider.cs`
- `src/ATrade.Api/Program.cs` (only if API error mapping needs a provider-neutral diagnostic tweak)
- `frontend/components/TradingWorkspace.tsx` (only if retry UX needs a copy/state fix after backend transport is corrected)
- `frontend/lib/marketDataClient.ts` (only if user-facing provider error formatting needs a safe diagnostic tweak)
- `tests/ATrade.Brokers.Ibkr.Tests/*`
- `tests/ATrade.MarketData.Ibkr.Tests/*`
- `tests/apphost/ibeam-runtime-contract-tests.sh`
- `tests/apphost/ibkr-paper-safety-tests.sh`
- `tests/apphost/ibkr-market-data-provider-tests.sh`
- `tests/apphost/market-data-feature-tests.sh`
- `tests/apphost/frontend-trading-workspace-tests.sh` (only if frontend retry behavior changes)
- `.env.template`
- `.env.example` (restore/update only as a committed template synchronized with `.env.template`; never copy from ignored `.env`)
- `README.md`
- `PLAN.md`
- `tasks/CONTEXT.md`
- `scripts/README.md`
- `docs/architecture/provider-abstractions.md`
- `docs/architecture/paper-trading-workspace.md`
- `docs/architecture/modules.md`
- `tasks/TP-027-ibkr-ibeam-refresh-transport-fix/STATUS.md`

## Steps

> **Hydration:** STATUS.md tracks outcomes, not individual code changes. Workers expand steps when runtime discoveries warrant it.

### Step 0: Preflight and failure classification

- [ ] Confirm `TP-027` context and record the sanitized user-observed failure in `STATUS.md` without raw session ids, account ids, credentials, cookies, or local `.env` values
- [ ] Inventory current iBeam gateway URL scheme/port handling across AppHost, broker client, market-data client, committed templates, docs, and tests
- [ ] Determine whether the connection reset is caused by HTTP-vs-HTTPS/TLS/self-signed certificate handling, readiness/race behavior, port mapping, or another transport issue; record the evidence in `STATUS.md`
- [ ] If a real local iBeam runtime is available, reproduce with redacted commands and compare HTTP vs HTTPS auth-status behavior; otherwise add/identify automated simulations that cover the suspected transport failure without real credentials

**Artifacts:**
- `tasks/TP-027-ibkr-ibeam-refresh-transport-fix/STATUS.md` (modified)

### Step 1: Implement the shared IBKR/iBeam transport fix

- [ ] Add or update shared gateway transport configuration so both broker status and market-data clients use the same correct local iBeam scheme, timeout, handler, and validation behavior
- [ ] If the fix requires trusting a self-signed local iBeam certificate, scope that trust to loopback/local iBeam development traffic only; do not disable certificate validation globally or for arbitrary hosts
- [ ] Align AppHost endpoint metadata and committed gateway URL defaults/templates with the actual `voyz/ibeam:latest` transport contract, or record why no template/default change is required
- [ ] Improve redacted backend diagnostics for transport reset/scheme mismatch cases so users get actionable provider-unavailable guidance without leaking host secrets, credentials, account ids, session ids, cookies, or tokens
- [ ] Run targeted broker/market-data tests affected by the shared transport change

**Artifacts:**
- `src/ATrade.Brokers.Ibkr/IbkrGatewayOptions.cs` (modified if option normalization/validation changes)
- `src/ATrade.Brokers.Ibkr/IbkrServiceCollectionExtensions.cs` (modified)
- `src/ATrade.Brokers.Ibkr/IbkrGatewayClient.cs` (modified if diagnostics or request behavior change)
- `src/ATrade.Brokers.Ibkr/*Gateway*Http*.cs` (new/modified if shared helper is introduced)
- `src/ATrade.MarketData.Ibkr/IbkrMarketDataProvider.cs` (modified)
- `src/ATrade.MarketData.Ibkr/IbkrMarketDataClient.cs` (modified if diagnostics or request behavior change)
- `src/ATrade.AppHost/Program.cs` (modified if endpoint scheme/metadata changes)
- `.env.template` and `.env.example` (modified/restored if committed defaults change)

### Step 2: Add regression coverage for the transport contract

- [ ] Create a new focused regression test file, e.g. `tests/ATrade.Brokers.Ibkr.Tests/IbkrGatewayTransportContractTests.cs`, covering the local iBeam transport contract and any certificate-validation guardrails introduced by Step 1
- [ ] Update broker and market-data unit tests so expected gateway URLs, auth-status calls, timeout behavior, and provider-unavailable diagnostics match the corrected transport contract
- [ ] Extend AppHost/config shell tests so committed templates and manifests cannot regress to a gateway scheme/port combination that causes authenticated local iBeam to reset connections
- [ ] Add or update a cleanly-skipping optional real-iBeam smoke check if a suitable test hook exists; it must never require committed credentials and must not print secrets
- [ ] Run targeted tests/scripts changed by this step

**Artifacts:**
- `tests/ATrade.Brokers.Ibkr.Tests/IbkrGatewayTransportContractTests.cs` (new, or equivalent new test file if a better name is chosen)
- `tests/ATrade.Brokers.Ibkr.Tests/*` (modified as needed)
- `tests/ATrade.MarketData.Ibkr.Tests/*` (modified as needed)
- `tests/apphost/ibeam-runtime-contract-tests.sh` (modified if manifest/template contract changes)
- `tests/apphost/ibkr-paper-safety-tests.sh` (modified if template or status diagnostics change)
- `tests/apphost/ibkr-market-data-provider-tests.sh` (modified if provider diagnostics/config expectations change)
- `tests/apphost/market-data-feature-tests.sh` (modified if market-data unavailable behavior changes)

### Step 3: Verify API and frontend refresh behavior

- [ ] Verify `GET /api/broker/ibkr/status` and `GET /api/market-data/trending` use the corrected transport path and no longer fail with connection-reset when local iBeam is authenticated
- [ ] Ensure unauthenticated, disabled, missing-credential, or unreachable iBeam states still return safe provider/broker status JSON rather than mock data or unhandled exceptions
- [ ] Ensure the TradingWorkspace retry/refresh UX can recover after iBeam becomes authenticated; update frontend error copy only if backend diagnostics alone are insufficient
- [ ] Preserve provider-neutral API/frontend payloads and source metadata; do not expose gateway URLs, usernames, passwords, account ids, session ids, cookies, or tokens

**Artifacts:**
- `src/ATrade.Api/Program.cs` (modified only if provider-neutral error mapping changes)
- `frontend/components/TradingWorkspace.tsx` (modified only if retry UX changes)
- `frontend/lib/marketDataClient.ts` (modified only if safe error formatting changes)
- Relevant apphost/frontend tests from Step 2 (modified if behavior changes)

### Step 4: Testing & Verification

> ZERO unexpected test failures allowed. Runtime-dependent checks must pass or cleanly skip according to existing contracts.

- [ ] Run `dotnet test tests/ATrade.Brokers.Ibkr.Tests/ATrade.Brokers.Ibkr.Tests.csproj --nologo --verbosity minimal`
- [ ] Run `dotnet test tests/ATrade.MarketData.Ibkr.Tests/ATrade.MarketData.Ibkr.Tests.csproj --nologo --verbosity minimal`
- [ ] Run `bash tests/apphost/ibeam-runtime-contract-tests.sh`
- [ ] Run `bash tests/apphost/ibkr-paper-safety-tests.sh`
- [ ] Run `bash tests/apphost/ibkr-market-data-provider-tests.sh`
- [ ] Run `bash tests/apphost/market-data-feature-tests.sh`
- [ ] If frontend files changed, run `bash tests/apphost/frontend-trading-workspace-tests.sh`
- [ ] Run FULL test suite: `dotnet test ATrade.slnx --nologo --verbosity minimal`
- [ ] Optional real-runtime verification, only when ignored local `.env` and iBeam are available: run `./start run`, trigger the frontend retry/refresh, and/or call the local API trending endpoint; record only redacted results in `STATUS.md`
- [ ] Fix all failures or record pre-existing failures with evidence if they are unrelated and outside this task's scope

### Step 5: Documentation & Delivery

- [ ] "Must Update" docs/templates modified to describe the corrected iBeam gateway URL/scheme/certificate/readiness contract
- [ ] "Check If Affected" docs reviewed and updated only where relevant
- [ ] `STATUS.md` Discoveries include the root cause, the chosen transport fix, and any skipped real-runtime verification rationale
- [ ] Delivery notes explain how a developer should retry IBKR market data after configuring ignored local `.env` values

## Documentation Requirements

**Must Update:**
- `.env.template` — update the committed gateway URL/scheme/defaults if the transport contract changes
- `.env.example` — keep synchronized with `.env.template` if present or restored as part of the committed environment-template contract
- `scripts/README.md` — document the working local iBeam URL/scheme and any self-signed-certificate/runtime caveats
- `docs/architecture/paper-trading-workspace.md` — update the iBeam session/connectivity contract and troubleshooting language
- `docs/architecture/provider-abstractions.md` — update provider-unavailable/authentication-required behavior if diagnostics or transport handling changes

**Check If Affected:**
- `README.md` — update if the current runtime surface or verification guidance changes
- `PLAN.md` — update if active queue/current plan wording is stale after this fix task
- `tasks/CONTEXT.md` — log follow-up technical debt or future task guidance discovered during the fix
- `docs/architecture/modules.md` — update if module ownership or AppHost/client responsibilities change
- `docs/INDEX.md` — update only if new active docs are introduced

## Completion Criteria

- [ ] Authenticated local iBeam refresh no longer fails due to the observed `Connection reset by peer` transport path
- [ ] Broker status and market-data provider share the same corrected iBeam transport behavior
- [ ] Missing, disabled, unauthenticated, and unreachable iBeam states still return safe provider/broker unavailable JSON without mock data fallback
- [ ] Any TLS/self-signed-certificate handling is narrowly scoped to local iBeam development traffic and covered by tests
- [ ] No secrets, account ids, tokens, cookies, session ids, or ignored `.env` values are read into the task packet, logs, docs, tests, or committed files
- [ ] Targeted tests/scripts and `dotnet test ATrade.slnx --nologo --verbosity minimal` pass, or unrelated pre-existing failures are documented with evidence
- [ ] Active docs/templates explain how to configure and retry local iBeam market data safely

## Git Commit Convention

Commits happen at **step boundaries** (not after every checkbox). All commits for this task MUST include the task ID for traceability:

- **Step completion:** `fix(TP-027): complete Step N — description`
- **Bug fixes:** `fix(TP-027): description`
- **Tests:** `test(TP-027): description`
- **Docs:** `docs(TP-027): description`
- **Hydration:** `hydrate: TP-027 expand Step N checkboxes`

## Do NOT

- Read, print, copy, or commit the ignored repo-root `.env` file
- Store or log real IBKR usernames, passwords, account identifiers, tokens, cookies, session ids, or local secret values
- Disable TLS certificate validation globally or for arbitrary remote hosts
- Introduce live trading, real order placement, or any broker-order path
- Reintroduce production mock market data or fallback symbol catalogs for IBKR unavailable states
- Change provider-neutral API/frontend payload shapes unless the active docs and tests are updated in the same change
- Break the repo-local startup contract (`./start run`, `./start.ps1 run`, `./start.cmd run`)

---

## Amendments (Added During Execution)

<!-- Workers add amendments here if issues discovered during execution.
     Format:
     ### Amendment N — YYYY-MM-DD HH:MM
     **Issue:** [what was wrong]
     **Resolution:** [what was changed] -->
