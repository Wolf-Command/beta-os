# ATRIUM-SOD-1 result (1C — visual repair after CF confirm)

29 Sep 2026. Beta only, branch `build/wolf-command-rebuild`. Continues 1B. Decision: `2026-09-29 · PICK: ATRIUM-SOD-1` + Matt UPDATE 14:10 + Matt CF confirm ~15:28. Production `:8787` pid **15975** READ ONLY. Local commits only. `BETA_AUTH_MODE` unset (unchanged). `staff_ready` / `human_commissioned` stay **false**. Nobody marked commissioned.

## 1C (this pass)

Peaches VERIFY FAIL on 1B shots → visual repair only (not READY / not commissioned).

| Fix | Evidence |
| --- | --- |
| SoD self-deny ≠ review | `atriumsod1-sod-self-deny-*` = SUBMITTED `JRN-ATRIUMSOD1B-SELF` (Zayen AR prep) with plain-language deny; `atriumsod1-zayen-review-*` = POSTED `JRN-ATRIUMSOD1B-COMM1` filter. Hashes distinct. |
| Posted GL ≠ empty history | `atriumsod1-zayen-posted-gl-*` = account **1020** with COMM1 Wolf-created debit Rp 50.000; `atriumsod1-gl-history-*` = account **1000** honest empty (0 posted / cutover copy). |
| Zayen My Work shows SOD cards | Scroll to plain-language REVIEW / APPROVE / POST (+ GL / temp AR in queue). Priority 1 on `COMM-ZAYEN-SOD-*`. |
| CF + AP activate (Peaches — do not undo) | `zenitalfathan@gmail.com` in CF Beta Allow (`state/access-evidence/cf-beta-allow-20260929.json`). AP WIs activated: `WI-c8ca39bc-…` PREPARE + `WI-d3bc4a01-…` SUBMIT (`state/atrium-sod/ap-activate-20260929.json`). Gmail onboarding draft already exists — no second draft. |
| AP prepare shots | Kept (`atriumsod1-ap-prepare-*`) — still accurate SoD on preparer seat. |

Shot script: `scripts/audit/atriumsod1_shots.py` (sidecar reload via `serve_atrium_finance.sh` after sqlite seed so Node memory matches).

## Structure

| Seat | Role | Position | Assignment | Person |
| --- | --- | --- | --- | --- |
| Financial Controller | `ROLE-AMG-FINANCIAL-CONTROLLER` | `POS-AMG-FINANCIAL-CONTROLLER-1` | `ASG-ZAYEN-FC-1` (primary) | Zayen |
| Accounts Payable | `ROLE-AMG-ACCOUNTS-PAYABLE` (“Accounts Payable”) | `POS-AMG-ACCOUNTS-PAYABLE-1` | `ASG-ZENITALFATHAN-AP-1` | `PERS-ZENITALFATHAN` · `zenitalfathan@gmail.com` · display `zenitalfathan` · legal_name **NULL** · Auth `AUTH-ZENITALFATHAN-EMAIL` ACTIVE |
| Accounts Receivable (temp) | `ROLE-AMG-ACCOUNTS-RECEIVABLE` (“Accounts Receivable”) | `POS-AMG-ACCOUNTS-RECEIVABLE-1` | `ASG-ZAYEN-AR-1` (non-primary) | Zayen — **ending later = data change only** |
| Finance Officer | `ROLE-AMG-FINANCE-OFFICER` | `POS-AMG-FINANCE-OFFICER-1` | **VACANT** | — |

## SoD proof

Server compares `journal.preparer_person_id` to actor `person_id`. Equal → **403** on approve (`sod_self_approve`) and post (`sod_self_post`), even when actor holds Controller. Zayen-as-AR prepare then FC self-approve = 403 (suite + live demo `JRN-ATRIUMSOD1B-SELF` archived after shot). UI titles plain language only.

## Workflow

`DRAFT → VALIDATED → SUBMITTED → APPROVED|RETURNED → POSTED → GL`. Return requires reason. Append-only `journal_workflow_audit`. No skips.

## Commissioning

- Journal `JRN-ATRIUMSOD1B-COMM1` prepared+submitted by AP (`PERS-ZENITALFATHAN`), then FC approve+post → **POSTED**, `wolf_created=1`, lines on **1020/4000**, commissioning memo attached (not a fake invoice).
- Legacy Owner interim `JRN-ATRIUMSOD1-COMM1` **ARCHIVED** (superseded).
- My Work: AP PREPARE/SUBMIT **ACTIVE** (CF confirmed); Zayen REVIEW/APPROVE/POST/GL + temp AR plain-language tasks (priority 1).
- Finding `FIND-ATRIUMSOD1-ZAYEN-PREPARER-SEAT` kept; 13:32 FAIL history not overwritten; 1B update appended in `state/atrium-sod/findings.md`.

## Historical ledger

Honest empty on parent **1000**: sources searched (see `state/atrium-sod/discovery.md`), nothing authoritative imported, cutover `2026-09-29`. Wolf-created commissioning posts appear on postable accounts (e.g. 1020) after Controller post — not historical hotel books.

## Tests (honest counts — 1C)

| Suite | Result |
| --- | --- |
| `test_atrium_sod1_20260929.py` | pass=**69** fail=**0** (AP WIs assert active-after-CF) |
| humfix1c | 54/0 |
| mywork1b | 53/0 · RESULT: PASS |
| humancomm1 | PASS=60 FAIL=0 |
| staff_access | 274/0 |

## Shots (`docs/wolf/ops/shots/`)

`atriumsod1-ap-prepare-{desktop,phone}.png` · `atriumsod1-zayen-review-{desktop,phone}.png` · `atriumsod1-zayen-posted-gl-{desktop,phone}.png` · `atriumsod1-zayen-mywork-{desktop,phone}.png` · `atriumsod1-gl-history-{desktop,phone}.png` · `atriumsod1-sod-self-deny-{desktop,phone}.png`

## Pids

| Process | Pid |
| --- | --- |
| Production `:8787` | **15975** (untouched) |
| Beta `:8788` | **22575** |
| Atrium sidecar `:8790` | **43398** (restarted for 1C shot reload) |
