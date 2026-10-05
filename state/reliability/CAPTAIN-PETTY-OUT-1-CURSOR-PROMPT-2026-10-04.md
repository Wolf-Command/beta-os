# CURSOR STDIN PROMPT — CAPTAIN-PETTY-OUT-1
# Captain Petty Cash OUT (armed ship queue item B)
# Paste entire file to cursor-agent stdin. Do not print process args.

Written: 2026-10-04 ~16:53 WITA (box arm artifact). Launch ONLY on Studio when control path is up.
Workspace: `/Users/wolfterminal/beta-os`
Launch form (operator only — never print argv here):
  `/Users/wolfterminal/.local/bin/cursor-agent -p --force --model composer-2.5 --workspace /Users/wolfterminal/beta-os`
  NO `--trust`. stdin = this prompt. `start_new_session`. One Cursor at a time. Leave private worker pid 63443 alone.
Branch: local Beta only. No push. No prod `:8787`.

Pack: `CAPTAIN-PETTY-OUT-1`
God Mode row: GM-017 (Captain petty cash)
Prior box evidence (do not treat as this launch): Peaches verify `PEACHES-VERIFY-CAPTAIN-PETTY-CASH-OUT-20261004.json` claimed migration `petty_cash_record_out_1`, tests 28/0, page `dashboards/bzg-uma-blu-petty.html`, route `/bzg/uma-blu/petty`, permission `petty_cash.record_out`. Re-read live Beta on Studio. Fill gaps. Do not invent a second parallel petty system. Do not claim human commissioned.

Target: BUILT → DEPLOYED BETA → ENGINEERING PROVED → READY FOR HUMAN TEST
`staff_ready` stays **false** until human.

---

## Mission

Ensure **Captain and above** may record authorised **PETTY CASH OUT** via **Assignment + scope**, on Beta Uma Blu (BZG), with full required fields, evidence exception behaviour, Daily Close expected-cash integration without double counting, and audit.

### Who may OUT

Grant / keep permission `petty_cash.record_out` (or equivalent already present) on roles that are Captain-and-above by role composition, e.g. standing grants named in prior verify:

- `ROLE-BZG-CAPTAIN`
- `ROLE-BZG-HFB`
- `ROLE-BZG-FB-OPS-LEAD`
- `ROLE-MATT`

Deny cashier-only / closer-only if that is the standing SoD (prior verify denied `ROLE-BZG-CASHIER`, `ROLE-BZG-CLOSER`).

**Code uses assignment + role + scope.** Do **NOT** hardcode Iza. `PERS-IZA` / `ASG-IZA-CAPTAIN-UMA-1` may appear in tests as an **example assignee** only.

### What OUT does NOT grant

This permission does **not** grant:

- PETTY CASH **IN** / top-up recording
- Bank movement
- Payment execution / release of money from bank
- History deletion or alteration of past movements
- Config / chart edits
- SoD bypass (approving own exception where policy forbids)

Missing required evidence → **EXCEPTION**, not fake completion, not zeroed amount, not silent success.

---

## Required fields (OUT record)

Every authorised OUT must capture:

1. **Business** (ENT-BZG)
2. **Outlet** (Uma Blu / BZG-UMA scope — required)
3. **Business date**
4. **Time**
5. **Amount** (must be > 0; no invented defaults)
6. **Category**
7. **Reason**
8. **Payee**
9. **Person** (authenticated actor bound to assignment)
10. **Evidence / receipt** (required for completed OUT; missing → EXCEPTION state)
11. **Accounting mapping** (must be present as a real mapping field / code path — do not invent CoA rows; if mapping config missing, STOP or EXCEPTION honestly)
12. **Audit** (who/when/what before-after)

---

## Daily Close integration

Same-day authorised OUT must integrate into Daily Close **expected-cash** so till math stays honest.

- **No double counting** of the same OUT in expected cash.
- Do **not** mutate protected close `VDC-470e741f-d889-437a-9a40-1ec9c083fb95` (business_date 2026-10-03, state EXCEPTION). Leave it unchanged.
- Do **not** mutate `VDC-87202768`.
- Do **not** invent or write openings `560000` / `505000` as ledger writes. Those figures appear in box finance notes as owner-confirmed arithmetic; they are **not** authorised writes from this pack.
- New closes / calculations may *read* petty OUT movements for the business date; they must not rewrite protected historical close rows.

---

## Scope fence

IN SCOPE:
- Captain+ OUT via assignment
- Fields above + evidence EXCEPTION path
- Expected-cash integration without double count
- Temp sqlite tests
- Gap-fill on existing petty page/API/migration if already partially present
- RESULT under `state/reliability/`

OUT OF SCOPE:
- Petty IN / bank / payment execute
- Rewriting protected closes
- Inventing opening balances
- GGV/AMG petty
- Prod, push, `--trust`
- Changing God Mode denominator 43
- Almond Milk recipe work
- Hardcoding Iza as the only captain

---

## Hard locks

- Beta only. No prod.
- Tests on **temp / schema-only sqlite**. NEVER `shutil.copy2` live `catalog/content_library.sqlite`.
- No invent operational OUT rows in live catalog for demo.
- `staff_ready=false`. No HUMAN COMMISSIONED claim.
- One Cursor. Leave pid 63443 alone.
- Prefer no commit while operator arm says no_commit; implement + test + RESULT; local commit only if Studio standing rule requires it. Never push.

---

## Implementation guidance

1. Re-read live Beta:
   - `dashboards/bzg-uma-blu-petty.html`
   - route `/bzg/uma-blu/petty` in `scripts/serve_beta.py`
   - `scripts/core/uma_ops_console.py`, `bzg_daily_close.py`, related petty modules
   - migration `petty_cash_record_out_1` if present
   - prior test `scripts/tests/test_petty_cash_record_out_20261004.py` if present
2. If already complete per this prompt: prove with tests, confirm protected close unchanged, stamp RESULT as ALREADY_PRESENT_PROVED (still `staff_ready=false`). Do not rewrite working code for theatre.
3. If gaps: smallest fix. Keep permission assignment-based. Ensure UI has no IN control for this seat. Ensure missing receipt → EXCEPTION.
4. Expected-cash: assert OUT counted once in reconciliation helper used by Daily Close for that business date.

---

## Prove (engineering)

- Permission evaluate ALLOW for Captain assignment on Uma scope; DENY without assignment / for cashier-only if SoD says so
- OUT create with all required fields persists + audits
- Missing evidence → EXCEPTION (not completed)
- No IN endpoint/control granted by this permission
- Expected-cash helper includes same-day OUT once (double-count test)
- Protected close `VDC-470e741f` row unchanged (read before/after in test or verify stamp)
- No writes of 560000 / 505000 openings
- No hardcoded `Iza` / `PERS-IZA` in production branch logic (tests may use as fixture subject)
- Tests temp sqlite only

---

## STOP conditions

STOP and write RESULT STOPPED if:

1. Prod path would be edited
2. Fixing expected-cash requires mutating `VDC-470e741f`
3. Accounting mapping requires inventing a CoA / journal set
4. Would need `shutil.copy2` of live content_library for tests
5. Cursor conflict with pid 63443
6. Scope expands into bank movement or petty IN

---

## Result file (required)

Write:

- `state/reliability/CAPTAIN-PETTY-OUT-1-RESULT-2026-10-04.md`
- `state/reliability/CAPTAIN-PETTY-OUT-1-RESULT-2026-10-04.json`

JSON minimum:

```json
{
  "pack_id": "CAPTAIN-PETTY-OUT-1",
  "finished_at_wita": "...",
  "status": "IMPLEMENTATION_DONE_LOCAL_PASS | ALREADY_PRESENT_PROVED | STOPPED | FAILED",
  "eng_proved": false,
  "staff_ready": false,
  "human_commissioned": false,
  "ready_for_human_test": false,
  "deployed_beta": false,
  "tests_pass": 0,
  "tests_fail": 0,
  "permission": "petty_cash.record_out",
  "protected_close_id": "VDC-470e741f-d889-437a-9a40-1ec9c083fb95",
  "protected_close_untouched": true,
  "no_opening_writes_560000_505000": true,
  "no_hardcoded_iza": true,
  "no_IN_granted": true,
  "evidence_missing_is_exception": true,
  "double_count_avoided": true,
  "stop_reason": null
}
```

`ready_for_human_test` true only when route + assignment gate + tests pass + page is not a shell + first real task is one real Uma Blu payment OUT with receipt. Still `staff_ready=false`.

---

## Exit

`EXIT:0` on honest done/STOP + RESULT.
`EXIT:1` on failed tests without RESULT.

Do not raise God Mode. Do not change denominator 43. Do not claim Studio work from the box.
