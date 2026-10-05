# PETTY-IZA-FAIL-REPAIR — Result

**Finished:** 2026-10-04 WITA · **Status:** ENG_PROVED · **ready_for_human_test:** yes · **human_commissioned:** no · **staff_ready:** false

## Defects fixed

| # | Defect | Fix |
|---|--------|-----|
| 1 | Outlet dropdown | Removed. Outlet derived server-side from assignment → scope → `BZG-UMA` / Uma Blu. Client-supplied wrong outlet → `outlet_forbidden` (403). |
| 2 | GL on Captain form | Removed from UI and POST body. GL applied downstream via `resolve_category_accounting_code`; unmapped → `NEEDS_ACCOUNTING_CLASSIFICATION`, movement still saved. |
| 3 | Category list | Alchemist `petty_cash` operational master (not A&G GL labels). |
| 4 | Balance Rp0 | Reconciled from movement chain + reference anchors. **Derived Rp54,000**; owner-stated Rp55,000 → **gap Rp1,000 shown** (not forced). |
| 5 | Iza's two notas | Found persisted, counted once each (see below). |
| 6 | Phone layout | PETTY CASH → Uma Blu (locked) → balance → today's out → form → ledger. |
| 7 | Daily close once | Proved on temp 2026-10-04 path; protected 3 Oct closes untouched. |
| 8 | Security | Captain OUT only; no IN; no outlet/GL override; missing receipt = exception. |

## Outlet lock

- `resolve_petty_outlet_for_person` → `bzg_outlet_registry.outlets_for_person` → `BZG-UMA` / Uma Blu
- POST with `outlet: "Pool Bar"` → `outlet_forbidden`
- GET returns `outlet_locked: {display_name, outlet_id, locked: true}`

## Balance derivation

| Item | IDR | Source |
|------|-----|--------|
| 4 Oct reference opening | 505,000 | `PETTY-CHAIN-VERIFICATION-ANCHORS.json` (verification only — not ledger write) |
| 4 Oct OUT total | 451,000 | Wolf movements (430,000 + 21,000) |
| **Derived balance** | **54,000** | 505,000 − 451,000 |
| Owner stated | 55,000 | Reference anchor |
| **Gap** | **1,000** | Shown on phone — not forced to 55,000 |
| 3 Oct OUT verified | 555,000 | Movement sum (490k + 50k + 15k) |

Stale Oct-02 day row opening (Rp56,000 human-supplied) superseded when today has no proven opening.

## Iza's notas (found, counted once)

| movement_id | amount | purpose | category |
|-------------|--------|---------|----------|
| PETTY-UMA-6E512800FE | 430,000 | Nasi bungkus | Staff |
| PETTY-UMA-80867C2504 | 21,000 | Laundry | Supplies |

## Tests

```
python3 scripts/tests/test_petty_iza_fail_repair_20261004.py  → PASS 30 / FAIL 0
python3 scripts/tests/test_petty_surface_20261004.py          → PASS 26 / FAIL 0
python3 scripts/tests/test_petty_cash_record_out_20261004.py  → PASS 31 / FAIL 0
```

Temp schema-only sqlite. No live catalog copy.

## Processes

| Listener | PID | Action |
|----------|-----|--------|
| Beta (`serve-beta`) | 28164 | Reloaded via `launchctl kickstart` |
| Production (`serve.py :8787`) | 1297 | **Not restarted** |

## Protected closes (unchanged)

- `VDC-470e741f-d889-437a-9a40-1ec9c083fb95` — EXCEPTION — `updated_at=2026-10-03T13:47:39Z`
- `VDC-87202768-55af-4c8e-abc3-382a5496b8c6` — CANCELLED — `updated_at=2026-10-03T12:32:22Z`
