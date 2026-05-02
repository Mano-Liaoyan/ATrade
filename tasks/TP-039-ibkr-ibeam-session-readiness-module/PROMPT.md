# Task: TP-039 - Deepen the IBKR/iBeam session readiness module

**Created:** 2026-05-02
**Size:** L

## Review Level: 2 (Plan and Code)

**Assessment:** This task consolidates duplicate readiness trees used by broker status, market-data status, transport diagnostics, and worker monitoring. It touches safety-related IBKR/iBeam behavior but should preserve existing external states and avoid data model changes.
**Score:** 4/8 — Blast radius: 2, Pattern novelty: 1, Security: 1, Reversibility: 0

## Canonical Task Folder

```
tasks/TP-039-ibkr-ibeam-session-readiness-module/
├── PROMPT.md   ← This file (immutable above --- divider)
├── STATUS.md   ← Execution state (worker updates this)
├── .reviews/   ← Reviewer output (created by the orchestrator runtime)
└── .DONE       ← Created when complete
```

## Mission

Deepen the IBKR/iBeam session readiness module so broker status, market-data status, worker monitoring, and future paper-order work consume one normalized readiness result. This matters because the current implementation repeats integration-enabled checks, credential checks, paper-only guardrails, iBeam image/port validation, HTTPS transport handling, auth-status parsing, safe redaction, and status-to-error mapping in multiple modules.

## Dependencies

- **Task:** TP-038 (market-data read interface should be stable before changing the IBKR market-data adapter)

## Context to Read First

**Tier 2 (area context):**
- `tasks/CONTEXT.md`

**Tier 3 (load only if needed):**
- `docs/INDEX.md` — documentation discovery layer
- `docs/architecture/provider-abstractions.md` — broker and market-data provider seam rules
- `docs/architecture/modules.md` — Broker, IBKR adapter, MarketData, and worker module map
- `docs/architecture/paper-trading-workspace.md` — paper-only IBKR/iBeam safety states

## Environment

- **Workspace:** `src/ATrade.Brokers.Ibkr`, `src/ATrade.MarketData.Ibkr`, `workers/ATrade.Ibkr.Worker`
- **Services required:** None for unit tests; real iBeam checks must use ignored `.env` and skip cleanly when unavailable

## File Scope

- `src/ATrade.Brokers.Ibkr/IbkrBrokerStatusService.cs`
- `src/ATrade.Brokers.Ibkr/IbkrGatewayClient.cs`
- `src/ATrade.Brokers.Ibkr/IbkrGatewayTransport.cs`
- `src/ATrade.Brokers.Ibkr/IbkrGatewayOptions.cs`
- `src/ATrade.Brokers.Ibkr/IbkrPaperTradingGuard.cs`
- `src/ATrade.Brokers.Ibkr/*Readiness*.cs` (new if needed)
- `src/ATrade.MarketData.Ibkr/IbkrMarketDataProvider.cs`
- `src/ATrade.MarketData.Ibkr/IbkrMarketDataClient.cs`
- `workers/ATrade.Ibkr.Worker/IbkrWorkerShell.cs`
- `tests/ATrade.Brokers.Ibkr.Tests/IbkrSessionReadinessTests.cs` (new)
- `tests/ATrade.Brokers.Ibkr.Tests/*`
- `tests/ATrade.MarketData.Ibkr.Tests/*`
- `tests/apphost/ibeam-runtime-contract-tests.sh`
- `tests/apphost/ibkr-paper-safety-tests.sh`
- `tests/apphost/ibkr-market-data-provider-tests.sh`
- `docs/architecture/*`

## Steps

### Step 0: Preflight

- [ ] Required files and paths exist
- [ ] Dependencies satisfied

### Step 1: Create the shared IBKR/iBeam readiness interface

- [ ] Add an IBKR/iBeam readiness module in `ATrade.Brokers.Ibkr` that evaluates paper guard, integration, credentials, account id, iBeam image/port/url, local HTTPS transport, auth status, and safe diagnostics
- [ ] Add `tests/ATrade.Brokers.Ibkr.Tests/IbkrSessionReadinessTests.cs` covering disabled, credentials-missing, not-configured, configured-iBeam/unreachable, unauthenticated, authenticated, degraded/error, rejected-live, timeout, and redaction cases
- [ ] Preserve existing provider-neutral broker status values and safe messages
- [ ] Run targeted broker tests

**Artifacts:**
- `src/ATrade.Brokers.Ibkr/*Readiness*.cs` (new/modified)
- `tests/ATrade.Brokers.Ibkr.Tests/IbkrSessionReadinessTests.cs` (new)

### Step 2: Adapt broker, market-data, and worker callers

- [ ] Refactor `IbkrBrokerStatusService` to project the shared readiness result into `BrokerProviderStatus`
- [ ] Refactor `IbkrMarketDataProvider.GetStatus()` and request guards to project the same readiness result into `MarketDataProviderStatus` / `MarketDataError`
- [ ] Refactor `ATrade.Ibkr.Worker` monitoring to report readiness without re-implementing the readiness tree
- [ ] Run targeted broker, worker, and market-data tests

**Artifacts:**
- `src/ATrade.Brokers.Ibkr/IbkrBrokerStatusService.cs` (modified)
- `src/ATrade.MarketData.Ibkr/IbkrMarketDataProvider.cs` (modified)
- `workers/ATrade.Ibkr.Worker/IbkrWorkerShell.cs` (modified if needed)

### Step 3: Preserve transport, auth, and redaction safety

- [ ] Keep loopback HTTPS iBeam self-signed certificate handling scoped to local iBeam only
- [ ] Keep stable Client Portal user-agent behavior and content-length scanner requirements intact
- [ ] Ensure diagnostics never echo gateway URLs containing sensitive data, usernames, passwords, account ids, cookies, tokens, or sessions
- [ ] Run targeted iBeam runtime and paper-safety scripts

**Artifacts:**
- `src/ATrade.Brokers.Ibkr/IbkrGatewayTransport.cs` (modified if needed)
- `src/ATrade.MarketData.Ibkr/IbkrMarketDataClient.cs` (modified if needed)
- `tests/apphost/*ibkr*` (modified if needed)

### Step 4: Testing & Verification

> ZERO test failures allowed. This step runs the FULL test suite as a quality gate.

- [ ] Run FULL test suite: `dotnet test ATrade.slnx --nologo --verbosity minimal`
- [ ] Run integration tests if affected: `bash tests/apphost/ibkr-paper-safety-tests.sh`, `bash tests/apphost/ibeam-runtime-contract-tests.sh`, `bash tests/apphost/ibkr-market-data-provider-tests.sh`, `bash tests/apphost/ibkr-symbol-search-tests.sh`
- [ ] Fix all failures
- [ ] Build passes: `dotnet build ATrade.slnx --nologo --verbosity minimal`

### Step 5: Documentation & Delivery

- [ ] "Must Update" docs modified
- [ ] "Check If Affected" docs reviewed
- [ ] Discoveries logged in STATUS.md

## Documentation Requirements

**Must Update:**
- `docs/architecture/provider-abstractions.md` — shared IBKR/iBeam readiness seam if provider composition changes
- `docs/architecture/paper-trading-workspace.md` — readiness states and safety messages if changed
- `docs/architecture/modules.md` — Broker/IBKR/MarketData/worker module responsibilities if changed

**Check If Affected:**
- `README.md` — runtime surface summary if status behavior changes
- `scripts/README.md` — iBeam local runtime diagnostics if changed

## Completion Criteria

- [ ] All steps complete
- [ ] All tests passing
- [ ] Documentation updated
- [ ] Broker status, market-data status, and worker monitoring use one readiness model
- [ ] Existing provider-neutral status/error behavior remains compatible
- [ ] No secrets or account identifiers leak through logs, docs, tests, or payloads

## Git Commit Convention

Commits happen at **step boundaries** (not after every checkbox). All commits
for this task MUST include the task ID for traceability:

- **Step completion:** `feat(TP-039): complete Step N — description`
- **Bug fixes:** `fix(TP-039): description`
- **Tests:** `test(TP-039): description`
- **Hydration:** `hydrate: TP-039 expand Step N checkboxes`

## Do NOT

- Expand task scope — add tech debt to `tasks/CONTEXT.md` instead
- Skip tests
- Modify framework/standards docs without explicit user approval
- Load docs not listed in "Context to Read First"
- Commit without the task ID prefix in the commit message
- Add real order placement, live-trading behavior, credential persistence, or execution persistence
- Commit secrets, IBKR credentials, account identifiers, tokens, or session cookies
- Weaken loopback-only iBeam certificate handling or paper-only guardrails

---

## Amendments (Added During Execution)

<!-- Workers add amendments here if issues discovered during execution.
     Format:
     ### Amendment N — YYYY-MM-DD HH:MM
     **Issue:** [what was wrong]
     **Resolution:** [what was changed] -->
