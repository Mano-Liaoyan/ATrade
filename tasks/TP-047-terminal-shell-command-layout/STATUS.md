# TP-047: Build the terminal shell, command registry, and resizable layout — Status

**Current Step:** Not Started
**Status:** 🔵 Ready for Execution
**Last Updated:** 2026-05-04
**Review Level:** 2
**Review Counter:** 0
**Iteration:** 0
**Size:** L

> **Hydration:** Checkboxes represent meaningful outcomes, not individual code
> changes. Workers expand steps when runtime discoveries warrant it — aim for
> 2-5 outcome-level items per step, not exhaustive implementation scripts.

---

### Step 0: Preflight
**Status:** ⬜ Not Started

- [ ] Required files and paths exist
- [ ] Dependencies satisfied

---

### Step 1: Model terminal modules and deterministic commands
**Status:** ⬜ Not Started

- [ ] Create terminal types and enabled/disabled module registry
- [ ] Create deterministic command registry/parser for approved commands
- [ ] Ensure disabled modules render honest unavailable states
- [ ] Add shell command source assertions

---

### Step 2: Build the terminal application frame and module rail
**Status:** ⬜ Not Started

- [ ] Create terminal app, command input, rail, strip, help, and status components
- [ ] Route home and symbol pages through the new terminal frame
- [ ] Make command input and rail first-class navigation paths
- [ ] Preserve paper-only/provider safety messages

---

### Step 3: Add resizable multi-panel layout and persistence
**Status:** ⬜ Not Started

> ⚠️ Hydrate: Expand after selecting the exact resizable split implementation compatible with the chosen UI stack.

- [ ] Add resizable primary/context/monitor layout with responsive fallback
- [ ] Add versioned localStorage persistence with bounds/reset behavior
- [ ] Add terminal layout CSS for splitters, panels, rail, command header, and status strip
- [ ] Ensure persistence is SSR-safe and browser/desktop-wrapper friendly

---

### Step 4: Retire the old shell primitives from active routes
**Status:** ⬜ Not Started

- [ ] Remove old shell primitive usage from active routes
- [ ] Update frontend tests away from old homepage/shell copy
- [ ] Preserve API clients/workflow modules for downstream module tasks
- [ ] Run targeted shell/command tests and frontend build

---

### Step 5: Testing & Verification
**Status:** ⬜ Not Started

- [ ] Command/shell validation passing
- [ ] Terminal shell UI validation passing
- [ ] Frontend bootstrap checks passing
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
| 2026-05-04 | Task staged | PROMPT.md and STATUS.md created |

---

## Blockers

*None*

---

## Notes

*Reserved for execution notes*
