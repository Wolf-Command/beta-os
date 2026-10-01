# Exit notes — Phase A forensic completeness
**Run:** 2026-10-01 ~19:20 WITA · Cursor · discovery only  
No Exit Report. No Wolf Intelligence. No product PR. Prod `:8787` was GET-only. `staff_ready` not flipped. Matt not pinged.

## Files
All under `~/beta-os/state/final-completion/forensic-completeness-20261001/`:

| File | Role |
|---|---|
| MISSION-CHARTER.md | Peaches, pre-existing |
| PEACHES-SAMPLE-VERIFY.md / .json | Peaches floor, pre-existing, not rewritten |
| build_inventory.py | Extractor for the jsonl |
| INVENTORY-STATS.json | Machine counts |
| V1-SURFACE-INVENTORY.jsonl | **177** function rows |
| V1-SURFACE-INVENTORY-SUMMARY.md | |
| BETA-SURFACE-INVENTORY.jsonl | **188** records (158 page surfaces + 30 functions) |
| BETA-SURFACE-INVENTORY-SUMMARY.md | |
| V1-BETA-DIFFERENCE-MATRIX.jsonl | **177** rows |
| V1-BETA-DIFFERENCE-MATRIX-SUMMARY.md | |
| MISSING-FUNCTION-REGISTER.jsonl | **177** (every inventoried job still has a gap; the 6 real-data glances stay in because the job behind the number is open) |
| REQUIREMENTS-RECOVERY.md | |
| REQUIREMENTS-SEARCH-LOG.md | |
| BUSINESS-OPS-AUDIT.md | |
| DASHBOARD-EYES.md | API/HTML/sqlite. No screenshots. Beta `/` not re-fetched after Peaches 403 |
| CONNECTIONS-42-OPERATIONAL.md | 42 ids from the Beta House matrix |
| HISTORY-GAPS.md | |
| E2E-WORKFLOW-CHAINS.md | |
| FIRST-CHECKPOINT.md | Expansion draft for Peaches → Matt |
| BUILD-PACK-QUEUE.md | Names and scope only |
| EXIT-NOTES.md | This file |

## Deltas vs the 22-surface parity audit (2026-09-30)
| Prior parity | This pass |
|---|---|
| 22 surfaces | 177 functions (Y not closed) |
| BETA_BETTER 5, PARITY 5, V1_BETTER 5, BETA_MISSING 3, MORE_CONFUSING 2, V1_OBSOLETE 2 | Function classes: LESS_FUNCTIONAL 70, MISSING_FROM_BETA 47, MORE_CONFUSING 18, INTEGRATION_MISSING 12, WRITE_WORKFLOW_MISSING 11, HISTORY_MISSING 5, ACTION_MISSING 5, DATA_MISSING 4, NAVIGATION_WRONG 3, PERMISSION_WRONG 2, BETA_BETTER 0, SUPERSEDED_CORRECTLY 0 |
| Content / BZG / voice / Habitat / integrations treated as parity or better | Withdrawn at function level. Evidence on the matrix rows |
| Owner home “no live pulse” | Page 403 stands. JSON pulse has 10 cards; 8 Beta function rows classed FUNCTIONAL_REAL_DATA as **reads only**. HUMAN_PROVEN 0 |
| ~283 LaunchAgents | This session: **169** `*.plist`, **280** names including bak/parked/disabled |

## Deltas vs the Peaches sample (same folder, earlier this evening)
Incorporated, not re-litigated: HTML 55 / 158, manifest 23, parity 22, NAS 38,091, library stamp 18, Wave 8, empty requirements dir, 7 reconstruction files, 12 Owner Home items.

Added: assets table **48**, `nas_index` **63,370**, footage catalogue **61,719**, recipe copy 127/756, Alchemist row counts, Beta ops tables at 0, sales sqlite counts, 14-round ledger is 15 lines, 465 requirements are a condensation, connection matrix Spartacus/Trading still ABSENT while RO routes return 200.

## Not done
Browser render of either home. Full verb-level split of all 191 V1 APIs. Download of the Drive master plan. Any product code change.
