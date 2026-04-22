# TP-004: Add Windows CI verification for `start run` — Status

**Current Step:** Step 4: Verification
**Status:** 🟡 In Progress
**Last Updated:** 2026-04-22
**Review Level:** 2
**Review Counter:** 0
**Iteration:** 1
**Size:** M

---

### Step 0: Preflight
**Status:** ✅ Complete

- [x] Read the startup-contract docs, wrapper files, and current Linux regression test
- [x] Confirm there is no existing Windows workflow for `start run`
- [x] Confirm `scripts/README.md` still documents Windows verification as an open gap

---

### Step 1: Add a Windows smoke harness
**Status:** ✅ Complete

- [x] Create `tests/start-contract/start-wrapper-windows.ps1`
- [x] Exercise `./start.ps1 run` and `./start.cmd run`
- [x] Detect successful startup without hanging indefinitely
- [x] Tear down launched processes cleanly with CI-friendly exit codes

---

### Step 2: Add GitHub Actions coverage
**Status:** ✅ Complete

- [x] Create `.github/workflows/windows-start-run.yml`
- [x] Use `windows-latest`
- [x] Install required .NET and Node toolchains
- [x] Run the PowerShell smoke harness in CI

---

### Step 3: Keep repo-local verification and docs in sync
**Status:** ✅ Complete

- [x] Update `tests/start-contract/start-wrapper-tests.sh`
- [x] Update `scripts/README.md`
- [x] Update `README.md` only if wording changed
- [x] Update active plan docs (`PLAN.md`, and `plans/devops/CURRENT.md` if wording changed) to reflect the completed Windows CI verification milestone

---

### Step 4: Verification
**Status:** 🟨 In Progress

- [ ] `bash tests/start-contract/start-wrapper-tests.sh`
- [ ] `grep -n "windows-latest\|start.ps1 run\|start.cmd run" .github/workflows/windows-start-run.yml tests/start-contract/start-wrapper-windows.ps1`
- [ ] Record that the durable deliverable is the checked-in Windows CI path

---

### Step 5: Delivery
**Status:** ⬜ Not Started

- [ ] Commit with conventions

---

## Reviews

| # | Type | Step | Verdict | File |
|---|------|------|---------|------|

---

## Discoveries

| Discovery | Disposition | Location |
|-----------|-------------|----------|

---

## Execution Log

| Timestamp | Action | Outcome |
|-----------|--------|---------|
| 2026-04-23 | Task staged | PROMPT.md and STATUS.md created |
| 2026-04-22 23:44 | Task started | Runtime V2 lane-runner execution |
| 2026-04-22 23:44 | Step 0 started | Preflight |

---

## Blockers

*None*

---

## Notes

*Goal: convert the documented Windows verification gap into a durable CI-backed check without changing the startup contract itself.*
