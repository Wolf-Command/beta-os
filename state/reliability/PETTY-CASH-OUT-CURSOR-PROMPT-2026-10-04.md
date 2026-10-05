# CAPTAIN-PETTY-CASH-OUT-2026-10-04

You are editing ONLY the Beta workspace at /Users/wolfterminal/beta-os. Do not commit. Do not push. Do not merge PR #1. Do not reset, stash, or clean. Do not restart Beta or production. Do not touch production (port 8787, pid 15975). Do not signal beta pid 33020. Do not touch close VDC-470e741f. Leave cursor-agent pid 63443 alone. Do not run recover-watchdog. Code and tests only on Beta. Do not put secrets, API keys, cookies, or process command lines in any file you write.

## Approved scope (this slice only)

Captains and above may record **petty cash OUT only**, through assignment capability `petty_cash.record_out`.

### In scope
- Capability-gated **petty cash OUT** recording for Captains and above via `petty_cash.record_out`.
- Required fields for each OUT:
  - business
  - outlet
  - business date
  - transaction time
  - amount
  - category
  - reason
  - payee where applicable
  - person recording
  - evidence/photo
  - receipt where available
  - linked purchasing item
  - accounting mapping
  - audit
- Missing receipt is an **evidence exception**, not zero, and not completed proof.
- That day's petty cash OUT must flow into the **Uma daily close** cash reconciliation:
  - opening float where configured
  - cash sales
  - petty OUT
  - other authorised movements
  - expected closing cash
  - counted cash
  - difference
- Flow must avoid double count and must avoid staff retyping transactions already in Wolf.
- Beta only. Tests on copies only.

### Out of scope / forbidden
- Petty cash **IN**
- Self-approval where separation of duties forbids it
- History edits
- Audit deletes
- Bank movement
- Petty-cash config changes
- Hardcoding Iza or any person id (use assignment / capability routing)
- Editing or rewriting production
- Rewriting the 3 Oct close (including close VDC-470e741f and its evidence/audit)
- Restarting servers, committing, pushing, merging PR #1, recover-watchdog

## Implementation expectations
1. Gate OUT recording on assignment capability `petty_cash.record_out` for Captains and above.
2. Capture all required fields; treat missing receipt as evidence exception status, not a zero amount and not as completed proof.
3. Wire same-day petty OUT into Uma daily close expected cash math without double counting and without forcing re-entry of Wolf transactions.
4. Keep separation of duties: no self-approval path where policy forbids it; do not hardcode person ids.
5. Tests must use temporary/copy databases or fixtures. Tests must never write or rewrite the protected 3 Oct close.

## Deliverable
Implement the Beta-only slice above. py_compile Python you edit. Write a short result note under `state/reliability/` describing files changed, tests run and results, what you deliberately did not change, and status `IMPLEMENTATION_DONE` or `BLOCKED`. Do not claim HUMAN PASS. Stop when fixes are saved and tests have been run.
