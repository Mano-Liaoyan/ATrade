# Task: TP-012 — Externalize local port allocation into a repo `.env` contract

**Created:** 2026-04-24
**Size:** M

## Review Level: 2 (Moderate)

**Assessment:** This task centralizes local port allocation for the Aspire-managed
bootstrap stack into environment-driven configuration instead of scattered
literals. It changes local startup/config/test behavior, but does not add domain
logic.
**Score:** 4/8 — Blast radius: 2, Pattern novelty: 1, Security: 0, Reversibility: 1

## Canonical Task Folder

```text
tasks/TP-012-externalize-local-port-allocation/
├── PROMPT.md   ← This file (immutable above --- divider)
├── STATUS.md   ← Execution state (worker updates this)
├── .reviews/   ← Reviewer output (task-runner creates this)
└── .DONE       ← Created when complete
```

## Mission

Fix the local port-allocation contract by externalizing the operator-facing port
settings into a repo-level `.env` contract instead of leaving port choices
scattered across AppHost code, launch settings, and test scripts.

The operator explicitly asked to put the ports into a `.env` file to fix port
allocation. Implement that request in the correct way:

- centralize the ports that developers/operators need to control
- keep the AppHost / tests reading from the same source of truth
- do **not** blindly move every literal port into `.env` if the value is a
  protocol-internal target port or intentionally ephemeral system port

This task must solve the real configuration problem, not just add another file
that nobody reads.

## Scope

Deliver a durable env-driven port contract for local development:

1. Inventory the current port usage across AppHost, launch settings, and test
   harnesses.
2. Create a repo-level `.env` contract for developer-controlled local ports
   (and a committed template such as `.env.template` if that is the safest shape).
3. Update AppHost and related test harnesses to read from that env contract.
4. Keep protocol-internal/default container ports where they belong unless there
   is a real reason to externalize them.
5. Preserve sensible fallbacks so the repo still boots in a clean environment.
6. Add verification that demonstrates the same `.env` contract actually drives
   the local runtime/test paths.

## Dependencies

- **TP-010** and **TP-011** should be integrated first, because this task edits
  the same AppHost/runtime surface and should build on the latest frontend and
  infra startup fixes.

## Context to Read First

- `README.md`
- `PLAN.md`
- `AGENTS.md`
- `tasks/CONTEXT.md`
- `scripts/README.md`
- `src/ATrade.AppHost/Program.cs`
- `src/ATrade.AppHost/Properties/launchSettings.json`
- `tests/apphost/api-bootstrap-tests.sh`
- `tests/apphost/frontend-nextjs-bootstrap-tests.sh`
- `tests/apphost/apphost-infrastructure-manifest-tests.sh`
- `tests/apphost/apphost-infrastructure-runtime-tests.sh`
- `.gitignore`

## Observed Current State

Current hard-coded or semi-hard-coded port usage includes examples like:

- AppHost frontend target port `3000`
- API direct-start test port `5181`
- frontend direct-start test port `3111`
- AppHost launch settings using ephemeral `127.0.0.1:0` for internal host/dashboard endpoints
- infra manifest expectations for container/service ports such as `5432`, `6379`, and `4222`

The implementation must distinguish between:

1. **operator-controlled local bind ports** that belong in the `.env` contract
2. **protocol/service target ports** that may stay fixed by design
3. **intentionally ephemeral internal ports** that should remain dynamic

## Environment

- **Workspace:** Project root
- **Services required:** none for implementation; runtime verification may use the local engine when available

## File Scope

- `src/ATrade.AppHost/Program.cs`
- `src/ATrade.AppHost/Properties/launchSettings.json` (only if the right solution requires it)
- `.env.template` or equivalent committed template (new)
- `.gitignore` (if a developer-local `.env` file should be ignored)
- `tests/apphost/api-bootstrap-tests.sh`
- `tests/apphost/frontend-nextjs-bootstrap-tests.sh`
- `tests/apphost/apphost-infrastructure-manifest-tests.sh`
- `tests/apphost/apphost-infrastructure-runtime-tests.sh`
- `scripts/README.md`
- `README.md` / `PLAN.md` only if wording would otherwise become inaccurate

## Steps

### Step 0: Preflight

- [ ] Inventory current port literals and categorize them as bind-port, service-target-port, or intentionally ephemeral
- [ ] Confirm whether a repo `.env` contract already exists (it currently does not)
- [ ] Confirm how AppHost and tests currently obtain their ports

### Step 1: Define the `.env` contract

- [ ] Choose the correct committed shape (`.env.template` or equivalent) plus developer-local file behavior
- [ ] Define clear variable names for the ports developers are expected to control
- [ ] Keep intentionally ephemeral internal ports dynamic unless there is a real product reason to pin them
- [ ] Document fallback behavior when the `.env` file is absent

### Step 2: Wire AppHost and startup paths to the env contract

- [ ] Update AppHost/startup code to read the env-driven port values
- [ ] Ensure the frontend/AppHost and infra/runtime paths use the centralized contract where appropriate
- [ ] Do not regress the recent `NODE_ENV`, Turbopack-root, or container-runtime fixes

### Step 3: Wire tests to the same source of truth

- [ ] Update direct-start and AppHost-related test harnesses so they read the same env contract or a shared helper
- [ ] Remove duplicated port assumptions where the env contract should now drive behavior
- [ ] Keep tests deterministic in CI

### Step 4: Verification

- [ ] Add or update verification to prove the `.env` contract is actually consumed
- [ ] Verify direct API/frontend startup still works
- [ ] Verify AppHost manifest/runtime checks still pass with the env-driven configuration
- [ ] Include at least one assertion that changing the configured env port is reflected in the relevant startup/test path

### Step 5: Documentation

- [ ] Update `scripts/README.md` with the local port contract
- [ ] Update `README.md` only if operator-facing startup guidance changes materially
- [ ] Update `PLAN.md` only if milestone/current-state wording would otherwise be stale

### Step 6: Final verification

- [ ] Run the affected tests
- [ ] Confirm the repo remains runnable with defaults
- [ ] Confirm the new `.env` contract is the single source of truth for developer-controlled local port allocation

### Step 7: Delivery

- [ ] Commit with the conventions below

## Documentation Requirements

**Must Update:** `scripts/README.md`
**Check If Affected:** `README.md`, `PLAN.md`

## Completion Criteria

- [ ] A repo-level `.env` contract exists for developer-controlled local ports
- [ ] AppHost and relevant tests use that contract instead of scattered duplicated literals
- [ ] Intentionally dynamic/internal ports are not incorrectly frozen just for the sake of consistency
- [ ] Verification proves the env contract is real and used

## Git Commit Convention

- **Implementation:** `fix(TP-012): description`
- **Checkpoints:** `checkpoint: TP-012 description`

## Do NOT

- Dump every port literal into `.env` without understanding whether it is a bind port, service target port, or intentionally ephemeral internal port
- Break the current AppHost runtime fixes from TP-010 / TP-011
- Introduce machine-specific values with no fallback/default behavior
- Leave tests reading stale hard-coded ports while production code reads `.env`

---

## Amendments (Added During Execution)

<!-- Workers add amendments here if issues discovered during execution. -->
