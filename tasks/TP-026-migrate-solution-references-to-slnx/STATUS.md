# TP-026: Migrate solution references from ATrade.sln to ATrade.slnx — Status

**Current Step:** Step 2: Migrate active docs and future-facing prompt material
**Status:** 🟡 In Progress
**Last Updated:** 2026-04-30
**Review Level:** 2
**Review Counter:** 0
**Iteration:** 1
**Size:** M

> **Hydration:** Checkboxes represent meaningful outcomes, not individual code changes. Workers expand steps when runtime discoveries warrant it — aim for 2-5 outcome-level items per step, not exhaustive implementation scripts.

---

### Step 0: Preflight and reference classification
**Status:** ✅ Complete

- [x] `ATrade.slnx` parse/build baseline confirmed
- [x] `ATrade.sln` reference inventory captured
- [x] References classified as active, future-facing prompt material, compatibility, or historical
- [x] Retain/remove decision for `ATrade.sln` recorded

---

### Step 1: Migrate active scripts and verification commands
**Status:** ✅ Complete

- [x] Active build/test scripts use `ATrade.slnx`
- [x] Solution membership assertions validate `ATrade.slnx`
- [x] Solution-root detection supports `ATrade.slnx`
- [x] Runtime skip behavior preserved
- [x] Targeted modified script checks pass

---

### Step 2: Migrate active docs and future-facing prompt material
**Status:** ✅ Complete

- [x] Active docs reference `ATrade.slnx`
- [x] Future task guidance references `ATrade.slnx`
- [x] Pending/future task prompt references updated where applicable
- [x] Completed task-packet historical exceptions handled and recorded
- [x] Temporary compatibility wording added if `ATrade.sln` remains

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
| Initial `ATrade.sln` references totaled 128: 24 active code/script/test references to migrate, 30 current-task instruction/status references, 74 completed-task historical references, and no non-completed future task prompt references. | Active references will be migrated; current-task and completed-task references are historical/current-task exceptions; no TP-027 update needed. | `tasks/TP-026-migrate-solution-references-to-slnx/audits/initial-classification.md` |
| Decision: retain root `ATrade.sln` for now as a non-authoritative compatibility artifact. | Active scripts/docs/tests will prefer `ATrade.slnx`; Step 2/3 will document compatibility wording and verify no active guidance prefers `.sln`. | Repo root solution files |
| `.env.example` was missing even though active startup docs/tests require it as the fallback local-port/env contract. | Restored `.env.example` by copying the safe committed `.env.template`; no real credentials or account identifiers added. | `.env.example`, `.env.template`, `scripts/local-env.sh` |
| Completed task-packet `ATrade.sln` references are historical records: 31 refs in completed `tasks/TP-019-*` through `TP-025-*` packets and 43 refs under `tasks/archive/`. | Left untouched as immutable task history; active docs now note TP-019 through TP-025 are completed pending archival. | `tasks/TP-019-*` through `tasks/TP-025-*`, `tasks/archive/` |

---

## Execution Log

| Timestamp | Action | Outcome |
|-----------|--------|---------|
| 2026-04-30 | Task staged | PROMPT.md and STATUS.md created |
| 2026-04-30 07:49 | Task started | Runtime V2 lane-runner execution |
| 2026-04-30 07:49 | Step 0 started | Preflight and reference classification |
| 2026-04-30 | Step 0 baseline | `dotnet sln ATrade.slnx list` parsed 20 projects matching 20 repo `.csproj` files; `dotnet build ATrade.slnx --nologo --verbosity minimal` passed with 0 warnings/errors. |
| 2026-04-30 | Step 0 reference inventory | Captured 128 `ATrade.sln` references from `rg -n "ATrade\\.sln\\b"` into `tasks/TP-026-migrate-solution-references-to-slnx/audits/initial-ATrade-sln-references.txt`. |
| 2026-04-30 | Step 0 classification | Wrote `audits/initial-classification.md`: 24 active references, 30 current-task references, 74 completed-task historical references, no TP-027/future prompt references. |
| 2026-04-30 | Step 0 retain/remove decision | `ATrade.sln` will remain temporarily as non-authoritative compatibility; `ATrade.slnx` is the active authoritative build/test target. |
| 2026-04-30 | Step 1 started | Migrating active shell scripts, membership checks, and root detection to prefer `ATrade.slnx`. |
| 2026-04-30 | Step 1 build commands migrated | Updated active shell-script `dotnet build` solution invocations to `ATrade.slnx`; `rg -n "dotnet (build|test).*ATrade\\.sln\\b" tests scripts --glob '*.sh'` returned no matches. |
| 2026-04-30 | Step 1 membership assertions migrated | Updated active shell scripts to inspect `ATrade.slnx`; `rg -n "ATrade\\.sln\\b" tests --glob '*.sh'` returned no matches. |
| 2026-04-30 | Step 1 root detection migrated | `LocalDevelopmentPortContract` now recognizes `ATrade.slnx` before the retained legacy `.sln` compatibility file and `.env.example`. |
| 2026-04-30 | Step 1 runtime skips preserved | `git diff -U0 -- tests/*.sh tests/**/*.sh | grep -E '^[+-].*(SKIP:|command -v (docker|lean)|exit 0)'` had no matches; modified scripts only changed solution references. |
| 2026-04-30 | Step 1 targeted script triage | First targeted script sweep passed `project-shells` and `provider-abstraction`, then failed `market-data-feature` before solution use because `.env.example` was missing; restored `.env.example` from `.env.template` and will rerun modified scripts. |
| 2026-04-30 | Step 1 targeted checks passed | Reran all modified scripts successfully: `project-shells`, `provider-abstraction`, `market-data-feature`, `lean-analysis-engine` (unit tests pass; LEAN CLI cleanly skipped), `analysis-engine-contract`, `ibkr-paper-safety`, `accounts-feature-bootstrap`, `ibkr-market-data-provider`, and `api-bootstrap`. |
| 2026-04-30 | Step 2 started | Auditing active docs and future-facing Taskplane material for `ATrade.sln` guidance and adding `ATrade.slnx` authority/compatibility wording. |
| 2026-04-30 | Step 2 active docs migrated | Updated `README.md`, `PLAN.md`, `scripts/README.md`, and `tasks/CONTEXT.md` so active guidance names `ATrade.slnx` as the authoritative solution; verified with `rg -n "ATrade\\.slnx\\b" README.md PLAN.md scripts/README.md tasks/CONTEXT.md docs --glob '*.md'`. |
| 2026-04-30 | Step 2 future guidance migrated | `tasks/CONTEXT.md` now tells new task prompts and verification commands to use `ATrade.slnx`; template/pending-task audit found no stale future-facing `ATrade.sln` guidance outside TP-026/current compatibility wording. |
| 2026-04-30 | Step 2 pending prompt audit | `rg -n "ATrade\\.sln\\b" tasks/TP-027-ibkr-ibeam-refresh-transport-fix` returned no matches, so no pending/future task prompt edits were needed beyond `tasks/CONTEXT.md`. |
| 2026-04-30 | Step 2 historical exceptions recorded | Audited completed packets: 31 root completed-task refs plus 43 archived refs remain intentionally untouched as historical records. |
| 2026-04-30 | Step 2 compatibility wording added | `README.md`, `PLAN.md`, `scripts/README.md`, and `tasks/CONTEXT.md` explain that `ATrade.sln` is retained only as a temporary non-authoritative compatibility artifact while `ATrade.slnx` is authoritative. |

---

## Blockers

*None*

---

## Notes

Created after integrating batch `20260429T221511`. The integration kept both `ATrade.sln` and `ATrade.slnx`, with both solution files listing 20 projects and both builds passing. This task should make `ATrade.slnx` the active authoritative solution reference while handling `ATrade.sln` as either a temporary compatibility artifact or a removed legacy file.
