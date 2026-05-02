# TP-036: Deepen the local runtime contract module — Status

**Current Step:** Step 0: Preflight
**Status:** 🟡 In Progress
**Last Updated:** 2026-05-02
**Review Level:** 3
**Review Counter:** 0
**Iteration:** 1
**Size:** L

> **Hydration:** Checkboxes represent meaningful outcomes, not individual code
> changes. Workers expand steps when runtime discoveries warrant it — aim for
> 2-5 outcome-level items per step, not exhaustive implementation scripts.

---

### Step 0: Preflight
**Status:** ✅ Complete

- [x] Required files and paths exist
- [x] Dependencies satisfied

---

### Step 1: Inventory and fix committed contract drift
**Status:** ⬜ Not Started

- [ ] Runtime defaults compared across template, shims, docs, and tests
- [ ] Safe paper-only committed defaults restored and documented
- [ ] New runtime-contract drift test added
- [ ] Targeted startup/config contract tests passing

---

### Step 2: Deepen shared env parsing and resolved contract interface
**Status:** ⬜ Not Started

> ⚠️ Hydrate: Expand checkboxes when entering this step based on the chosen shared module location and existing contract reader call sites.

- [ ] Shared runtime-contract interface implemented and duplicate parsing removed or adapted
- [ ] Secret/non-secret handling preserved
- [ ] Targeted .NET contract tests passing

---

### Step 3: Project resolved contract values into startup shims and AppHost
**Status:** ⬜ Not Started

- [ ] Startup shims and AppHost use consistent resolved defaults
- [ ] `start run` contract preserved on Unix and Windows shims
- [ ] AppHost environment handoff preserves broker/iBeam, LEAN, database, API, and frontend behavior
- [ ] Targeted AppHost/start-contract tests passing

---

### Step 4: Testing & Verification
**Status:** ⬜ Not Started

- [ ] FULL test suite passing
- [ ] Integration/contract tests passing or cleanly skipped where applicable
- [ ] All failures fixed
- [ ] Build passes

---

### Step 5: Documentation & Delivery
**Status:** ⬜ Not Started

- [ ] "Must Update" docs modified
- [ ] "Check If Affected" docs reviewed
- [ ] Discoveries logged

---

## Reviews

| # | Type | Step | Verdict | File |
|---|------|------|---------|------|

---

## Discoveries

| Discovery | Disposition | Location |
|-----------|-------------|----------|
| Prompt/file-scope references `scripts/start.run.cmd`, but the repository's committed Windows cmd shim is root `start.cmd`; `scripts/start.run.ps1` is the delegated Windows script. | Treat root `start.cmd` plus `scripts/start.run.ps1` as the Windows cmd/PowerShell startup surface unless implementation discovers a real need for a new delegated cmd script. | Preflight / `scripts/README.md` planned layout |

---

## Execution Log

| Timestamp | Action | Outcome |
|-----------|--------|---------|
| 2026-05-02 | Task staged | PROMPT.md and STATUS.md created |
| 2026-05-02 13:51 | Task started | Runtime V2 lane-runner execution |
| 2026-05-02 13:51 | Step 0 started | Preflight |
| 2026-05-02 16:00 | Step 0 completed | Preflight files/dependencies verified; `scripts/start.run.cmd` prompt mismatch logged as discovery. |

---

## Blockers

*None*

---

## Notes

- Preflight dependency check: `dotnet 10.0.203`, GNU bash 5.3.9, git 2.54.0, node v24.15.0/npm 11.12.1, Docker 29.3.0-ce, Podman 5.8.1 available; `pwsh` is not installed locally, so Windows PowerShell wrapper coverage remains via repository Windows harness/CI.

