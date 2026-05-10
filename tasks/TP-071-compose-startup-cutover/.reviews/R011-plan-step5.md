## Plan Review: Step 5 — Documentation and durable memory update

### Verdict: APPROVE

### Summary
The five checkboxes correctly cover the documentation outcomes from PROMPT.md Step 5: the four "Must Update" files, modules doc review, verification inventories, ADR consideration, and CONTEXT.md updates. Each outcome is a meaningful behavioral change rather than an implementation detail. The worker has adequate direction to proceed — the PROMPT.md file lists exact artifacts and prescribes the messaging ("Compose manages infra; Aspire launches API, worker, and frontend"). The known areas of substantive rewrite (overview.md diagram and section 3, README.md Run Contract/Current Runtime Surface, scripts/README.md Required Behavior/Bootstrap Status) are all naturally covered by the outcome-level checkboxes. Several helpful suggestions below can improve completeness.

### Issues Found
_None blocking._

### Missing Items
_None. The five checkboxes map directly to the five outcomes from PROMPT.md Step 5, and together they address all "Must Update" files plus the "Check If Affected" conditional items._

### Suggestions

1. **"Check If Affected" docs should be explicitly noted during implementation** — The four "Check If Affected" architecture docs (`provider-abstractions.md`, `analysis-engines.md`, `backtesting.md`, `paper-trading-workspace.md`) are not listed as explicit checkboxes in Step 5. The grep results show `paper-trading-workspace.md` contains references to "AppHost-managed Postgres resource" (line ~44) and "AppHost-managed Postgres data directory" (line ~694) that describe Postgres as an Aspire-managed resource — these become stale after the cutover. While Step 7 "Delivery" has a "Check If Affected" docs reviewed checkbox, a quick scan during Step 5 would prevent a redo cycle. The worker should review these four files for "AppHost-managed" wording that refers to Postgres/TimescaleDB/Redis/NATS (not iBeam or LEAN, which remain AppHost-managed).

2. **`overview.md` architecture diagram needs redrawing** — Section 1's ASCII diagram currently shows `Infra` as a peer of API/Workers/Next.js under Aspire AppHost. After the cutover, Compose is a first-class startup step alongside Aspire, not a sub-box. The diagram should reflect: `start run` → Compose (infra) + AppHost (API/worker/frontend). The plan's outcome "Update architecture overview" covers this, but the worker should be aware the diagram rewrite is the most visible change.

3. **`overview.md` section 3 title and content** — Currently titled "Aspire 13.2 As The Orchestrator" and declares Aspire manages infra by default, with `ATRADE_INFRASTRUCTURE_MODE=compose` as opt-in. Post-cutover, the default is inverted: Compose manages infra by default, Aspire launches app services. Section 3 needs to describe the new division clearly and move the legacy apphost-infra mode to a separate "legacy fallback" subsection. The plan's outcome covers this rewrite, but the title change from single-orchestrator to split-orchestration is worth calling out.

4. **`README.md` "Run Contract" wording** — Currently says "All variants delegate to the Aspire AppHost so one command can bring up the API, worker, frontend, and local infrastructure." After cutover: "All variants invoke Compose for infrastructure, then delegate to the Aspire AppHost for API, worker, and frontend." The worker should update this sentence precisely.

5. **`README.md` "Current Runtime Surface" `ATrade.AppHost` entry** — The long paragraph starting "`src/ATrade.AppHost` — Aspire graph for the API, IBKR worker, Next.js frontend, volume-backed Postgres, volume-backed TimescaleDB, Redis, NATS…" needs to be split: Compose now manages Postgres/TimescaleDB/Redis/NATS volumes and ports, while AppHost only launches API/worker/frontend plus optional iBeam/LEAN containers (which remain AppHost-managed). This is the single largest paragraph rewrite in Step 5.

6. **`README.md` verification inventories** — The "Verification Entry Points" section should list the Compose contract tests (`tests/compose/compose-infra-contract-tests.sh`) and the renamed/migrated AppHost infrastructure/persistence tests. The current list doesn't include the new Compose test path. The plan's "Update verification inventories" checkbox covers this, but the worker should ensure the new tests from Steps 1-4 appear.

7. **ADR consideration** — The PROMPT says to "consider whether a short ADR is warranted." Given the significance of the orchestration split (default behavior changes, tests rewritten, documentation rewritten across 4+ files), a brief ADR in `docs/adr/` (e.g., `docs/adr/003-compose-infrastructure-split.md`) would be valuable. It can be short — 2-3 paragraphs capturing: what changed, why, what the new startup flow is, and the migration path for legacy apphost-mode users. If skipped, at minimum `PLAN.md`'s "Follow-Up Direction" section should capture this architecture decision so future maintainers understand why the split happened.

8. **`tasks/CONTEXT.md` runtime contract update** — The "Current Repository State" section currently says "AppHost-managed local infrastructure includes Postgres, TimescaleDB, Redis, and NATS." This should become "Compose-managed local infrastructure includes Postgres, TimescaleDB, Redis, and NATS; AppHost launches API, worker, and frontend." The "Next Task ID" should advance to `TP-072` (assuming TP-071 completes). The worker should also add a brief entry for TP-071 to the "most recent completed work" list after delivery.

9. **Consistency check: `scripts/README.md` still describes compose as "opt-in"** — The "Compose-managed infrastructure foundation variables" section and "Required Behavior" section still frame Compose as an opt-in mode and AppHost-managed infra as the default. After Step 1's flip of the default, this framing is stale. The compose section should be promoted and the AppHost-managed infra description should be demoted to a legacy/diagnostic note. This is the most important `scripts/README.md` rewrite in Step 5.
