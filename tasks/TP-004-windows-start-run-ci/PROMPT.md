# Task: TP-004 — Add Windows CI verification for `start run`

**Created:** 2026-04-23
**Size:** M

## Review Level: 2 (Moderate)

**Assessment:** Adds GitHub Actions automation plus a Windows-specific smoke
harness for the repo-local startup wrappers. This changes CI/workflow behavior
and verification docs, but does not change product logic or introduce new
runtime features.
**Score:** 4/8 — Blast radius: 2, Pattern novelty: 1, Security: 0, Reversibility: 1

## Canonical Task Folder

```text
tasks/TP-004-windows-start-run-ci/
├── PROMPT.md   ← This file (immutable above --- divider)
├── STATUS.md   ← Execution state (worker updates this)
├── .reviews/   ← Reviewer output (task-runner creates this)
└── .DONE       ← Created when complete
```

## Mission

Close the documented Windows verification gap for the repo-local startup
contract by adding a repeatable **Windows-hosted CI path** that exercises both
`./start.ps1 run` and `./start.cmd run`.

The repo currently documents Windows wrapper support but explicitly says the
wrappers still need Windows-hosted verification. This task should turn that gap
into durable repository automation instead of relying on a one-off manual check.

## Scope

Deliver one repeatable verification path:

1. Add a repo-local PowerShell smoke harness under `tests/start-contract/`
   that exercises both Windows entrypoints.
2. Add a GitHub Actions workflow on `windows-latest` that runs that harness.
3. Keep the existing Linux regression checks in sync with the new CI assets.
4. Update the active docs so they describe the new Windows verification path
   accurately.

This task is about **verification automation**, not about redesigning the
startup contract.

## Dependencies

- **None**

## Context to Read First

- `README.md`
- `PLAN.md`
- `AGENTS.md`
- `docs/INDEX.md`
- `scripts/README.md`
- `start.ps1`
- `start.cmd`
- `scripts/start.run.ps1`
- `tests/start-contract/start-wrapper-tests.sh`
- `src/ATrade.AppHost/Program.cs`

## Environment

- **Workspace:** Project root
- **Services required:** None before implementation; CI workflow is part of the deliverable

## File Scope

- `.github/workflows/windows-start-run.yml` (new)
- `tests/start-contract/start-wrapper-windows.ps1` (new)
- `tests/start-contract/start-wrapper-tests.sh`
- `scripts/README.md`
- `README.md` (if verification wording changes)
- `plans/devops/CURRENT.md` (if affected)

## Steps

### Step 0: Preflight

- [ ] Read the startup-contract docs, wrapper files, and current Linux regression test
- [ ] Confirm there is no existing Windows workflow for `start run`
- [ ] Confirm `scripts/README.md` still documents Windows verification as an open gap

### Step 1: Add a Windows smoke harness

- [ ] Create `tests/start-contract/start-wrapper-windows.ps1`
- [ ] Exercise `./start.ps1 run` and `./start.cmd run` from the repo root
- [ ] Detect successful startup of the AppHost-managed graph without hanging the CI job indefinitely
- [ ] Shut down or tear down the launched process(es) cleanly and return CI-friendly exit codes

### Step 2: Add GitHub Actions coverage

- [ ] Create `.github/workflows/windows-start-run.yml`
- [ ] Use a Windows-hosted runner (`windows-latest`)
- [ ] Install the required .NET and Node toolchains needed for the current AppHost graph
- [ ] Run the new PowerShell smoke harness in CI

### Step 3: Keep repo-local verification and docs in sync

- [ ] Update `tests/start-contract/start-wrapper-tests.sh` so the Linux regression suite asserts the new Windows CI assets exist and reference the expected wrapper commands
- [ ] Update `scripts/README.md` so Windows verification is described as CI-backed rather than a missing gap
- [ ] Update `README.md` only if its verification wording becomes inaccurate

### Step 4: Verification

- [ ] `bash tests/start-contract/start-wrapper-tests.sh`
- [ ] `grep -n "windows-latest\|start.ps1 run\|start.cmd run" .github/workflows/windows-start-run.yml tests/start-contract/start-wrapper-windows.ps1`
- [ ] Do **not** claim a successful Windows execution from the Linux task environment; the durable deliverable is the checked-in CI path

### Step 5: Delivery

- [ ] Commit with the conventions below

## Documentation Requirements

**Must Update:** `scripts/README.md`
**Check If Affected:** `README.md`, `plans/devops/CURRENT.md`

## Completion Criteria

- [ ] A Windows-hosted GitHub Actions workflow exists for `start run`
- [ ] A repo-local PowerShell smoke harness exercises both Windows wrappers
- [ ] The Linux wrapper regression test asserts the new CI assets exist
- [ ] Active docs accurately describe the Windows verification path

## Git Commit Convention

- **Implementation:** `ci(TP-004): description`
- **Checkpoints:** `checkpoint: TP-004 description`

## Do NOT

- Change the meaning of `start run`
- Add new repo-local startup subcommands
- Rework the Linux wrapper behavior unless required for the Windows verification path
- Claim the Windows wrappers were manually verified outside the checked-in CI flow

---

## Amendments (Added During Execution)

<!-- Workers add amendments here if issues discovered during execution. -->
