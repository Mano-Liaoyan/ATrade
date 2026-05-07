# TP-065: Terminal route architecture and old symbol route removal — Status

**Current Step:** Not Started
**Status:** 🔵 Ready for Execution
**Last Updated:** 2026-05-07
**Review Level:** 1
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

### Step 1: Add canonical route helpers and page entrypoints
**Status:** ⬜ Not Started

- [ ] Add reusable route parsing/creation helpers or page wrappers for terminal app initialization
- [ ] Create enabled module route entrypoints for home/search/watchlist/chart/analysis/backtest/status/help
- [ ] Create disabled module route entrypoints for news/portfolio/research/screener/econ/ai/node/orders
- [ ] Preserve exact identity and chart range query parsing on symbol routes

---

### Step 2: Wire rail and workflow navigation to real routes
**Status:** ⬜ Not Started

- [ ] Update module registry route metadata to canonical paths
- [ ] Update rail clicks to push real enabled and disabled routes with accessible state preserved
- [ ] Update market-monitor hrefs/intents to `/chart/[symbol]`, `/analysis/[symbol]`, and `/backtest/[symbol]`
- [ ] Keep browser back/forward route-derived behavior without command or hash-only fallback

---

### Step 3: Remove old `/symbols/[symbol]` route without aliasing
**Status:** ⬜ Not Started

- [ ] Delete `frontend/app/symbols/[symbol]/page.tsx`
- [ ] Replace `/symbols/[symbol]` references in source/tests/docs with canonical chart/analysis/backtest routes
- [ ] Verify no redirect, alias, compatibility route, or helper keeps `/symbols/[symbol]` alive

---

### Step 4: Add route architecture validation
**Status:** ⬜ Not Started

- [ ] Create `tests/apphost/frontend-terminal-route-architecture-tests.sh`
- [ ] Update existing route-sensitive frontend tests only where required
- [ ] Keep validation provider/runtime independent

---

### Step 5: Testing & Verification
**Status:** ⬜ Not Started

- [ ] Route architecture validation passing
- [ ] Terminal chart/analysis validation passing
- [ ] Trading workspace validation passing
- [ ] Next.js bootstrap validation passing
- [ ] Frontend build passes
- [ ] FULL test suite passing
- [ ] All failures fixed
- [ ] Build passes

---

### Step 6: Documentation & Delivery
**Status:** ⬜ Not Started

- [ ] Canonical route docs updated
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
| 2026-05-07 | Task staged | PROMPT.md and STATUS.md created |

---

## Blockers

*None*

---

## Notes

*Reserved for execution notes*
