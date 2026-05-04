# TP-026 Initial ATrade.sln Reference Classification

Source inventory: `initial-ATrade-sln-references.txt` generated with `rg -n "ATrade\\.sln\\b" .` excluding `.git`, `bin`, `obj`, and `node_modules`.

Total initial references: **128**.

## Active code / script / test references to migrate (24)

These are active repository checks or runtime code and must be updated to prefer `ATrade.slnx`.

| Path | Count | Disposition |
| --- | ---: | --- |
| `src/ATrade.ServiceDefaults/LocalDevelopmentPortContract.cs` | 1 | Update root detection to recognize `ATrade.slnx` before/alongside legacy `.sln`. |
| `tests/scaffolding/project-shells-tests.sh` | 7 | Update membership assertions and build command to `ATrade.slnx`. |
| `tests/apphost/accounts-feature-bootstrap-tests.sh` | 2 | Update membership assertion and build command to `ATrade.slnx`. |
| `tests/apphost/analysis-engine-contract-tests.sh` | 2 | Update solution path/build command to `ATrade.slnx`. |
| `tests/apphost/api-bootstrap-tests.sh` | 2 | Update membership assertion and build command to `ATrade.slnx`. |
| `tests/apphost/ibkr-market-data-provider-tests.sh` | 1 | Update membership assertion to `ATrade.slnx`. |
| `tests/apphost/ibkr-paper-safety-tests.sh` | 3 | Update membership assertions and build command to `ATrade.slnx`. |
| `tests/apphost/lean-analysis-engine-tests.sh` | 2 | Update membership assertions to `ATrade.slnx`. |
| `tests/apphost/market-data-feature-tests.sh` | 2 | Update membership assertion and build command to `ATrade.slnx`. |
| `tests/apphost/provider-abstraction-contract-tests.sh` | 2 | Update membership assertions to `ATrade.slnx`. |

## Current task packet material (30)

`tasks/TP-026-migrate-solution-references-to-slnx/PROMPT.md` (21) and `STATUS.md` (9) are current-task instructions/status that intentionally mention the migration target and legacy file. Keep as task history/status rather than treating as active solution guidance.

## Completed task packet history not to rewrite (74)

These references are in completed task packets. Leave untouched as immutable historical records and record as exceptions during delivery.

| Location group | Count | Disposition |
| --- | ---: | --- |
| `tasks/TP-019-*` through `tasks/TP-025-*` completed task packets | 31 | Completed packets with `.DONE`; leave historical references untouched. |
| `tasks/archive/TP-*` completed task packets | 43 | Archived historical task records; leave untouched. |

## Future-facing prompt material

No non-completed future/pending task prompt references were found. `tasks/TP-027-ibkr-ibeam-refresh-transport-fix` has no `ATrade.sln` references.

## Compatibility references

No active compatibility wording existed at preflight. If the legacy root `ATrade.sln` file remains after migration, Step 2/3 should add explicit compatibility wording stating that `ATrade.slnx` is authoritative and `ATrade.sln` is retained only for tooling compatibility.
