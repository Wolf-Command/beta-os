# PETTY-OWNER-CASH-IN-1 — surgical Beta repair

You are a cursor-agent working ONLY in `/Users/wolfterminal/beta-os` (Beta). Today is Monday 5 Oct 2026, Asia/Makassar (WITA).

This Owner order authorises this surgical repair now. It supersedes the older GOD-MODE note "do not rebuild Petty Cash" for THIS slice only. Do not edit `state/build-factory/GOD-MODE-DISPATCH.json`. Do not start another agent. Do not commit, push, merge, or clean the dirty tree. Do not touch production files, production port 8787, or production pid 1297. Do not stop finance, matching, or ready-to-pay workers. Leave `/Users/wolfterminal/.openclaw/workspace/wolf-system` alone.

Owner operational truth is NOT permission to edit the ledger. Uma Blu page currently shows Rp52,700. Physical target Rp55,000 is only valid if an actual count proves it. Do not invent Rp2,300. Do not force Rp55,000.

Provenance already written (read it, do not rewrite the numbers): `state/reliability/PETTY-BALANCE-PROVENANCE-2026-10-05.md`.

Live catalog the petty code reads: `catalog/content_library.sqlite` via `scripts/core/uma_ops_console.py` (`bzg_ops_petty_movements`, `bzg_ops_petty_days`). Page `dashboards/bzg-uma-blu-petty.html` shows `data.current_balance` from `reconcile_petty_balance`.

Proved displayed balance, do not change it by inserting money:
- Anchor: 2026-10-02 `opening_float` 56000, human_supplied by Matt Goss at 2026-10-01T23:52:23Z.
- Plus every `example=0` Uma movement with business_date >= 2026-10-02.
- Ends at Rp52,700 after PETTY-UMA-6E512800FE OUT 430000 (Iza) and PETTY-UMA-80867C2504 OUT 21000 (Iza).
- Excluded from the sum but must remain: PETTY-UMA-2321496C6D OUT 50000 on 2026-10-01.
- No `counted_amount`. No coin row. Rp2,300 is unproved. Do not insert it.

## Implement

1. Reconcile by proving ledger movements. Add a simple cash-count/reconciliation capability for Owner and authorised Finance only:
   Notes total, Coins total, Physical cash total, Ledger balance, Difference.
   Provenance required: who counted, when, outlet, business date, reason, evidence/notes.
   If coins of Rp2,300 are NOT already evidenced, do not post an adjustment. Show the difference as unproved. An audited opening/reconciliation adjustment may be recorded only when a real count is submitted through this control, and that submission must be a new immutable movement, never a silent overwrite.
2. Do not show this complexity to Captains during normal Cash OUT.
3. Permission bug: Matt (OWNER) on /bzg/uma-blu/petty only sees RECORD CASH OUT. He must also see CASH IN / TOP UP. Captains must not.
4. Authority via PERSON → ASSIGNMENT → ROLE → SCOPE → PERMISSION. Do NOT hardcode Matt, Iza, or any person. Do not add `if person_id == ...` allowlists.
   New explicit permissions: petty_cash.record_out, petty_cash.record_in, petty_cash.reconcile.
   `petty_cash.record_out` already exists from `scripts/migrations/migrate_petty_cash_record_out_1.py`. Extend that pattern; do not drop existing captain OUT.
   Owner assignment receives record_out, record_in, and reconcile.
   Captain receives record_out only.
   Authorised finance role receives record_in, record_out, and reconcile according to assignment+scope, and may classify in the Finance workflow. Accounting mapping must NOT appear on the operational petty page.
5. Captain: CASH OUT only. Cannot CASH IN. Cannot choose accounting mapping. Cannot change outlet. Cannot delete or edit history. Cannot move bank money.
6. Owner UX on Uma Blu petty page: two obvious actions, CASH OUT and CASH IN / TOP UP. Cash IN fields: Amount, Reason/Source, Evidence/photo where applicable. Person from authenticated user. Outlet from current workspace. Business date/time automatic. Audit event automatic. Do not require an accounting account to record the physical movement.
7. Outlet remains derived from workspace/context. Owner does not get a free outlet picker on this page; another outlet means entering that outlet workspace. Server must reject an outlet override in the request body.
8. Ledger: OPENING + CASH IN − CASH OUT = CURRENT BALANCE. Every movement immutable. Corrections supersede or reverse; never silently overwrite. Never create money to force a balance.
9. Daily Close stays simple. Captain does not see GL, journals, debits, credits, account codes, or finance classifications. Petty OUT reduces expected closing cash exactly once. Petty IN increases expected cash exactly once where the close model consumes it. No double count. Do not mutate the three protected close ids below. Do not rebuild Daily Close. Do not write 360000. Do not edit esb_totals_json.
   - VDC-470e741f-d889-437a-9a40-1ec9c083fb95 (3 Oct EXCEPTION, declared cash 3225000, variance -125000, updated_at 2026-10-03T13:47:39Z)
   - VDC-87202768-55af-4c8e-abc3-382a5496b8c6 CANCELLED
   - VDC-64f5f529-5485-4ff1-a0cc-11941a64e6f5 4 Oct Uma, DATA_CAPTURED, declared_cash_amount stays NULL
10. Tests, server-side not just UI, all must pass:
    1 Owner can record CASH IN on Uma Blu.
    2 Owner can record CASH OUT.
    3 Captain (Iza's role/assignment, not a hardcoded person id in production code; tests may use the existing captain fixture) can record CASH OUT.
    4 Captain CANNOT record CASH IN even by direct API.
    5 Outlet cannot be changed by manipulating the request.
    6 Cash IN changes balance exactly once.
    7 Cash OUT changes balance exactly once.
    8 Duplicate submit does not duplicate a movement.
    9 Evidence remains attached.
    10 Audit identifies actor, assignment, outlet, amount, type, timestamp.
    11 Daily Close consumes the relevant movement exactly once (prove with a fixture or by showing the close calculator reads the movement once; do not write the live protected closes).
    12 Existing real petty history unchanged (assert the two PETTY-UMA ids and the pre-repair balance provenance still match: displayed derived balance remains 52700, those two amounts unchanged, the 2026-10-01 OUT 50000 still present).
    Use a minimal isolated fixture or temporary database for tests. Do not copy the full library. Do not fake operational rows into the live catalog. Any CASH IN the tests insert must be in the fixture DB, not the live Uma ledger, unless the test harness rolls it back. Prefer fixture. The live displayed balance must be the same after tests.
11. Deploy/reload Beta only. staff_ready=false. Do not mark human commissioned. Prod untouched.
    HTML-only needs no reload. If Python changes, reload Beta ONLY if exactly one listener remains on 127.0.0.1:8788. Use `python3 scripts/beta_restart.py` (LaunchAgent kickstart of net.wolfcommand.serve-beta). Never reload or restart prod. Abort if more than one 8788 listener. Confirm prod pid is still 1297 afterwards.
12. Write the result file `state/reliability/PETTY-OWNER-CASH-IN-1-RESULT-2026-10-05.json` (and a short markdown sibling if useful) including: test counts, beta pid, prod pid still 1297, live balance before and after (must match unless a real non-test movement was intentionally not made — it must NOT be made), provenance path `state/reliability/PETTY-BALANCE-PROVENANCE-2026-10-05.md`, and the public URL https://beta.wolfcommand.net/bzg/uma-blu/petty
    Also set staff_ready false and human_commissioned false in that result. Do not claim coins were counted.

## Constraints while coding

- Do not insert Rp2300 or any adjustment into the live catalog.
- Do not UPDATE or DELETE existing `bzg_ops_petty_movements` rows.
- Do not copy `content_library.sqlite`.
- Tests must not leave new rows in the live Uma ledger.
- Permission grants go through role/assignment tables, not hardcoded people.
- Captain Cash OUT screen stays simple: no notes/coins reconciliation, no GL, no account picker, no outlet picker.
- Server rejects outlet override even for Owner.
- Idempotent submit (duplicate client token or same idempotency key must not double-post).
- Keep the live displayed balance Rp52,700 when you finish.

When done, stop. Do not commit.
