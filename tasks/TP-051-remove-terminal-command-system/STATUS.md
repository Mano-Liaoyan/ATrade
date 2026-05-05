# TP-051: Remove terminal branding and command system — Status

**Current Step:** Not Started
**Status:** 🔵 Ready for Execution
**Last Updated:** 2026-05-05
**Review Level:** 2
**Review Counter:** 0
**Iteration:** 0
**Size:** M

> **Hydration:** Checkboxes represent meaningful outcomes, not individual code
> changes. Workers expand steps when runtime discoveries warrant it — aim for
> 2-5 outcome-level items per step, not exhaustive implementation scripts.

---

### Step 0: Preflight
**Status:** ⬜ Not Started

- [ ] Required files and paths exist
- [ ] Dependencies satisfied

---

### Step 1: Remove the command system from active frontend source
**Status:** ⬜ Not Started

- [ ] Remove `TerminalCommandInput` and `terminalCommandRegistry` from active shell source
- [ ] Remove command parse/action/result types, command feedback, and command help constants from active source
- [ ] Preserve non-command module rail and market-monitor chart/analysis navigation
- [ ] Run targeted source validation for command removal

---

### Step 2: Remove user-facing ATrade Terminal and command-first copy
**Status:** ⬜ Not Started

- [ ] Remove visible `ATrade Terminal`, `ATrade Terminal Shell`, and command-first header copy
- [ ] Update HELP/status/safety/accessibility copy that references command-first terminal behavior
- [ ] Preserve `ATrade.Api`, provider-truthful, exact-identity, and no-order safety copy
- [ ] Run targeted source validation for removed copy and preserved safety facts

---

### Step 3: Update and add frontend validation scripts
**Status:** ⬜ Not Started

- [ ] Create `tests/apphost/frontend-no-command-shell-tests.sh`
- [ ] Delete or retire `tests/apphost/frontend-terminal-shell-command-tests.sh`
- [ ] Update affected shell/cutover/chart-analysis tests away from command assertions
- [ ] Preserve API-boundary, no-order, no-secrets, disabled-module, and identity-handoff assertions

---

### Step 4: Update active documentation and plan state
**Status:** ⬜ Not Started

- [ ] Update design doc away from command-first terminal requirements
- [ ] Update paper workspace and module docs for direct module/workflow navigation
- [ ] Update README verification inventory
- [ ] Update PLAN follow-up direction

---

### Step 5: Testing & Verification
**Status:** ⬜ Not Started

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

---

## Blockers

*None*

---

## Notes

*Reserved for execution notes*
