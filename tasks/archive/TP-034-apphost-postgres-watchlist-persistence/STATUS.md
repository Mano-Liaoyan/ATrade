# TP-034: Persist AppHost Postgres watchlists across application reboot — Status

**Current Step:** Step 5: Documentation & Delivery
**Status:** 🟡 In Progress
**Last Updated:** 2026-04-30
**Review Level:** 1
**Review Counter:** 0
**Iteration:** 1
**Size:** M

> **Hydration:** Checkboxes represent meaningful outcomes, not individual code
> changes. Workers expand steps when runtime discoveries warrant it — aim for
> 2-5 outcome-level items per step, not exhaustive implementation scripts.

---

### Step 0: Confirm root cause and scope boundary
**Status:** ✅ Complete

- [x] Current AppHost Postgres storage inspected
- [x] Existing API-restart watchlist coverage reviewed
- [x] Selected Postgres volume approach recorded
- [x] Frontend/localStorage scope boundary confirmed

---

### Step 1: Add durable Postgres storage to AppHost
**Status:** ✅ Complete

- [x] Persistent AppHost data volume added for `postgres`
- [x] Optional non-secret volume-name setting added and parsed if needed
- [x] Isolated test volume strategy implemented without touching developer default volume
- [x] Existing AppHost project references and connection-string names preserved
- [x] Targeted AppHost build/manifest checks run

---

### Step 2: Add full AppHost watchlist reboot regression coverage
**Status:** ✅ Complete

- [x] New AppHost watchlist volume test starts with isolated temp ports/volume
- [x] Test pins watchlist entries, restarts full AppHost, and verifies pins survive
- [x] Test uses backend API persistence only, not localStorage
- [x] Runtime skip and cleanup are safe for unavailable Docker/Podman
- [x] Manifest assertions verify non-read-only Postgres volume mount

---

### Step 3: Guard against regressions in existing watchlist behavior
**Status:** ✅ Complete

- [x] Exact `instrumentKey` / `pinKey` semantics preserved
- [x] Database-unavailable behavior remains explicit
- [x] Existing Workspaces and watchlist apphost tests run
- [x] Frontend tests updated only if frontend-visible behavior changes

---

### Step 4: Testing & Verification
**Status:** ✅ Complete

- [x] `dotnet test tests/ATrade.Workspaces.Tests/ATrade.Workspaces.Tests.csproj --nologo --verbosity minimal` passing
- [x] `bash tests/apphost/postgres-watchlist-persistence-tests.sh` passing
- [x] `bash tests/apphost/apphost-postgres-watchlist-volume-tests.sh` passing
- [x] `bash tests/apphost/apphost-infrastructure-manifest-tests.sh` passing
- [x] `bash tests/apphost/apphost-infrastructure-runtime-tests.sh` passing or cleanly skipped
- [x] `bash tests/apphost/paper-trading-config-contract-tests.sh` passing if `.env.template` changes
- [x] FULL test suite passing: `dotnet test ATrade.slnx --nologo --verbosity minimal`
- [x] Solution build passing: `dotnet build ATrade.slnx --nologo --verbosity minimal`
- [x] All failures fixed or unrelated pre-existing failures documented

---

### Step 5: Documentation & Delivery
**Status:** ✅ Complete

- [x] "Must Update" docs modified
- [x] "Check If Affected" docs reviewed
- [x] Discoveries logged with root cause, volume name/override behavior, and cleanup caveats

---

## Reviews

| # | Type | Step | Verdict | File |
|---|------|------|---------|------|

---

## Discoveries

| Discovery | Disposition | Location |
|-----------|-------------|----------|
| AppHost declares `postgres` as `builder.AddPostgres("postgres").WithContainerRuntimeArgs("--pids-limit", safeInfraContainerPidsLimit)` with no `WithDataVolume(...)`, bind mount, or volume mount on the primary Postgres resource, so full AppHost/container recreation can lose watchlist rows even though API/repository persistence works while the database container/data directory survives. | Drives Step 1 AppHost volume fix. | `src/ATrade.AppHost/Program.cs:21` |
| Existing `postgres-watchlist-persistence-tests.sh` starts one disposable Postgres container, pins exact IBKR/provider-market watchlist entries, stops/restarts only `ATrade.Api`, and verifies rows survive against the same database; it does not restart AppHost or recreate the `postgres` container/data directory. | Drives Step 2 full AppHost reboot regression coverage. | `tests/apphost/postgres-watchlist-persistence-tests.sh:333` |
| Selected AppHost storage approach: add Aspire `WithDataVolume(storageContract.PostgresDataVolumeName, isReadOnly: false)` to the primary `postgres` resource, preserve the existing `--pids-limit` runtime arg, add non-secret `.env.template` default `ATRADE_POSTGRES_DATA_VOLUME=atrade-postgres-data`, and let tests override that setting with an isolated temporary volume name. | Implement in Step 1 and verify through manifest/runtime tests; tests must remove only their own temporary volume. | `src/ATrade.AppHost/Program.cs`, `.env.template`, new `AppHostStorageContract` |
| Frontend scope boundary confirmed: docs and tests already require the browser to load/pin/unpin through `/api/workspace/watchlist`; `localStorage` remains a symbol-only, non-authoritative fallback/migration cache and must not be changed for this AppHost storage fix. | Leave frontend behavior unchanged unless a later regression proves otherwise. | `docs/architecture/paper-trading-workspace.md:430`, `frontend/lib/watchlistStorage.ts:5`, `tests/apphost/frontend-trading-workspace-tests.sh:126` |
| Primary AppHost `postgres` now uses an explicit writable Aspire data volume before preserving the existing `--pids-limit` runtime arg. | Implemented in Step 1. | `src/ATrade.AppHost/Program.cs:22` |
| Added non-secret `ATRADE_POSTGRES_DATA_VOLUME` storage contract parsing with default `atrade-postgres-data`; environment variables override `.env`/`.env.template`, and invalid volume names fail fast instead of being passed to Docker. | Enables developer override and isolated AppHost reboot tests without secrets. | `.env.template`, `src/ATrade.AppHost/AppHostStorageContract.cs` |
| Manifest coverage now exports an isolated `atrade-postgres-manifest-test-*` volume name and asserts the AppHost manifest uses it, proving tests can override the developer default without removing or modifying `atrade-postgres-data`. | Step 2 runtime test should use the same override principle and clean up only its own temp volume. | `tests/apphost/apphost-infrastructure-manifest-tests.sh` |
| AppHost project references remain wired to the existing `postgres`, `timescaledb`, `redis`, and `nats` resources; manifest assertions now pin `ConnectionStrings__postgres` and `ConnectionStrings__timescaledb` so the API/worker connection-string names are not accidentally renamed while adding storage. | Guarded by manifest test. | `src/ATrade.AppHost/Program.cs`, `tests/apphost/apphost-infrastructure-manifest-tests.sh` |
| Added AppHost reboot regression script with unique loopback API/frontend ports, `ATRADE_POSTGRES_DATA_VOLUME=atrade-postgres-watchlist-volume-test-*`, and health polling against the AppHost-managed API. | Implements Step 2 runtime test entrypoint. | `tests/apphost/apphost-postgres-watchlist-volume-tests.sh` |
| The AppHost reboot script pins AAPL NASDAQ, AAPL LSE, and MSFT through `/api/workspace/watchlist`, stops the full AppHost session and its containers while keeping the named volume, restarts AppHost with the same volume, and verifies exact `instrumentKey`/metadata survives. | Implements full reboot persistence regression. | `tests/apphost/apphost-postgres-watchlist-volume-tests.sh` |
| The reboot test is API-only: it uses `curl` against AppHost-managed `/health` and `/api/workspace/watchlist` endpoints and does not start a browser, inspect frontend files, or read/write `localStorage`/cache files. | Confirms backend Postgres volume is the persistence source under test. | `tests/apphost/apphost-postgres-watchlist-volume-tests.sh` |
| Runtime test skips cleanly when Docker CLI or engine is unavailable; cleanup kills the AppHost process, removes only containers created in the current session, and removes only the unique `atrade-postgres-watchlist-volume-test-*` volume allocated by the test. | Prevents developer default volume deletion/corruption. | `tests/apphost/apphost-postgres-watchlist-volume-tests.sh` |
| AppHost manifest assertions verify the `postgres` resource includes the configured named volume at `/var/lib/postgresql/data` with `readOnly: false`. | Guards published graph persistence. | `tests/apphost/apphost-infrastructure-manifest-tests.sh` |
| Full AppHost reboot test exposed an additional persistence requirement: once `postgres` data is volume-backed, the AppHost-generated random `postgres-password` can change between full AppHost sessions, causing password-auth failures against the preserved data directory. | Step 2/1 fix extended to use a stable secret parameter value loaded from the local contract; template remains a fake local-dev placeholder and tests override it. | `tests/apphost/apphost-postgres-watchlist-volume-tests.sh`, `src/ATrade.AppHost/Program.cs` |
| Exact `instrumentKey` / `pinKey` semantics were not changed by the AppHost storage fix; Workspaces unit coverage and existing API restart coverage still pass for duplicate same-symbol market pins and exact key deletion. | Verified in Step 3. | `tests/ATrade.Workspaces.Tests`, `tests/apphost/postgres-watchlist-persistence-tests.sh` |
| Database-unavailable behavior remains explicit: repository storage failures still surface `WorkspaceStorageUnavailableException`, API watchlist endpoints still return 503 `watchlist-storage-unavailable`, and frontend cache remains read-only/actions-disabled when the backend is unavailable. | Verified by static assertions in Step 3; no frontend/localStorage masking added. | `src/ATrade.Api/Program.cs`, `src/ATrade.Workspaces/PostgresWorkspaceWatchlistRepository.cs`, `frontend/components/TradingWorkspace.tsx` |
| No frontend-visible behavior changed for this storage-only fix; frontend sources and `frontend-trading-workspace-tests.sh` remain untouched. | Frontend test updates not needed. | `frontend/`, `tests/apphost/frontend-trading-workspace-tests.sh` |
| `apphost-infrastructure-runtime-tests.sh` now overrides AppHost Postgres to an isolated `atrade-postgres-runtime-test-*` volume/password and removes only that test volume; on this Docker host it cleanly skips effective cgroup verification because `/proc/<container-pid>/root/sys/fs/cgroup/pids.max` is unreadable after verifying `HostConfig.PidsLimit=2048`. | Prevents runtime tests from touching the developer default volume while preserving environment-aware skip behavior. | `tests/apphost/apphost-infrastructure-runtime-tests.sh` |
| Must-update docs now describe volume-backed AppHost Postgres watchlist persistence, the `ATRADE_POSTGRES_DATA_VOLUME` / stable `ATRADE_POSTGRES_PASSWORD` contract, full AppHost reboot survival, and local/test cleanup caveats. | Documentation delivery. | `scripts/README.md`, `docs/architecture/paper-trading-workspace.md`, `docs/architecture/modules.md` |
| Check-if-affected docs reviewed: `.env.template` was updated for the new AppHost Postgres contract, `docs/architecture/overview.md` and `README.md` were updated for runtime-surface wording, and `docs/INDEX.md` required no change because no new active docs were introduced. | Documentation delivery. | `.env.template`, `docs/architecture/overview.md`, `README.md`, `docs/INDEX.md` |
| Final delivery summary: root cause was an AppHost `postgres` resource without a persistent data directory; the fix uses `ATRADE_POSTGRES_DATA_VOLUME` default `atrade-postgres-data` with env override plus stable `ATRADE_POSTGRES_PASSWORD` because a preserved data directory rejects newly generated passwords; tests use and remove only isolated `atrade-postgres-watchlist-volume-test-*`, `atrade-postgres-runtime-test-*`, or manifest-only volume names. | Delivery notes complete. | `STATUS.md`, docs, AppHost/test changes |

---

## Execution Log

| Timestamp | Action | Outcome |
|-----------|--------|---------|
| 2026-04-30 | Task staged | PROMPT.md and STATUS.md created |
| 2026-04-30 22:10 | Task started | Runtime V2 lane-runner execution |
| 2026-04-30 22:10 | Step 0 started | Confirm root cause and scope boundary |
| 2026-05-01 | Step 1 targeted checks | `dotnet build src/ATrade.AppHost/ATrade.AppHost.csproj --nologo --verbosity minimal`, `bash tests/apphost/apphost-infrastructure-manifest-tests.sh`, and `bash tests/apphost/paper-trading-config-contract-tests.sh` passed |
| 2026-05-01 | Step 2 targeted checks | `dotnet build src/ATrade.AppHost/ATrade.AppHost.csproj --nologo --verbosity minimal`, `bash tests/apphost/apphost-postgres-watchlist-volume-tests.sh`, `bash tests/apphost/apphost-infrastructure-manifest-tests.sh`, and `bash tests/apphost/paper-trading-config-contract-tests.sh` passed after stabilizing the AppHost Postgres password contract |
| 2026-05-01 | Step 3 targeted checks | `dotnet test tests/ATrade.Workspaces.Tests/ATrade.Workspaces.Tests.csproj --nologo --verbosity minimal` passed (23 tests), `bash tests/apphost/postgres-watchlist-persistence-tests.sh` passed, and static unavailable-state guard assertions passed |
| 2026-05-01 | Step 4 verification | Required Workspaces, watchlist persistence, AppHost volume, manifest, paper-trading config, full solution test, and solution build commands passed; AppHost infrastructure runtime check cleanly skipped effective cgroup verification on this Docker host after verifying `HostConfig.PidsLimit=2048` |
| 2026-05-01 | Step 5 docs verification | Documentation markers for `ATRADE_POSTGRES_DATA_VOLUME`, `ATRADE_POSTGRES_PASSWORD`, AppHost reboot survival, and isolated test cleanup verified across updated docs |

---

## Blockers

*None*

---

## Notes

*Reserved for execution notes*
