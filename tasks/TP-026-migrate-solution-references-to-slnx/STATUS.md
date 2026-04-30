# TP-026: Migrate solution references from ATrade.sln to ATrade.slnx — Status

**Current Step:** Step 0: Preflight and reference classification
**Status:** ⬜ Not Started
**Last Updated:** 2026-04-30
**Review Level:** 2
**Review Counter:** 0
**Iteration:** 0
**Size:** M

> **Hydration:** Checkboxes represent meaningful outcomes, not individual code changes. Workers expand steps when runtime discoveries warrant it — aim for 2-5 outcome-level items per step, not exhaustive implementation scripts.

---

### Step 0: Preflight and reference classification
**Status:** ⬜ Not Started

- [ ] `ATrade.slnx` parse/build baseline confirmed
- [ ] `ATrade.sln` reference inventory captured
- [ ] References classified as active, future-facing prompt material, compatibility, or historical
- [ ] Retain/remove decision for `ATrade.sln` recorded

---

### Step 1: Migrate active scripts and verification commands
**Status:** ⬜ Not Started

- [ ] Active build/test scripts use `ATrade.slnx`
- [ ] Solution membership assertions validate `ATrade.slnx`
- [ ] Solution-root detection supports `ATrade.slnx`
- [ ] Runtime skip behavior preserved
- [ ] Targeted modified script checks pass

---

### Step 2: Migrate active docs and future-facing prompt material
**Status:** ⬜ Not Started

- [ ] Active docs reference `ATrade.slnx`
- [ ] Future task guidance references `ATrade.slnx`
- [ ] Pending/future task prompt references updated where applicable
- [ ] Completed task-packet historical exceptions handled and recorded
- [ ] Temporary compatibility wording added if `ATrade.sln` remains

---

### Step 3: Finalize solution-file contract
**Status:** ⬜ Not Started

- [ ] `ATrade.slnx` contains all required projects
- [ ] `ATrade.sln` retained/removed according to recorded decision
- [ ] Active scripts/docs no longer prefer `ATrade.sln`
- [ ] Regression check for stale active solution references added or updated where appropriate

---

### Step 4: Testing & Verification
**Status:** ⬜ Not Started

- [ ] `dotnet test ATrade.slnx --nologo --verbosity minimal` passes
- [ ] `dotnet build ATrade.slnx --nologo --verbosity minimal` passes
- [ ] Targeted modified scripts pass or cleanly skip
- [ ] `bash tests/start-contract/start-wrapper-tests.sh` passes
- [ ] Active reference audit has no unexplained stale `ATrade.sln` guidance
- [ ] All failures fixed

---

### Step 5: Documentation & Delivery
**Status:** ⬜ Not Started

- [ ] "Must Update" docs modified
- [ ] "Check If Affected" docs reviewed
- [ ] Reference audit results and historical exceptions logged
- [ ] Delivery notes explain whether `ATrade.sln` was retained or removed

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
| 2026-04-30 | Task staged | PROMPT.md and STATUS.md created |

---

## Blockers

*None*

---

## Notes

Created after integrating batch `20260429T221511`. The integration kept both `ATrade.sln` and `ATrade.slnx`, with both solution files listing 20 projects and both builds passing. This task should make `ATrade.slnx` the active authoritative solution reference while handling `ATrade.sln` as either a temporary compatibility artifact or a removed legacy file.
