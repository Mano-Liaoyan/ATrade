# TP-065: Terminal route architecture and old symbol route removal — Status

**Current Step:** Step 6: Documentation & Delivery
**Status:** ✅ Complete
**Last Updated:** 2026-05-07
**Review Level:** 1
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

### Step 1: Add canonical route helpers and page entrypoints
**Status:** ✅ Complete

- [x] Add reusable route parsing/creation helpers or page wrappers for terminal app initialization
- [x] Create enabled module route entrypoints for home/search/watchlist/chart/analysis/backtest/status/help
- [x] Create disabled module route entrypoints for news/portfolio/research/screener/econ/ai/node/orders
- [x] Preserve exact identity and chart range query parsing on symbol routes

---

### Step 2: Wire rail and workflow navigation to real routes
**Status:** ✅ Complete

- [x] Update module registry route metadata to canonical paths
- [x] Update rail clicks to push real enabled and disabled routes with accessible state preserved
- [x] Update market-monitor hrefs/intents to `/chart/[symbol]`, `/analysis/[symbol]`, and `/backtest/[symbol]`
- [x] Keep browser back/forward route-derived behavior without command or hash-only fallback

---

### Step 3: Remove old `/symbols/[symbol]` route without aliasing
**Status:** ✅ Complete

- [x] Delete `frontend/app/symbols/[symbol]/page.tsx`
- [x] Replace `/symbols/[symbol]` references in source/tests/docs with canonical chart/analysis/backtest routes
- [x] Verify no redirect, alias, compatibility route, or helper keeps `/symbols/[symbol]` alive

---

### Step 4: Add route architecture validation
**Status:** ✅ Complete

- [x] Create `tests/apphost/frontend-terminal-route-architecture-tests.sh`
- [x] Update existing route-sensitive frontend tests only where required
- [x] Keep validation provider/runtime independent

---

### Step 5: Testing & Verification
**Status:** ✅ Complete

- [x] Route architecture validation passing
- [x] Terminal chart/analysis validation passing
- [x] Trading workspace validation passing
- [x] Next.js bootstrap validation passing
- [x] Frontend build passes
- [x] FULL test suite passing
- [x] All failures fixed
- [x] Build passes

---

### Step 6: Documentation & Delivery
**Status:** ✅ Complete

- [x] Canonical route docs updated
- [x] README/PLAN verification/current-surface text updated if affected
- [x] "Check If Affected" docs reviewed
- [x] Discoveries logged

---

## Reviews

| # | Type | Step | Verdict | File |
|---|------|------|---------|------|

---

## Discoveries

| Discovery | Disposition | Location |
|-----------|-------------|----------|
| Disabled rail entries need canonical routes while still announcing disabled state. | Implemented focusable `aria-disabled` rail buttons with `aria-current` for selected disabled routes and app-owned route pushes. | `frontend/components/terminal/TerminalModuleRail.tsx`, `frontend/components/terminal/ATradeTerminalApp.tsx` |
| Existing cutover validation globally rejected `height: auto;`, which conflicted with the backtest comparison SVG rather than route architecture. | Narrowed the assertion to the terminal workspace layout owning `height: 100%` while preserving the no-splitter/no-context guardrail. | `tests/apphost/frontend-terminal-cutover-tests.sh` |
| `next build` rewrites generated `frontend/next-env.d.ts` references between dev/build route type outputs. | Reverted generated `next-env.d.ts` after validation runs; no source contract change required. | `frontend/next-env.d.ts` |

---

## Execution Log

| Timestamp | Action | Outcome |
|-----------|--------|---------|
| 2026-05-07 | Task staged | PROMPT.md and STATUS.md created |
| 2026-05-07 01:32 | Task started | Runtime V2 lane-runner execution |
| 2026-05-07 01:32 | Step 0 started | Preflight |
| 2026-05-07 03:10 | Step 0 completed | Required paths and TP-064/runtime dependencies verified |
| 2026-05-07 03:10 | Step 1 started | Canonical route helpers and page entrypoints |
| 2026-05-07 03:10 | Step 1 targeted validation | `NEXT_PUBLIC_ATRADE_API_BASE_URL=http://127.0.0.1:1 npm run build` passed with canonical routes plus pending old symbols route |
| 2026-05-07 03:10 | Step 1 completed | Enabled/disabled route entrypoints share route helpers and preserve symbol query parsing |
| 2026-05-07 03:10 | Step 2 started | Rail/workflow navigation canonical route wiring |
| 2026-05-07 03:10 | Step 2 targeted validation | `NEXT_PUBLIC_ATRADE_API_BASE_URL=http://127.0.0.1:1 npm run build` passed; generated `.next` removed afterward |
| 2026-05-07 03:10 | Step 2 completed | Rail and market-monitor workflows now use canonical route pushes/hrefs without hash or module-query fallback |
| 2026-05-07 03:10 | Step 3 started | Old `/symbols/[symbol]` removal |
| 2026-05-07 03:10 | Step 3 targeted validation | Updated route-sensitive shell tests, `bash -n` passed, and frontend build route list omitted `/symbols/[symbol]` |
| 2026-05-07 03:10 | Step 3 completed | Old symbols route deleted with no redirect/alias/helper in frontend source |
| 2026-05-07 03:10 | Step 4 started | Route architecture validation script and route-sensitive test updates |
| 2026-05-07 03:10 | Step 4 targeted validation | Route architecture plus route-sensitive static frontend shell tests passed; new route validation remains provider/runtime independent |
| 2026-05-07 03:10 | Step 4 completed | Added canonical route architecture validation and updated stale route assertions |
| 2026-05-07 03:10 | Step 5 started | Full task verification gate |
| 2026-05-07 03:10 | Step 5 verification | Route architecture, chart/analysis, trading workspace, Next.js bootstrap, frontend build, `dotnet test ATrade.slnx`, and `dotnet build ATrade.slnx` passed |
| 2026-05-07 03:10 | Step 5 completed | All required verification commands passed after updating bootstrap route-wrapper assertion |
| 2026-05-07 03:10 | Step 6 started | Documentation and delivery updates |
| 2026-05-07 03:10 | Step 6 completed | Active route docs, README/PLAN verification inventory/current surface, check-if-affected docs, and discoveries updated |
| 2026-05-07 03:10 | Task completed | All TP-065 steps and verification gates complete |

---

## Blockers

*None*

---

## Notes

*Reserved for execution notes*
