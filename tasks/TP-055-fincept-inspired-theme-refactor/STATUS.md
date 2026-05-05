# TP-055: Fincept-inspired terminal theme refactor — Status

**Current Step:** Step 1: Define the original ATrade institutional terminal palette
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

### Step 1: Define the original ATrade institutional terminal palette
**Status:** 🟨 In Progress

- [ ] Inventory current theme tokens, terminal primitives, and chart colors
- [ ] Define original black/graphite/amber terminal tokens without copying third-party palette values or branding
- [ ] Fix token/config mismatches discovered during inventory
- [ ] Record palette decisions and clean-room constraints in discoveries

---

### Step 2: Apply the theme refactor across the workspace shell and primitives
**Status:** ⬜ Not Started

- [ ] Apply new theme tokens to global CSS and Tailwind config
- [ ] Reduce cyan/blue dominant gradients/glows while preserving accessible focus/information contrast
- [ ] Restyle terminal and UI primitives into crisp dense terminal controls
- [ ] Align chart colors with the new theme without breaking chart behavior or truthful states

---

### Step 3: Add theme validation coverage
**Status:** ⬜ Not Started

- [ ] Create `tests/apphost/frontend-terminal-theme-refactor-tests.sh`
- [ ] Update existing frontend terminal validation scripts only if affected
- [ ] Ensure validation is source/build based and provider-independent

---

### Step 4: Testing & Verification
**Status:** ⬜ Not Started

- [ ] New theme validation passing
- [ ] UI stack validation passing
- [ ] Shell validation passing
- [ ] Frontend build passes
- [ ] FULL test suite passing
- [ ] All failures fixed
- [ ] Build passes

---

### Step 5: Documentation & Delivery
**Status:** ⬜ Not Started

- [ ] "Must Update" docs modified
- [ ] README/PLAN verification/current-surface text updated if affected
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
| 2026-05-05 21:51 | Task started | Runtime V2 lane-runner execution |
| 2026-05-05 21:51 | Step 0 started | Preflight |
| 2026-05-05 | Step 0 completed | Required paths verified; Node/npm/.NET available; frontend dependencies installed with npm ci |

---

## Blockers

*None*

---

## Notes

*Reserved for execution notes*
