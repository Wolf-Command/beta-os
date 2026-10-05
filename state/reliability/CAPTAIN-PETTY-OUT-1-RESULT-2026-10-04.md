# CAPTAIN-PETTY-OUT-1 — Result

**Status:** `ALREADY_PRESENT_PROVED`  
**Finished:** 2026-10-04T18:58:00+08:00 (WITA)  
**Scope:** Beta only. No HUMAN PASS claimed. `staff_ready=false`.

## Verdict

Implementation from prior `CAPTAIN-PETTY-CASH-OUT-2026-10-04` slice is complete on Beta. This launch re-read live Beta, fixed the engineering test to comply with schema-only sqlite (no `shutil.copy2` of live catalog), re-proved all assertions, and confirmed protected close untouched.

## Engineering proof

```text
python3 scripts/tests/test_petty_cash_record_out_20261004.py
→ PASS=31 FAIL=0

python3 scripts/tests/test_petty_surface_20261004.py
→ PASS=24 FAIL=0
```

### Assertions covered

| Check | Result |
|-------|--------|
| `petty_cash.record_out` ALLOW Captain+ assignment on Uma scope | PASS |
| Cashier denied (SoD) | PASS |
| OUT create with required fields + audit | PASS |
| Missing receipt → `EVIDENCE_EXCEPTION` / `INCOMPLETE` (not fake completion) | PASS |
| IN direction blocked (`direction_forbidden`) | PASS |
| Expected-cash includes same-day OUT once (`double_count_avoided`) | PASS |
| Protected close `VDC-470e741f` not written by tests | PASS |
| No `560000` / `505000` opening writes | PASS |
| No hardcoded `PERS-IZA` in `uma_ops_console.py` | PASS |
| Tests use temp schema-only sqlite only | PASS |

## Live Beta (read-only)

| Item | Evidence |
|------|----------|
| Migration `petty_cash_record_out_1` | Applied in `catalog/content_library.sqlite` |
| Permission grants | `ROLE-BZG-CAPTAIN`, `ROLE-BZG-HFB`, `ROLE-BZG-FB-OPS-LEAD`, `ROLE-MATT` → ALLOW |
| Cashier/CLOSER | No ALLOW row for `petty_cash.record_out` |
| Page route | `GET /bzg/uma-blu/petty` → 200 |
| API route | `GET /api/bzg/uma-blu/petty` → 403 unauth (fail-closed; expected) |
| Protected close | `VDC-470e741f` state `EXCEPTION`, `updated_at=2026-10-03T13:47:39Z` unchanged |

## Gap fill this launch

- `scripts/tests/test_petty_cash_record_out_20261004.py` — refactored from live-catalog copy to schema-only bootstrap (matches `test_petty_surface_20261004.py` pattern); uses real ENT-BZG expense codes `5210` / `5220` from entity books.

## Deliberately not changed

- Petty IN / bank / payment execute
- Protected closes `VDC-470e741f`, `VDC-87202768`
- Opening balance writes (`560000` / `505000`)
- `staff_ready`, human commissioned claim
- Prod `:8787`, git push, commit

## Human test entry

Captain+ with `petty_cash.record_out` on Uma Blu assignment:

1. Open `https://beta.wolfcommand.net/bzg/uma-blu/petty`
2. Record one real authorised OUT with all fields + receipt photo
3. Confirm movement appears; missing receipt shows exception state
4. Confirm same-day Daily Close expected-cash reflects OUT once

`ready_for_human_test=true`. `staff_ready=false` until human commissions.
