# TP-011: Fix AppHost-managed container startup under a Podman-backed Docker API — Status

**Current Step:** Step 7: Delivery
**Status:** ✅ Complete
**Last Updated:** 2026-04-24
**Review Level:** 3
**Review Counter:** 0
**Iteration:** 1
**Size:** M

---

### Step 0: Preflight
**Status:** ✅ Complete

- [x] Reproduce/confirm the AppHost-created container runtime state in this repo
- [x] Confirm the effective `pids.max` problem on AppHost-created infra containers
- [x] Confirm the TimescaleDB tuning-script failure mode after pids are fixed

---

### Step 1: Fix process limits for AppHost-managed containers
**Status:** ✅ Complete

- [x] Update the AppHost resource configuration so infra containers do not inherit the broken default pids behavior
- [x] Use an explicit, readable container runtime configuration rather than a hidden machine tweak
- [x] Apply the fix consistently to the AppHost-managed infra resources that need it

---

### Step 2: Fix TimescaleDB startup for rootless Podman compatibility
**Status:** ✅ Complete

- [x] Make `timescaledb` start cleanly under the same runtime path after the pids fix
- [x] Prefer deterministic tuning inputs or another real configuration fix over hiding the problem
- [x] Keep the resource in the AppHost graph

---

### Step 3: Preserve the bootstrap graph
**Status:** ✅ Complete

- [x] Keep the existing AppHost graph names and roles intact
- [x] Do not replace Aspire with ad-hoc scripts or `docker compose`
- [x] Avoid unrelated consumer wiring

---

### Step 4: Add verification
**Status:** ✅ Complete

- [x] Add runtime-focused AppHost infrastructure verification when an engine is available
- [x] Verify affected containers get a real pids limit (`pids.max > 1`)
- [x] Verify `postgres` and `timescaledb` actually start through the AppHost path
- [x] Preserve the manifest-based verification path

---

### Step 5: Update docs
**Status:** ✅ Complete

- [x] Update `scripts/README.md`
- [x] Update `README.md` / `PLAN.md` only if wording would otherwise be stale
- [x] Call out any important local runtime assumptions without overstating support

---

### Step 6: Verification
**Status:** ✅ Complete

- [x] `bash tests/apphost/apphost-infrastructure-manifest-tests.sh`
- [x] Run the new runtime-focused AppHost infrastructure verification
- [x] Confirm the original startup failure class is resolved

---

### Step 7: Delivery
**Status:** ✅ Complete

- [x] Commit with conventions

---

## Reviews

| # | Type | Step | Verdict | File |
|---|------|------|---------|------|

---

## Discoveries

| Discovery | Disposition | Location |
|-----------|-------------|----------|
| `timeout 60s ./start run` created fresh AppHost-managed `postgres`, `timescaledb`, `redis`, and `nats` containers; inspect output confirmed each launched with `HostConfig.PidsLimit=0` under the Podman-backed Docker API. | Use as baseline evidence for Step 1 runtime fix. | Runtime repro on 2026-04-24 in lane-1 worktree |
| Live container inspection confirmed the broken translation from `HostConfig.PidsLimit=0` to an effective cgroup `pids.max=1`: `postgres` exposed `PROCROOT_PIDS_MAX ... 1`, `timescaledb` exposed `cat /sys/fs/cgroup/pids.max => 1`, and container logs showed `Cannot fork` / Go `newosproc` failures. | Treat as root cause evidence for AppHost-managed infra startup failures. | Runtime repro on 2026-04-24 in lane-1 worktree |
| Manual `timescale/timescaledb:latest-pg17` runs with `--pids-limit 2048` still failed without deterministic tuning inputs: `001_timescaledb_tune.sh` could not read `/sys/fs/cgroup/memory.max` or `/sys/fs/cgroup/cpu.max` and `timescaledb-tune` panicked; the same image stayed running once `TS_TUNE_MEMORY=512MB` and `TS_TUNE_NUM_CPUS=2` were supplied. | Use explicit tuning inputs in Step 2 rather than suppressing the failure. | Manual container repro on 2026-04-24 in lane-1 worktree |
| `src/ATrade.AppHost/Program.cs` now sets an explicit `--pids-limit 2048` container runtime argument for the AppHost-managed `postgres`, `timescaledb`, `redis`, and `nats` resources, and the AppHost project still builds cleanly. | Use this as the repo-local runtime fix baseline for verification in later steps. | `src/ATrade.AppHost/Program.cs`; `dotnet build src/ATrade.AppHost/ATrade.AppHost.csproj` |
| `src/ATrade.AppHost/Program.cs` now supplies deterministic `TS_TUNE_MEMORY=512MB` and `TS_TUNE_NUM_CPUS=2` values to the existing `timescaledb` resource; a live `./start run` repro showed the AppHost-managed `timescaledb`, `postgres`, `redis`, and `nats` containers all reach `Status=running` with `PidsLimit=2048`. | Keep the `timescaledb` resource in the AppHost graph while making the Podman-backed runtime path start cleanly. | `src/ATrade.AppHost/Program.cs`; runtime repro on 2026-04-24 in lane-1 worktree |
| `bash tests/apphost/apphost-infrastructure-manifest-tests.sh` still passed after the runtime fixes, preserving the `postgres`, `timescaledb`, `redis`, `nats`, `api`, and `frontend` graph names; direct code inspection of `src/ATrade.AppHost/Program.cs` confirmed the graph still uses Aspire primitives without `docker compose`, ad-hoc startup scripts, or new consumer wiring. | Treat as proof that the task preserved the bootstrap graph while staying in scope. | `tests/apphost/apphost-infrastructure-manifest-tests.sh`; `src/ATrade.AppHost/Program.cs` |
| `tests/apphost/apphost-infrastructure-runtime-tests.sh` now launches `./start run`, captures the fresh AppHost-managed infra containers for that session, verifies `HostConfig.PidsLimit`/effective `pids.max > 1` through `/proc/<pid>/root/sys/fs/cgroup/pids.max`, and asserts `postgres` / `timescaledb` logs no longer die in entrypoint scripts. The manifest test now also asserts the deterministic `TS_TUNE_*` values. | Use the runtime script when an engine is available and keep the manifest script as the engine-independent guardrail. | `tests/apphost/apphost-infrastructure-runtime-tests.sh`; `tests/apphost/apphost-infrastructure-manifest-tests.sh` |
| Final verification passed: the manifest test stayed green, the runtime test proved the AppHost-managed infra containers get `PidsLimit=2048` plus effective `pids.max > 1`, and the runtime assertions found no `Cannot fork`, `newosproc`, or `timescaledb-tune` cgroup-probe crash markers. | Treat as task-completion evidence for the original startup failure class. | `tests/apphost/apphost-infrastructure-manifest-tests.sh`; `tests/apphost/apphost-infrastructure-runtime-tests.sh` |

---

## Execution Log

| Timestamp | Action | Outcome |
|-----------|--------|---------|
| 2026-04-24 | Task staged | PROMPT.md and STATUS.md created |
| 2026-04-24 09:20 | Task started | Runtime V2 lane-runner execution |
| 2026-04-24 09:20 | Step 0 started | Preflight |
| 2026-04-24 11:30 | Reproduced AppHost runtime state | `./start run` created fresh managed infra containers with `HostConfig.PidsLimit=0` for `postgres`, `timescaledb`, `redis`, and `nats`. |
| 2026-04-24 11:30 | Confirmed broken effective pids limit | Live container inspection showed AppHost-created infra containers hit effective `pids.max=1`, producing `Cannot fork` and `newosproc` failures under the Podman-backed Docker API. |
| 2026-04-24 11:31 | Confirmed TimescaleDB tuning failure after safe pids | Manual `timescaledb` runs with `--pids-limit 2048` still crashed in `001_timescaledb_tune.sh` until explicit `TS_TUNE_MEMORY` and `TS_TUNE_NUM_CPUS` values were provided. |
| 2026-04-24 11:31 | Applied explicit infra pids limits | `ATrade.AppHost` now passes `--pids-limit 2048` to the AppHost-managed `postgres`, `timescaledb`, `redis`, and `nats` containers, and `dotnet build src/ATrade.AppHost/ATrade.AppHost.csproj` succeeded. |
| 2026-04-24 11:35 | Applied deterministic TimescaleDB tuning inputs | `ATrade.AppHost` now sets `TS_TUNE_MEMORY=512MB` and `TS_TUNE_NUM_CPUS=2` on the existing `timescaledb` resource, and a live `./start run` repro showed all four infra containers reach `Status=running` with `PidsLimit=2048`. |
| 2026-04-24 11:36 | Verified the bootstrap graph stayed intact | Manifest verification still passed for `postgres`, `timescaledb`, `redis`, `nats`, `api`, and `frontend`, and `Program.cs` still used Aspire-only resource wiring with no ad-hoc scripts, compose path, or unrelated consumers. |
| 2026-04-24 11:42 | Added runtime infrastructure verification | New `tests/apphost/apphost-infrastructure-runtime-tests.sh` now verifies real AppHost-managed container startup plus effective `pids.max > 1`, and the manifest test still passes with the new deterministic `TS_TUNE_*` assertions. |
| 2026-04-24 11:43 | Updated runtime docs | `scripts/README.md` now describes the explicit infra `--pids-limit 2048` safeguard, the deterministic `timescaledb` tuning inputs, and the new runtime verification path; `README.md` / `PLAN.md` were inspected and left unchanged because their current wording remained truthful. |
| 2026-04-24 11:44 | Completed final runtime verification | `bash tests/apphost/apphost-infrastructure-manifest-tests.sh` and `bash tests/apphost/apphost-infrastructure-runtime-tests.sh` both passed, confirming the old `Cannot fork` / `newosproc` startup class is resolved on the managed AppHost infra path. |

---

## Blockers

*None yet*

---

## Notes

*Goal: make the AppHost-managed infra resources start reliably under the operator's current container-runtime path instead of failing in entrypoint scripts and cgroup probing.*
