# TP-004: Add Windows CI verification for `start run` — Status

**Current Step:** Not Started
**Status:** 🔵 Ready for Execution
**Last Updated:** 2026-04-23
**Review Level:** 2
**Review Counter:** 0
**Iteration:** 0
**Size:** M

---

### Step 0: Preflight
**Status:** ⬜ Not Started

- [ ] Read the startup-contract docs, wrapper files, and current Linux regression test
- [ ] Confirm there is no existing Windows workflow for `start run`
- [ ] Confirm `scripts/README.md` still documents Windows verification as an open gap

---

### Step 1: Add a Windows smoke harness
**Status:** ⬜ Not Started

- [ ] Create `tests/start-contract/start-wrapper-windows.ps1`
- [ ] Exercise `./start.ps1 run` and `./start.cmd run`
- [ ] Detect successful startup without hanging indefinitely
- [ ] Tear down launched processes cleanly with CI-friendly exit codes

---

### Step 2: Add GitHub Actions coverage
**Status:** ⬜ Not Started

- [ ] Create `.github/workflows/windows-start-run.yml`
- [ ] Use `windows-latest`
- [ ] Install required .NET and Node toolchains
- [ ] Run the PowerShell smoke harness in CI

---

### Step 3: Keep repo-local verification and docs in sync
**Status:** ⬜ Not Started

- [ ] Update `tests/start-contract/start-wrapper-tests.sh`
- [ ] Update `scripts/README.md`
- [ ] Update `README.md` only if wording changed

---

### Step 4: Verification
**Status:** ⬜ Not Started

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

---

## Blockers

*None*

---

## Notes

*Goal: convert the documented Windows verification gap into a durable CI-backed check without changing the startup contract itself.*
