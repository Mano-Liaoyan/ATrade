# Task: TP-032 - Make Aspire dashboard port configurable from .env

**Created:** 2026-04-30
**Size:** M

## Review Level: 1 (Plan Only)

**Assessment:** This adapts the existing local port contract and cross-platform start wrappers for one additional AppHost/Aspire dashboard binding. It touches startup scripts and tests across Unix/Windows, but follows existing configuration patterns and has no durable data model or auth impact.
**Score:** 3/8 — Blast radius: 1, Pattern novelty: 1, Security: 0, Reversibility: 1

## Canonical Task Folder

```text
tasks/TP-032-configurable-aspire-dashboard-port/
├── PROMPT.md   ← This file (immutable above --- divider)
├── STATUS.md   ← Execution state (worker updates this)
├── .reviews/   ← Reviewer output (created by the orchestrator runtime)
└── .DONE       ← Created when complete
```

## Mission

Make the Aspire dashboard HTTP port configurable through the repo-level `.env` contract while preserving the existing `start run` behavior across Unix and Windows. Defaults should remain safe for local development (ephemeral/loopback unless the user opts into a fixed port), and the committed `.env.template` must document the new non-secret setting.

## Dependencies

- **None**

## Context to Read First

> Only load these files unless implementation reveals a directly related missing prerequisite. Do **not** read, print, or commit the ignored repo-root `.env` file.

**Tier 2 (area context):**
- `tasks/CONTEXT.md`

**Tier 3 (load only if needed):**
- `scripts/README.md` — current local `.env`/start-run contract
- `.env.template` — committed local port contract defaults (template only; never read ignored `.env`)
- `scripts/start.run.sh` and `scripts/start.run.ps1` — cross-platform AppHost startup wrappers
- `scripts/local-env.sh` — Unix `.env` loader pattern
- `src/ATrade.ServiceDefaults/LocalDevelopmentPortContract.cs` — local port contract parser used by AppHost/API/frontend
- `src/ATrade.AppHost/Properties/launchSettings.json` — current Aspire dashboard/OTLP launch defaults
- `src/ATrade.AppHost/Program.cs` — AppHost startup path if contract loader changes are needed
- `tests/start-contract/start-wrapper-tests.sh` and `tests/start-contract/start-wrapper-windows.ps1` — cross-platform wrapper checks
- `tests/apphost/local-port-contract-tests.sh` — `.env` override coverage
- `tests/apphost/frontend-nextjs-bootstrap-tests.sh` and `tests/apphost/apphost-infrastructure-manifest-tests.sh` — AppHost manifest/runtime checks affected by startup env
- `tests/apphost/paper-trading-config-contract-tests.sh` — `.env.template` contract assertions

## Environment

- **Workspace:** Repository root
- **Services required:** Tests should avoid requiring a long-running AppHost where possible. Any runtime smoke should use a temporary loopback port and clean up processes.

## File Scope

> The orchestrator uses this to avoid merge conflicts. Keep changes inside this scope unless `STATUS.md` records a discovered prerequisite.

- `.env.template`
- `scripts/local-env.sh`
- `scripts/local-env.ps1` (new if needed for PowerShell parity)
- `scripts/start.run.sh`
- `scripts/start.run.ps1`
- `src/ATrade.ServiceDefaults/LocalDevelopmentPortContract.cs`
- `src/ATrade.AppHost/Properties/launchSettings.json` (only if launch defaults must change; prefer preserving safe `0` defaults)
- `src/ATrade.AppHost/Program.cs` (only if AppHost code must consume the setting directly)
- `tests/start-contract/start-wrapper-tests.sh`
- `tests/start-contract/start-wrapper-windows.ps1`
- `tests/apphost/local-port-contract-tests.sh`
- `tests/apphost/frontend-nextjs-bootstrap-tests.sh`
- `tests/apphost/apphost-infrastructure-manifest-tests.sh`
- `tests/apphost/paper-trading-config-contract-tests.sh`
- `scripts/README.md`
- `README.md` (only if user-facing startup summary changes)
- `docs/architecture/overview.md` (only if AppHost config summary changes)
- `tasks/TP-032-configurable-aspire-dashboard-port/STATUS.md`

## Steps

> **Hydration:** STATUS.md tracks outcomes, not individual code changes. Workers expand steps when runtime discoveries warrant it.

### Step 0: Preflight and naming decision

- [ ] Inspect how the Aspire dashboard currently binds via `ASPNETCORE_URLS` and `ASPIRE_DASHBOARD_OTLP_ENDPOINT_URL` in `launchSettings.json`
- [ ] Choose and record the committed `.env` variable name in `STATUS.md`; prefer `ATRADE_ASPIRE_DASHBOARD_HTTP_PORT` for the dashboard UI port
- [ ] Decide whether OTLP remains ephemeral (`ASPIRE_DASHBOARD_OTLP_ENDPOINT_URL=http://127.0.0.1:0`) or needs a separate optional variable; do not add extra variables unless required by Aspire runtime evidence
- [ ] Confirm the default should preserve current ephemeral dashboard behavior, e.g. `ATRADE_ASPIRE_DASHBOARD_HTTP_PORT=0`, while allowing a non-zero fixed local port in ignored `.env`

**Artifacts:**
- `tasks/TP-032-configurable-aspire-dashboard-port/STATUS.md` (modified)

### Step 1: Extend the local port contract

- [ ] Add `ATRADE_ASPIRE_DASHBOARD_HTTP_PORT=0` (or the chosen name/default) to `.env.template` with comments explaining that `0` means ephemeral and a non-zero value fixes the dashboard UI port
- [ ] Extend `LocalDevelopmentPortContract` and its loader to parse the optional dashboard port, allowing `0` for ephemeral and `1..65535` for fixed ports
- [ ] Preserve existing required port validation for API, direct frontend, and AppHost frontend ports
- [ ] Add/update tests that validate default `0`, fixed non-zero, invalid text, and out-of-range dashboard port values
- [ ] Keep the variable non-secret and independent from broker/IBKR settings

**Artifacts:**
- `.env.template` (modified)
- `src/ATrade.ServiceDefaults/LocalDevelopmentPortContract.cs` (modified)
- `tests/start-contract/start-wrapper-tests.sh` or equivalent contract tests (modified)
- `tests/apphost/paper-trading-config-contract-tests.sh` (modified)

### Step 2: Apply the dashboard port in Unix and Windows start wrappers

- [ ] Update `scripts/start.run.sh` so `./start run` exports `ASPNETCORE_URLS=http://127.0.0.1:<ATRADE_ASPIRE_DASHBOARD_HTTP_PORT>` when the configured dashboard port is non-zero, and preserves `http://127.0.0.1:0` when it is `0` or absent
- [ ] Update `scripts/start.run.ps1` with equivalent `.env` loading and dashboard-port export behavior so Windows PowerShell and Command Prompt paths match Unix semantics
- [ ] Add a PowerShell local env loader (`scripts/local-env.ps1`) or equivalent shared parsing logic if needed; it must prefer ignored `.env` over `.env.template` and must not print secrets
- [ ] Preserve existing pass-through arguments, missing-dotnet/missing-project errors, and `start.cmd` delegation behavior
- [ ] Keep `ASPIRE_DASHBOARD_OTLP_ENDPOINT_URL` on its safe existing default unless Step 0 found evidence that it also must be configurable

**Artifacts:**
- `scripts/start.run.sh` (modified)
- `scripts/start.run.ps1` (modified)
- `scripts/local-env.sh` (modified only if needed)
- `scripts/local-env.ps1` (new if needed)
- `tests/start-contract/start-wrapper-tests.sh` (modified)
- `tests/start-contract/start-wrapper-windows.ps1` (modified if Windows smoke needs new expectations)

### Step 3: Add configuration and runtime regression coverage

- [ ] Update `tests/apphost/local-port-contract-tests.sh` to write a temporary `.env` with a non-zero dashboard port and verify the start/AppHost path honors it without breaking API/frontend port overrides
- [ ] Update start-wrapper tests to assert the new variable exists in `.env.template`, the wrappers load the local contract, and `launchSettings.json` keeps safe loopback defaults
- [ ] Add a bounded smoke check that starts AppHost with a temporary dashboard port and verifies the process listens/reports that port, if feasible without making tests flaky
- [ ] Update Windows wrapper smoke expectations only if the new PowerShell env loader changes observable output or required setup
- [ ] Run targeted startup/config tests

**Artifacts:**
- `tests/apphost/local-port-contract-tests.sh` (modified)
- `tests/start-contract/start-wrapper-tests.sh` (modified)
- `tests/start-contract/start-wrapper-windows.ps1` (modified if needed)
- `tests/apphost/frontend-nextjs-bootstrap-tests.sh` (modified only if startup expectations change)
- `tests/apphost/apphost-infrastructure-manifest-tests.sh` (modified only if manifest expectations change)

### Step 4: Testing & Verification

> ZERO unexpected test failures allowed.

- [ ] Run `bash tests/start-contract/start-wrapper-tests.sh`
- [ ] Run `bash tests/apphost/local-port-contract-tests.sh`
- [ ] Run `bash tests/apphost/paper-trading-config-contract-tests.sh`
- [ ] Run `bash tests/apphost/frontend-nextjs-bootstrap-tests.sh`
- [ ] Run `bash tests/apphost/apphost-infrastructure-manifest-tests.sh`
- [ ] Run FULL test suite: `dotnet test ATrade.slnx --nologo --verbosity minimal`
- [ ] Run solution build: `dotnet build ATrade.slnx --nologo --verbosity minimal`
- [ ] Fix all failures or record pre-existing unrelated failures with evidence in `STATUS.md`

### Step 5: Documentation & Delivery

- [ ] "Must Update" docs describe `ATRADE_ASPIRE_DASHBOARD_HTTP_PORT`, the `0`/ephemeral default, and how to set a fixed dashboard port in ignored `.env`
- [ ] "Check If Affected" docs reviewed and updated only where relevant
- [ ] `STATUS.md` Discoveries record the final variable name, default behavior, and any OTLP decision

## Documentation Requirements

**Must Update:**
- `.env.template` — add the dashboard port variable and comments
- `scripts/README.md` — document dashboard port configuration alongside other local port variables

**Check If Affected:**
- `README.md` — update only if startup/run-contract wording changes
- `docs/architecture/overview.md` — update only if AppHost/dashboard configuration summary changes
- `docs/INDEX.md` — update only if new active docs are introduced

## Completion Criteria

- [ ] A committed `.env.template` setting controls the Aspire dashboard UI port, with default behavior preserving ephemeral local binding
- [ ] `./start run`, `./start.ps1 run`, and `./start.cmd run` honor a non-zero dashboard port from ignored `.env`
- [ ] Existing API/frontend local port settings and AppHost frontend port behavior still work
- [ ] Tests cover default, fixed, and invalid dashboard port configuration
- [ ] Documentation explains the setting and keeps secrets out of committed files

## Git Commit Convention

Commits happen at **step boundaries** (not after every checkbox). All commits for this task MUST include the task ID for traceability:

- **Step completion:** `feat(TP-032): complete Step N — description`
- **Bug fixes:** `fix(TP-032): description`
- **Tests:** `test(TP-032): description`
- **Hydration:** `hydrate: TP-032 expand Step N checkboxes`

## Do NOT

- Break the `start run` contract on Unix or Windows
- Require a fixed dashboard port by default; preserve safe local ephemeral behavior unless ignored `.env` opts in
- Print or commit ignored `.env` values, broker credentials, tokens, or secrets
- Change frontend/API ports except through their existing variables
- Skip tests or commit without the task ID prefix

---

## Amendments (Added During Execution)

<!-- Workers add amendments here if issues discovered during execution.
     Format:
     ### Amendment N — YYYY-MM-DD HH:MM
     **Issue:** [what was wrong]
     **Resolution:** [what was changed] -->
