# TP-051: Remove terminal branding and command system — Status

**Current Step:** Step 5: Testing & Verification
**Status:** 🟡 In Progress
**Last Updated:** 2026-05-05
**Review Level:** 2
**Review Counter:** 0
**Iteration:** 1
**Size:** M

> **Hydration:** Checkboxes represent meaningful outcomes, not individual code
> changes. Workers expand steps when runtime discoveries warrant it — aim for
> 2-5 outcome-level items per step, not exhaustive implementation scripts.

---

### Step 0: Preflight
**Status:** ✅ Complete

- [x] Required files and paths exist
- [x] Dependencies satisfied

---

### Step 1: Remove the command system from active frontend source
**Status:** ✅ Complete

- [x] Remove `TerminalCommandInput` and `terminalCommandRegistry` from active shell source
- [x] Remove command parse/action/result types, command feedback, and command help constants from active source
- [x] Preserve non-command module rail and market-monitor chart/analysis navigation
- [x] Run targeted source validation for command removal

---

### Step 2: Remove user-facing ATrade Terminal and command-first copy
**Status:** ✅ Complete

- [x] Remove visible `ATrade Terminal`, `ATrade Terminal Shell`, and command-first header copy
- [x] Update HELP/status/safety/accessibility copy that references command-first terminal behavior
- [x] Preserve `ATrade.Api`, provider-truthful, exact-identity, and no-order safety copy
- [x] Run targeted source validation for removed copy and preserved safety facts

---

### Step 3: Update and add frontend validation scripts
**Status:** ✅ Complete

- [x] Create `tests/apphost/frontend-no-command-shell-tests.sh`
- [x] Delete or retire `tests/apphost/frontend-terminal-shell-command-tests.sh`
- [x] Update affected shell/cutover/chart-analysis tests away from command assertions
- [x] Preserve API-boundary, no-order, no-secrets, disabled-module, and identity-handoff assertions

---

### Step 4: Update active documentation and plan state
**Status:** ✅ Complete

- [x] Update design doc away from command-first terminal requirements
- [x] Update paper workspace and module docs for direct module/workflow navigation
- [x] Update README verification inventory
- [x] Update PLAN follow-up direction

---

### Step 5: Testing & Verification
**Status:** 🟨 In Progress

- [ ] No-command validation passing
- [ ] Updated shell/cutover validations passing
- [ ] Affected workflow validations passing
- [ ] Frontend build passes
- [ ] FULL test suite passing
- [ ] All failures fixed
- [ ] Build passes

---

### Step 6: Documentation & Delivery
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

---

## Execution Log

| Timestamp | Action | Outcome |
|-----------|--------|---------|
| 2026-05-05 | Task staged | PROMPT.md and STATUS.md created |
| 2026-05-05 13:27 | Task started | Runtime V2 lane-runner execution |
| 2026-05-05 13:27 | Step 0 started | Preflight |

---

## Blockers

*None*

---

## Notes

*Reserved for execution notes*
