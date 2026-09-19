# Grok review — Devi Uma commission auth 275d1c7

Date: 19 September 2026 (2026-09-19 08:52 WITA)
Commit: `275d1c7c10c52f82b715b16e1210f722e00cc9b4`
Run: BF-devi-uma-commission-auth-20260919
Slice: BF-devi-uma-commission-auth-20260919
Reviewer: Peaches (independent of Cursor's own report)

## Verdict

**PASS.** Close the lane. Do not change the Model C ledger. SYSTEM stays unchanged.
HUMAN_COMMISSIONING_STATUS stays **NOT_DONE**. Cloudflare Access Include still **NEEDS_MATT** (no widen this slice).

## What landed

- All `/api/bzg/uma-blu/*` GET and POST now go through `_require_uma_ops` (identity + `venue.close.read` on ENT-BZG/BZG-UMA + active `SCOPE-BZG-UMA`) fail-closed.
- Unknown Uma Blu POST routes return 403 (payment / float invent not granted).
- ROLE-BZG-HFB kept; no invented `bzg.pr.payment_approve`; ROLE-BZG-CLOSER still 0 people.
- New tests `scripts/tests/test_devi_uma_commission_auth.py`; petty API test expects anon 403 + Devi 200.
- Commissioning claim `state/build-claims/devi-uma-today-commissioning-2026-09-19.json` — API_AUTH_GATE GATED, HUMAN NOT_DONE, CF NEEDS_MATT.
- Dirty WIP four files still unstaged only. No Production / ledger / CAP / CF Include edits.

## Independent prove (factory watch CONTINUE_PEACHES → GROK_REVIEW)

- `python3 scripts/tests/test_devi_uma_commission_auth.py` → **PASS=27 FAIL=0**
- `python3 scripts/tests/test_uma_petty_cash.py` → **PASS=53 FAIL=0** (note: this suite re-ACTIVATEs ENTITY — see soft note; ENTITY re-ended after)
- Live Beta pages `/bzg/uma-blu` `/bzg/uma-blu/petty` `/bzg/uma-blu/issues` `/uma-blu-close` → **200**
- Live anon `GET /api/bzg/uma-blu/today` → **403** (`missing_auth` / Cf-Access-Jwt-Assertion required)
- Production `GET http://127.0.0.1:8787/wolf.html` → **200** (read-only; untouched)
- Catalog after surgical re-end: ACTIVE scopes for ASG-DEVI-HFB-UMA-1 = `{SCOPE-BZG-UMA}` only; ENTITY ENDED
- Cursor log: EXIT: DONE · CURSOR_SHELL_EXIT=0 · CURSOR_DONE · HEAD was 0aad28a → 275d1c7

## Red team

| Attack | Result |
| --- | --- |
| No identity on Uma API | PASS — 403 missing_auth / forbidden |
| Amanda without Uma scope | PASS — 403 forbidden |
| Devi without SCOPE-BZG-UMA (patched list) | PASS — 403 required_scope SCOPE-BZG-UMA |
| Devi payment / float invent POST | PASS — 403 |
| Devi closer submit | PASS — 403 |
| Devi Progress / Progress honesty | PASS — 403 |
| Invent payment_approve grant | PASS — not in serve gate; HFB lacks code |
| Mark HUMAN COMMISSIONED | PASS — claim NOT_DONE; gate text clean |
| Stage dirty WIP / touch :8787 / CF Includes | PASS — not in commit |

## Soft note (not FAIL)

- `migrate_uma_blu_daily_close.upsert_asg_scope` ON CONFLICT forces `status='ACTIVE', end_at=NULL`. Running `test_uma_blu_daily_close` / petty suite (which calls it) **re-ACTIVATEs** Devi `SCOPE-BZG-ENTITY` after a surgical end. Re-ended again at finish (`fix_end_devi_entity_scope.py --apply`). Durable FIX (do not revive ENDED scopes on upsert) is a follow-up lane — not blocking this auth-gate PASS.
- Phone / CF seat for Devi still needs Matt to add `deviputu236@gmail.com` to Access Include before live human commissioning.

## Next

Auth gate FINISHED. HUMAN commissioning still NOT_DONE until Matt CF seat + Devi phone prove. Soft follow-up: stop daily-close migrate from reviving ENDED assignment scopes. SYSTEM unchanged.
