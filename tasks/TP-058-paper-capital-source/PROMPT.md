# Task: TP-058 - Paper capital source

**Created:** 2026-05-05
**Size:** M

## Review Level: 2 (Plan and Code)

**Assessment:** This introduces account/cash behavior across the Accounts, IBKR broker adapter, API, Postgres-backed local state, tests, and docs. It is paper-safe and reversible, but touches account-adjacent data and must be reviewed for redaction and safety.
**Score:** 5/8 — Blast radius: 2, Pattern novelty: 1, Security: 1, Reversibility: 1

## Canonical Task Folder

```
tasks/TP-058-paper-capital-source/
├── PROMPT.md   ← This file (immutable above --- divider)
├── STATUS.md   ← Execution state (worker updates this)
├── .reviews/   ← Reviewer output (created by the orchestrator runtime)
└── .DONE       ← Created when complete
```

## Mission

Add a paper-capital source contract that backtesting can use for initial capital. The effective capital must prefer an authenticated IBKR/iBeam paper account balance when safely available, fall back to a user-configured local paper capital value persisted in Postgres, and report an explicit unavailable/unconfigured state when neither source exists. This task must not expose account identifiers, credentials, gateway URLs, tokens, or session details to the browser or logs.

## Dependencies

- **None**

## Context to Read First

**Tier 2 (area context):**
- `tasks/CONTEXT.md`

**Tier 3 (load only if needed):**
- `docs/INDEX.md` — documentation discovery layer
- `docs/architecture/paper-trading-workspace.md` — paper-only safety, account secrecy, and backend/API boundaries
- `docs/architecture/modules.md` — Accounts, Brokers.Ibkr, API, and Workspaces module responsibilities
- `docs/architecture/provider-abstractions.md` — provider state and redaction rules
- `README.md` — current runtime surface and verification entry points
- `PLAN.md` — active queue and solution-file contract

## Environment

- **Workspace:** `src/ATrade.Accounts`, `src/ATrade.Brokers.Ibkr`, `src/ATrade.Api`, `tests/`, active docs
- **Services required:** Postgres for local paper capital persistence. Real IBKR/iBeam is optional only through ignored local `.env`; automated tests must use fakes and must skip cleanly when real runtime is unavailable.

## File Scope

- `src/ATrade.Accounts/*`
- `src/ATrade.Brokers.Ibkr/*`
- `src/ATrade.Api/Program.cs`
- `src/ATrade.Api/ATrade.Api.csproj`
- `tests/ATrade.Accounts.Tests/*` (new)
- `tests/ATrade.Brokers.Ibkr.Tests/*`
- `tests/apphost/paper-capital-source-tests.sh` (new)
- `ATrade.slnx`
- `README.md`
- `PLAN.md`
- `docs/architecture/paper-trading-workspace.md`
- `docs/architecture/modules.md`
- `docs/architecture/provider-abstractions.md` (check if affected)

## Steps

> **Hydration:** STATUS.md tracks outcomes, not individual code changes. Workers
> expand steps when runtime discoveries warrant it. See task-worker agent for rules.

### Step 0: Preflight

- [ ] Required files and paths exist
- [ ] Dependencies satisfied

### Step 1: Add provider-neutral paper-capital contracts and local ledger persistence

- [ ] Create Accounts module contracts for effective paper capital, capital source (`ibkr-paper-balance`, `local-paper-ledger`, `unavailable`), local configured state, IBKR availability state, safe messages, and update requests
- [ ] Add a Postgres-backed local paper capital repository/schema initialized idempotently under the Accounts module, scoped to the same temporary local user/workspace pattern used by current workspace preferences
- [ ] Validate local paper capital updates server-side: positive amount, supported currency, no account ids/secrets, stable storage-unavailable error shape
- [ ] Create `tests/ATrade.Accounts.Tests` and cover local persistence, validation, unconfigured state, and response redaction

**Artifacts:**
- `src/ATrade.Accounts/*` (modified/new)
- `tests/ATrade.Accounts.Tests/*` (new)
- `ATrade.slnx` (modified)

### Step 2: Add safe IBKR/iBeam paper balance read seam

> ⚠️ Hydrate: Expand based on the existing `ATrade.Brokers.Ibkr` gateway transport/client patterns and the safest available Client Portal account summary/balance endpoint.

- [ ] Add a broker-adapter seam that attempts to read the configured paper account's cash/net-liquidation balance through the existing iBeam HTTPS transport only after readiness reports an authenticated paper session
- [ ] Ensure the configured paper account id is used only internally and never appears in API payloads, logs, errors, test snapshots, frontend source, or docs
- [ ] Map disabled, credentials-missing, unauthenticated, rejected-live, timeout, and provider failures into safe unavailable states with redacted messages
- [ ] Add unit tests/fakes in `tests/ATrade.Brokers.Ibkr.Tests` for authenticated balance, unavailable states, timeout/error redaction, and no leaked account identifiers

**Artifacts:**
- `src/ATrade.Brokers.Ibkr/*` (modified/new)
- `tests/ATrade.Brokers.Ibkr.Tests/*` (modified/new)

### Step 3: Expose paper-capital APIs through `ATrade.Api`

- [ ] Compose the new Accounts services in `AddAccountsModule(...)`, including configuration/Postgres dependencies needed by the local ledger
- [ ] Add `GET /api/accounts/paper-capital` returning `effectiveCapital`, `currency`, `source`, `ibkrAvailable`, `localConfigured`, `localCapital`, and safe messages without account ids
- [ ] Add `PUT /api/accounts/local-paper-capital` to set/update the local fallback capital; return the same effective-capital payload after update
- [ ] Add API projection tests/contract checks for HTTP status codes, validation failures, storage unavailable behavior, and no credential/account leakage

**Artifacts:**
- `src/ATrade.Accounts/*` (modified)
- `src/ATrade.Api/Program.cs` (modified)
- `src/ATrade.Api/ATrade.Api.csproj` (modified if needed)
- `tests/apphost/paper-capital-source-tests.sh` (new)

### Step 4: Testing & Verification

> ZERO test failures allowed. This step runs the FULL test suite as a quality gate.

- [ ] Run targeted Accounts tests: `dotnet test tests/ATrade.Accounts.Tests/ATrade.Accounts.Tests.csproj --nologo --verbosity minimal`
- [ ] Run targeted IBKR broker tests: `dotnet test tests/ATrade.Brokers.Ibkr.Tests/ATrade.Brokers.Ibkr.Tests.csproj --nologo --verbosity minimal`
- [ ] Run API/apphost contract validation: `bash tests/apphost/paper-capital-source-tests.sh`
- [ ] Run FULL test suite: `dotnet test ATrade.slnx --nologo --verbosity minimal`
- [ ] Fix all failures
- [ ] Build passes: `dotnet build ATrade.slnx --nologo --verbosity minimal`

### Step 5: Documentation & Delivery

- [ ] Update active docs to describe the paper-capital source contract, IBKR-first/local-ledger fallback, explicit unavailable state, and redaction guardrails
- [ ] Update README/PLAN current runtime and queued-work text if affected by the new account/capital surface or verification script
- [ ] "Check If Affected" docs reviewed
- [ ] Discoveries logged in STATUS.md, including the exact IBKR balance endpoint/shape used or why real-runtime smoke was skipped

## Documentation Requirements

**Must Update:**
- `docs/architecture/paper-trading-workspace.md` — account/capital ownership, local paper ledger fallback, IBKR balance safety, and API contract
- `docs/architecture/modules.md` — Accounts and Brokers.Ibkr responsibilities if new seams/classes are added
- `README.md` — current runtime surface and verification entry points if adding endpoints/tests
- `PLAN.md` — current plan/queue if affected

**Check If Affected:**
- `docs/architecture/provider-abstractions.md` — update only if broker capability/status text changes

## Completion Criteria

- [ ] All steps complete
- [ ] All tests passing
- [ ] Documentation updated
- [ ] `GET /api/accounts/paper-capital` prefers safe IBKR paper balance when authenticated and falls back to local Postgres paper capital when configured
- [ ] `PUT /api/accounts/local-paper-capital` persists a validated local fallback without secrets or account identifiers
- [ ] When neither source is available, the API reports an explicit unconfigured/unavailable state that downstream backtest creation can block on
- [ ] No response, log, frontend source, docs, or tests leak real account identifiers, credentials, gateway URLs, tokens, or session cookies

## Git Commit Convention

Commits happen at **step boundaries** (not after every checkbox). All commits
for this task MUST include the task ID for traceability:

- **Step completion:** `feat(TP-058): complete Step N — description`
- **Bug fixes:** `fix(TP-058): description`
- **Tests:** `test(TP-058): description`
- **Hydration:** `hydrate: TP-058 expand Step N checkboxes`

## Do NOT

- Expand task scope — add tech debt to `tasks/CONTEXT.md` instead
- Skip tests
- Modify framework/standards docs without explicit user approval
- Load docs not listed in "Context to Read First"
- Commit without the task ID prefix in the commit message
- Add order placement, order tickets, buy/sell controls, live-trading behavior, or broker execution behavior
- Expose account identifiers, usernames, passwords, gateway URLs, tokens, cookies, or session ids
- Treat placeholder `.env.template` account values as configured real paper accounts
- Add synthetic IBKR balances or fake provider success when iBeam is unavailable
- Add frontend UI beyond source/API contract checks in this task

---

## Amendments (Added During Execution)

<!-- Workers add amendments here if issues discovered during execution.
     Format:
     ### Amendment N — YYYY-MM-DD HH:MM
     **Issue:** [what was wrong]
     **Resolution:** [what was changed] -->
