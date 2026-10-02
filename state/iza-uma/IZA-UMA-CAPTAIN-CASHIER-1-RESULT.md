# IZA-UMA-CAPTAIN-CASHIER-1 RESULT

**As of:** 2026-10-02 WITA · **Branch:** `build/wolf-command-rebuild` (local only — no push)  
**Decision:** Owner order `IZA-UMA-CAPTAIN-CASHIER-DAILY-CLOSE-20261002` (`credit_override=OWNER_ORDER`)  
**HR:** `BZG26023002` Iza Zainatulloh Hulhidayati · Floor Captain · `izazaen00@gmail.com`  
**Prod `:8787`:** READ-ONLY untouched (pid 15975)  
**Flags:** `staff_ready=false` · `human_commissioned=false`

## What landed

### Person + auth
- `PERS-IZA` ACTIVE — display/legal **Iza Zainatulloh Hulhidayati** (HR verbatim)
- `AUTH-IZA-EMAIL` provider=email identifier=`izazaen00@gmail.com`
- No emp/salary/bank fields written into `org_persons` (HR emp `BZG26023002` in migration comment only)

### Roles (composition, not person fork)
- `ROLE-BZG-CASHIER` · Cashier · DEPT-BZG-FB · OPERATING · SPECIFIED
- `ROLE-BZG-CAPTAIN` · Floor Captain · DEPT-BZG-FB · OPERATING · SPECIFIED
- Identical **CASHIER_BUNDLE** grants on both (reuse existing permission_ids):
  `venue.close.read/submit`, `evidence.record.read/submit`, `work.read/update/complete`
- No finance / bank / Owner / admin / HR / AMG / GGV grants

### Position / Assignment / Scope
- `POS-BZG-CAPTAIN-UMA-1` → ROLE-BZG-CAPTAIN · ENT-BZG · BZG-UMA · DEPT-BZG-FB · `Floor Captain · Uma Blu`
- `ASG-IZA-CAPTAIN-UMA-1` ACTIVE primary for PERS-IZA
- Scope **SCOPE-BZG-UMA only** (not ENTITY / finance / AMG / GGV)

### Multi-closer roster
- `VCR-UMA-2` ACTIVE — PERS-IZA / POS-BZG-CAPTAIN-UMA-1 / ASG-IZA-CAPTAIN-UMA-1
- `VCR-UMA-1` Devi **untouched** (still ACTIVE)
- ACTIVE variance policies still **0** · EDC terminals still **0** (NEEDS CONFIGURATION)

### UI ACL
- `serve_beta.py` close_roles for `/uma-blu-close` + `/bzg/daily-close` includes **`ROLE-BZG-CAPTAIN`** (reusable — no PERS-IZA / email hardcode)

## Prove (engineering)

| Check | Result |
| --- | --- |
| `active_role_ids(PERS-IZA)` | includes `ROLE-BZG-CAPTAIN` |
| `rbac.evaluate(PERS-IZA, venue.close.submit, ENT-BZG/BZG-UMA)` | ALLOW |
| finance.* / AMG / GGV evaluate | DENY / no grant |
| Unsigned `GET :8788/uma-blu-close` | **403** |
| Migration idempotent re-run | PASS |
| CF login binding | Owner-gated checklist only — **not claimed live** |

## Tests

| Suite | Result |
| --- | --- |
| `scripts/tests/test_iza_uma_captain_cashier_1.py` | **pass=43 fail=0** |
| `scripts/tests/test_uma_blu_daily_close.py` | **71 passed, 0 failed** |
| `scripts/tests/test_bzg_daily_close_till_edc_1.py` | **pass=57 fail=0** |

## Commissioning honesty

- `staff_ready=false` · `human_commissioned=false`
- Gmail draft: already exists — **not duplicated**
- CF Access Allow for `izazaen00@gmail.com` = **Owner gate** (Matt) — eng does not claim CF live
- Tonight Daily Close controls unfinished (EDC NEEDS CONFIGURATION, variance empty) — **not bypassed**

## Files

- `scripts/migrations/migrate_iza_uma_captain_cashier_1.py`
- `scripts/serve_beta.py` (close_roles +ROLE-BZG-CAPTAIN)
- `scripts/tests/test_iza_uma_captain_cashier_1.py`
- `state/iza-uma/IZA-UMA-CAPTAIN-CASHIER-1-RESULT.md` (+ `.json`)

RESULT: **PASS** (engineering). Human commissioning PENDING · CF binding Owner-gated.
