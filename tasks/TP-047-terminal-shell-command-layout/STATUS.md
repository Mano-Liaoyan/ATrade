# TP-047: Build the terminal shell, command registry, and resizable layout — Status

**Current Step:** Step 2: Build the terminal application frame and module rail
**Status:** 🟡 In Progress
**Last Updated:** 2026-05-04
**Review Level:** 2
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

### Step 1: Model terminal modules and deterministic commands
**Status:** ✅ Complete

- [x] Create terminal types and enabled/disabled module registry
- [x] Create deterministic command registry/parser for approved commands
- [x] Ensure disabled modules render honest unavailable states
- [x] Add shell command source assertions

---

### Step 2: Build the terminal application frame and module rail
**Status:** ✅ Complete

- [x] Create terminal app, command input, rail, strip, help, and status components
- [x] Route home and symbol pages through the new terminal frame
- [x] Make command input and rail first-class navigation paths
- [x] Preserve paper-only/provider safety messages

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
| 2026-05-04 22:05 | Task started | Runtime V2 lane-runner execution |
| 2026-05-04 22:05 | Step 0 started | Preflight |
| 2026-05-05 | Step 0 preflight | Verified required files, TP-046 terminal UI stack status, terminal primitives, installed frontend dependencies, and package lock |
| 2026-05-05 | Step 1 started | Loaded terminal UI design, module, and paper-workspace authorities |
| 2026-05-05 | Step 1 verification | Ran frontend-terminal-shell-command-tests.sh and TypeScript no-emit check with TS 6 deprecation silenced |
| 2026-05-05 | Step 2 started | Added new terminal frame, command input, module rail, status strip, help, and status components |
| 2026-05-05 | Step 2 verification | Ran command source test, TypeScript no-emit check, safety source grep, and frontend build |

---

## Blockers

*None*

---

## Notes

*Reserved for execution notes*
