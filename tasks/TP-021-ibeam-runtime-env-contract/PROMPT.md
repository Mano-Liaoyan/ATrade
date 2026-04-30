# Task: TP-021 - Wire iBeam runtime and `.env` credential contract for IBKR API login

**Created:** 2026-04-29
**Size:** L

## Review Level: 3 (Full)

**Assessment:** This changes the broker runtime from a placeholder Gateway image to the user-approved `voyz/ibeam:latest` container and introduces credential-bearing environment variables that must remain ignored locally. It touches runtime orchestration, broker configuration, worker/API status redaction, tests, and documentation.
**Score:** 7/8 — Blast radius: 2, Pattern novelty: 1, Security: 2, Reversibility: 2

## Canonical Task Folder

```text
tasks/TP-021-ibeam-runtime-env-contract/
├── PROMPT.md   ← This file (immutable above --- divider)
├── STATUS.md   ← Execution state (worker updates this)
├── .reviews/   ← Reviewer output (created by the orchestrator runtime)
└── .DONE       ← Created when complete
```

## Mission

Replace the optional placeholder IBKR Gateway image/configuration with a real iBeam runtime contract using `voyz/ibeam:latest`, while keeping real credentials only in the ignored repo-root `.env`. The AppHost should be able to start an iBeam container when broker integration is enabled locally, map ATrade environment variables to the container variables required by iBeam, and keep the API/worker status surfaces safe and redacted. This task enables authenticated IBKR API access for later real market-data tasks; it must not place or route real orders.

## Dependencies

- **Task:** TP-019 (provider-neutral broker/market-data abstractions must exist first)

## Context to Read First

> Only load these files unless implementation reveals a directly related missing prerequisite.

**Tier 2 (area context):**
- `tasks/CONTEXT.md`

**Tier 3 (load only if needed):**
- `docs/architecture/provider-abstractions.md` — broker/provider seam from TP-019
- `docs/architecture/paper-trading-workspace.md` — current IBKR safety and secrets contract to update
- `docs/architecture/modules.md` — AppHost/API/worker/broker module boundaries
- `docs/architecture/overview.md` — AppHost resource graph and infrastructure authority
- `scripts/README.md` — local `.env` contract and startup rules
- `.env.template` — current committed env template
- `.gitignore` — confirm repo-root `.env` remains ignored
- `src/ATrade.AppHost/PaperTradingEnvironmentContract.cs` — current env-file loader
- `src/ATrade.AppHost/Program.cs` — current optional gateway container wiring
- `src/ATrade.Brokers.Ibkr/IbkrGatewayEnvironmentVariables.cs` — current broker env names
- `src/ATrade.Brokers.Ibkr/IbkrGatewayOptions.cs` — current broker options binding
- `src/ATrade.Brokers.Ibkr/IbkrBrokerStatusService.cs` — status/redaction behavior
- `workers/ATrade.Ibkr.Worker/*` — worker status/session flow
- `tests/apphost/ibkr-paper-safety-tests.sh` — current no-secrets/no-live guardrails
- `tests/apphost/apphost-worker-resource-wiring-tests.sh` — AppHost manifest/resource assertions

## Environment

- **Workspace:** Project root
- **Services required:** Automated tests must not require real IBKR credentials, iBeam login, or network access to IBKR. Optional manual verification may use a real ignored `.env`, `voyz/ibeam:latest`, and any required user-driven IBKR/iBeam 2FA steps.

## File Scope

> This task owns the iBeam/env runtime contract. Market-data endpoint replacement happens in TP-022.

- `.env.template`
- `.env.template` (new if absent)
- `.gitignore` (only if `.env` is not ignored)
- `src/ATrade.AppHost/PaperTradingEnvironmentContract.cs`
- `src/ATrade.AppHost/Program.cs`
- `src/ATrade.Brokers.Ibkr/IbkrGatewayEnvironmentVariables.cs`
- `src/ATrade.Brokers.Ibkr/IbkrGatewayOptions.cs`
- `src/ATrade.Brokers.Ibkr/IbkrGatewayContainerOptions.cs`
- `src/ATrade.Brokers.Ibkr/IbkrBrokerStatusService.cs`
- `workers/ATrade.Ibkr.Worker/*`
- `tests/apphost/ibeam-runtime-contract-tests.sh` (new)
- `tests/apphost/ibkr-paper-safety-tests.sh`
- `tests/apphost/apphost-worker-resource-wiring-tests.sh`
- `docs/architecture/paper-trading-workspace.md`
- `docs/architecture/modules.md`
- `docs/architecture/overview.md`
- `scripts/README.md`
- `README.md`

## Steps

> **Hydration:** STATUS.md tracks outcomes, not individual code changes. Workers expand steps when runtime discoveries warrant it.

### Step 0: Preflight

- [ ] Required files and paths exist
- [ ] Dependencies satisfied
- [ ] Confirm `.env` is ignored and no real credential-like values are committed
- [ ] Confirm the previous committed Gateway image is a placeholder before replacing the runtime contract
- [ ] Verify iBeam container environment variable names from the `voyz/ibeam` documentation or image metadata before hard-coding mappings

### Step 1: Update the committed environment templates without secrets

- [ ] Update `.env.template` with safe placeholders for iBeam/IBKR login and data access while keeping broker integration disabled by default
- [ ] Create or update `.env.template` as the user-facing copy template and canonical committed contract
- [ ] Include `ATRADE_IBKR_GATEWAY_IMAGE=voyz/ibeam:latest`, gateway URL/port, timeout, paper/live account-mode guard, and ATrade-owned placeholders for IBKR username/password/account id that belong only in ignored `.env`
- [ ] Ensure all credential placeholder values are obviously fake (`IBKR_USERNAME`, `IBKR_PASSWORD`, `IBKR_ACCOUNT_ID`) and no real account ids, usernames, passwords, session cookies, or tokens are committed
- [ ] Confirm `.gitignore` ignores repo-root `.env`; update only if missing

**Artifacts:**
- `.env.template` (modified)
- `.env.template` (new or modified)
- `.gitignore` (modified only if required)

### Step 2: Wire `voyz/ibeam:latest` into AppHost safely

- [ ] Update `PaperTradingEnvironmentContract` to load the new iBeam/IBKR credential variable names from environment or ignored `.env` while preserving safe defaults from committed templates
- [ ] Update `src/ATrade.AppHost/Program.cs` so the `ibkr-gateway` container uses `voyz/ibeam:latest` when broker integration is enabled and passes only the required iBeam environment variables to that container
- [ ] Do not print or expose credentials in resource names, status endpoints, logs, exception messages, or frontend-visible payloads
- [ ] Preserve the existing API, worker, Postgres, Redis, NATS, and frontend resource wiring
- [ ] Keep broker integration disabled by default when `.env` is absent; a missing real credential should produce a clear safe configuration status, not a live trading path
- [ ] Run targeted AppHost manifest/resource tests: `bash tests/apphost/apphost-worker-resource-wiring-tests.sh`

**Artifacts:**
- `src/ATrade.AppHost/PaperTradingEnvironmentContract.cs` (modified)
- `src/ATrade.AppHost/Program.cs` (modified)

### Step 3: Extend broker options, worker status, and redaction

- [ ] Add typed broker options/env constants for the ATrade-owned iBeam credential variables and any verified iBeam container mappings
- [ ] Update the broker status service and worker so they can distinguish disabled, credentials-missing, iBeam-container-configured, connecting, authenticated, degraded, and error states without leaking secrets
- [ ] Keep account mode constrained to safe paper/data behavior; no real-order capability may become enabled by these environment variables
- [ ] Update tests so live-mode/rejected-mode and redaction checks cover the new credential-bearing env names
- [ ] Run targeted tests: `dotnet test tests/ATrade.Brokers.Ibkr.Tests/ATrade.Brokers.Ibkr.Tests.csproj --nologo --verbosity minimal && bash tests/apphost/ibkr-paper-safety-tests.sh`

**Artifacts:**
- `src/ATrade.Brokers.Ibkr/IbkrGatewayEnvironmentVariables.cs` (modified)
- `src/ATrade.Brokers.Ibkr/IbkrGatewayOptions.cs` (modified)
- `src/ATrade.Brokers.Ibkr/IbkrGatewayContainerOptions.cs` (modified)
- `src/ATrade.Brokers.Ibkr/IbkrBrokerStatusService.cs` (modified)
- `workers/ATrade.Ibkr.Worker/*` (modified if status behavior changes)
- `tests/ATrade.Brokers.Ibkr.Tests/*` (modified)
- `tests/apphost/ibkr-paper-safety-tests.sh` (modified)

### Step 4: Add iBeam runtime contract verification

- [ ] Create `tests/apphost/ibeam-runtime-contract-tests.sh`
- [ ] Verify committed env templates include `voyz/ibeam:latest`, safe placeholders, and no credential-like real values
- [ ] Verify `.env.template` contains the canonical safe placeholders
- [ ] Verify AppHost references the iBeam image and does not require credentials for normal test startup/default disabled mode
- [ ] Verify API/worker status payloads never include username, password, token, session cookie, or raw account id values
- [ ] Run targeted test: `bash tests/apphost/ibeam-runtime-contract-tests.sh`

**Artifacts:**
- `tests/apphost/ibeam-runtime-contract-tests.sh` (new)

### Step 5: Update runtime and safety documentation

- [ ] Update `scripts/README.md` with the ignored `.env` flow, `.env.template` contract, iBeam startup instructions, and secret-handling rules
- [ ] Update `docs/architecture/paper-trading-workspace.md` to record that the user-approved local IBKR data runtime is `voyz/ibeam:latest` while no-real-orders guardrails remain in force
- [ ] Update `docs/architecture/modules.md` and `docs/architecture/overview.md` if AppHost/API/worker current-state notes change
- [ ] Update `README.md` only if current-status or run-contract text would otherwise be stale

**Artifacts:**
- `scripts/README.md` (modified)
- `docs/architecture/paper-trading-workspace.md` (modified)
- `docs/architecture/modules.md` (modified)
- `docs/architecture/overview.md` (modified if affected)
- `README.md` (modified if affected)

### Step 6: Testing & Verification

> ZERO test failures allowed. This step runs the full available repository verification suite as the quality gate.

- [ ] Run FULL test suite: `dotnet test ATrade.sln --nologo --verbosity minimal && bash tests/start-contract/start-wrapper-tests.sh && bash tests/scaffolding/project-shells-tests.sh && bash tests/apphost/api-bootstrap-tests.sh && bash tests/apphost/accounts-feature-bootstrap-tests.sh && bash tests/apphost/ibkr-paper-safety-tests.sh && bash tests/apphost/ibeam-runtime-contract-tests.sh && bash tests/apphost/market-data-feature-tests.sh && bash tests/apphost/provider-abstraction-contract-tests.sh && bash tests/apphost/postgres-watchlist-persistence-tests.sh && bash tests/apphost/frontend-nextjs-bootstrap-tests.sh && bash tests/apphost/frontend-trading-workspace-tests.sh && bash tests/apphost/apphost-infrastructure-manifest-tests.sh && bash tests/apphost/apphost-worker-resource-wiring-tests.sh && bash tests/apphost/local-port-contract-tests.sh && bash tests/apphost/paper-trading-config-contract-tests.sh && bash tests/apphost/apphost-infrastructure-runtime-tests.sh`
- [ ] Confirm Docker-dependent runtime tests pass or cleanly skip when no Docker-compatible engine or real iBeam credentials are available
- [ ] Fix all failures
- [ ] Solution build passes: `dotnet build ATrade.sln --nologo --verbosity minimal`

### Step 7: Documentation & Delivery

- [ ] "Must Update" docs modified
- [ ] "Check If Affected" docs reviewed
- [ ] Discoveries logged in STATUS.md

## Documentation Requirements

**Must Update:**
- `scripts/README.md` — document `.env`, `.env.template`, iBeam, and secret-handling startup flow
- `docs/architecture/paper-trading-workspace.md` — update the IBKR data runtime and safety contract
- `.env.template` — expose safe placeholders only

**Check If Affected:**
- `docs/architecture/modules.md` — update if API/worker/broker current state changes
- `docs/architecture/overview.md` — update if AppHost resource graph changes materially
- `README.md` — update if current status or run instructions become stale
- `docs/INDEX.md` — update only if new indexed docs are added (none expected)

## Completion Criteria

- [ ] `voyz/ibeam:latest` is the configured local IBKR Gateway/iBeam image in committed templates and AppHost wiring
- [ ] Real IBKR login values are read only from ignored `.env`/environment and are never committed or surfaced
- [ ] API/worker status can report iBeam configuration/authentication state safely and redacted
- [ ] Tests prove template safety, secret redaction, disabled-by-default behavior, and AppHost container wiring
- [ ] Active docs explain how to configure real IBKR API login through `.env` without enabling real order placement

## Git Commit Convention

Commits happen at **step boundaries** (not after every checkbox). All commits for this task MUST include the task ID for traceability:

- **Step completion:** `feat(TP-021): complete Step N — description`
- **Bug fixes:** `fix(TP-021): description`
- **Tests:** `test(TP-021): description`
- **Hydration:** `hydrate: TP-021 expand Step N checkboxes`

## Do NOT

- Commit real IBKR usernames, passwords, account ids, session cookies, tokens, or gateway URLs tied to a real account
- Print secrets in logs, status payloads, frontend code, test output, docs, or exception messages
- Enable live trading or real order placement
- Assume iBeam variable names without verifying them against the image/documentation
- Replace market-data endpoints with IBKR data in this task; that is TP-022
- Load docs not listed in "Context to Read First" unless a missing prerequisite is discovered and recorded

---

## Amendments (Added During Execution)

<!-- Workers add amendments here if issues discovered during execution.
     Format:
     ### Amendment N — YYYY-MM-DD HH:MM
     **Issue:** [what was wrong]
     **Resolution:** [what was changed] -->
