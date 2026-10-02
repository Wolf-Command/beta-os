# IZA-ASSIGNMENT-RESOLUTION-1 RESULT

**As of:** 2026-10-02 WITA · **Branch:** `build/wolf-command-rebuild` (local only — no push)  
**Decision:** extends `2026-09-17 · Uma Blu Daily Close` + Owner order `IZA-UMA-CAPTAIN-CASHIER-DAILY-CLOSE-20261002` / pack `IZA-ASSIGNMENT-RESOLUTION-1`  
**Incident:** Iza CF OK (`izazaen00@gmail.com`) → UI **Access denied — This close is not on your assignment.**  
**Flags:** `staff_ready=false` · `human_commissioned=false` until Iza real PASS

## Root cause

`/uma-blu-close` page gate used only `active_role_ids ∩ hard role set` and ignored `venue_closer_roster` → Assignment → tonight’s open Uma close. Live Beta process also started **before** Captain⊇Cashier tip (`19:56` vs Captain land `~20:17`), so even ROLE-BZG-CAPTAIN in source was not loaded.

## Fix (reusable)

1. **`venue_close.person_authorised_for_venue_close`** — ACTIVE `venue_closer_roster` + ACTIVE Assignment + closer role (CLOSER/CAPTAIN/CASHIER) + brand scope → ALLOW. Oversight roles (HFB / FB-OPS-LEAD / MATT / OWNER) ALLOW without roster. No email special-case. No person-per-day invent.
2. **`venue_close.take_open_venue_close`** — take/submit attribution (`taken_by_person_id` / `taken_at`). Concurrent take → **409** + audited `DENIED concurrent_take`. Same person idempotent.
3. **`serve_beta.py`** `/uma-blu-close` + `/bzg/daily-close` gate calls roster resolution (not hard role set alone).
4. **`bzg_daily_close.open_human_close`** — authz then open then take.

## Independent verify (Iza identity path)

| Check | Result |
| --- | --- |
| `resolve_verified_person(izazaen00@gmail.com)` | PERS-IZA |
| `person_authorised_for_venue_close(PERS-IZA)` | ALLOW via roster `VCR-UMA-2` / ROLE-BZG-CAPTAIN |
| Unsigned `GET :8788/uma-blu-close` | **403** `authz_reason=anonymous` |
| Beta restarted | listen pid refreshed with new gate |

## Tests

| Suite | Result |
| --- | --- |
| `scripts/tests/test_iza_assignment_resolution_1.py` | **pass=23 fail=0** |
| `scripts/tests/test_iza_uma_captain_cashier_1.py` | **pass=41 fail=0** |
| `scripts/tests/test_bzg_daily_close_till_edc_1.py` | **pass=57 fail=0** |
| `scripts/tests/test_bzg_daily_close_multi_edc_vision_1.py` | **pass=77 fail=0** |

Pack cases: Iza ALLOW · Devi ALLOW · unauthorised BZG DENY · wrong outlet DENY · inactive assignment DENY · anonymous DENY · direct URL DENY · concurrent take audited.

## Honesty

- `staff_ready=false` · `human_commissioned=false`
- Prod `:8787` READ-ONLY untouched
- No RBAC grant loosen · no Iza email ACL · multi-closer VCR-UMA-1/2 preserved

## Files

- `scripts/core/venue_close.py`
- `scripts/core/bzg_daily_close.py`
- `scripts/serve_beta.py`
- `scripts/tests/test_iza_assignment_resolution_1.py`
- `scripts/tests/test_iza_uma_captain_cashier_1.py` (gate assertion)
- `scripts/tests/test_bzg_daily_close_till_edc_1.py` / `test_bzg_daily_close_multi_edc_vision_1.py` (test roster seed)

## Next human

Peaches → Matt: **RETEST IZA NOW** at `https://beta.wolfcommand.net/bzg/daily-close` (or `/uma-blu-close`).

RESULT: **PASS** (engineering). Human commissioning PENDING.
