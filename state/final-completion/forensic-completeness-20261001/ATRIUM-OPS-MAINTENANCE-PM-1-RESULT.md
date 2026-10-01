# ATRIUM-OPS-MAINTENANCE-PM-1 — Maintenance / preventive maintenance workflow

Eng proof only. `staff_ready` stays false. Not HUMAN_PROVEN. Not a Kanban board of fake WOs. Prod `:8787` health-checked only (not restarted, not written).

Decision served: 2026-10-02 PICK ATRIUM-OPS-MAINTENANCE-PM-1 in `~/.openclaw/wolf-output/decisions.md` (Owner order ATRIUM-OPS-FOUR-20261002).

## Job built

Deterministic AMG-first workflow on Beta:

asset register (CAP-MSC-01 `/api/msc/assets` SoT) → location → PM schedule → inspection/checklist → assigned role/person → due/overdue → issue → work order → priority → action → parts/vendor/cost (optional UNKNOWN) → evidence → verification → closed → next service date → history → recurring failure flag.

## Data

- Beta sqlite: `state/maintenance-pm/maintenance_pm.sqlite`
- Seed mirror: `state/maintenance-pm/amg-preventive-maintenance.seed.json` (copy of V1 19-task schedule)
- Tables: `pm_schedule`, `work_orders`, `wo_evidence` / `wo_history` / `wo_audit` (append-only triggers)
- V1 seed: read-only open of `~/.openclaw/workspace/wolf-system/state/amg-preventive-maintenance.json`; 19 tasks imported with provenance `v1:amg-preventive-maintenance.json#id=<task_id>`; V1 mtime unchanged; intervals not invented
- Asset SoT: CAP-MSC-01 `/api/msc/assets` — no second register; empty inventory stays honest
- Sinks Cloudbeds / ClickUp / Notion / Telegram: RETIRED (POST refused 405)
- Auto room block: refused (405)

## Live HTTP on `:8788` (after Beta kickstart)

| Path | Result |
|---|---|
| `GET /api/msc/maintenance-pm` | 200, register_state PARTIAL, schedule 19, overdue 16, staff_ready false |
| `GET /msc/maintenance-pm` | 200 desk HTML |
| `POST /api/msc/maintenance-pm/raise` | 200 create `WO-85BF33CD8EF1` (fire-safety) |
| `POST …/{id}/checklist` | 200 → checklist_complete |
| `POST …/{id}/action` | 200 → in_progress |
| `POST …/{id}/parts` | 200 cost_status UNKNOWN |
| `POST …/{id}/evidence` | 200 |
| `POST …/{id}/verify` | 200 → verified |
| `POST …/{id}/close` | 200 → closed; next_service_date 2027-03-31; room_block false |
| `POST …/room-block` | 405 `auto_room_block_refused` |
| `POST …/clickup` | 405 `sink_retired` |
| `GET :8788 /api/health` | 200 |
| `GET :8787 /api/health` | 200 (read only) |

## Tests

`scripts/tests/test_atrium_ops_maintenance_pm_1.py`: 54 passed, 0 failed (temp DB + in-process Beta + wiring checks).

## Register

`need.maintenance`: MISSING → PARTIAL (real PM schedule + WO workflow + API + desk). `staff_ready` remains false until human commission.

## Left undone

Human commission. Cross-entity (BZG) slice. Live barcode inventory (msc-asset empty — honest). Predictive intelligence. Parts/vendor catalogs (explicitly not invented).

## Forbidden preserved

No invent intervals/serials/rates. No Cloudbeds/ClickUp/Notion/Telegram revive. No auto room blocks. No prod `:8787` mutate. No second asset register. Honesty-only board was not counted as done.
