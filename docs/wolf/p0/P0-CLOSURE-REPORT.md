# P0 closure report

Pack S3. 27 Sep 2026. Owner brief 27 Sep 2026 16:32 WITA.

TECHNICAL PROOF is the ledger read, the war-room suite, and the twelve pack files named below. DEPLOYED ROUTE PROOF is the unsigned Beta check this session. STAFF READINESS stays 0/77. HUMAN COMMISSIONING stays 0/77. OPERATING ADOPTION stays 0/77 and NOT MEASURED. A passing suite is not a seated walk.

Production `:8787` stayed pid 15975. Beta `:8788` stayed pid 78725. It was not restarted. No money, bank, payment, ESB, or NAS write. No ledger row was raised.

## Four counts

These are separate. None of them is inferred from another.

| Count | Figure | Evidence |
| --- | --- | --- |
| SYSTEM | 19.65 / 77 = 25.52% | `build_war_room()` this session. Source `state/model-c-baseline-assessments.json`. Counts ABSENT 1, SPECIFIED 41, BUILT 20, PROVEN 12, READY 3. |
| STAFF READY | 0/77 | Every row in `state/completion-register/COMMISSIONING-STATE-20260927-w3p5.json` and `GAP-REGISTER-20260927.json` has `staff_ready` false. The war room returns `staff_ready_count` 0. |
| HUMAN COMMISSIONED | 0/77 | The same two files have `human_commissioned` false on every row. No seated Cloudflare session was observed. |
| OPERATING ADOPTION | 0/77 (NOT MEASURED) | Every w3p5 commissioning row says NOT MEASURED. Zero capabilities have an adoption measurement. That is not a measured usage rate of zero. |

`scripts/tests/test_completion_war_room.py` this session: PASS=227 FAIL=0. The ledger hash matched its backup before and after. Previously green Uma and progress suites are recorded under Verification.

## The twelve

Queue states this session: CLOSED 1, READY_FOR_HUMAN 1, BLOCKED_OWNER 2, WAITING_EXTERNAL 0, OPEN 8.

OPEN is not CLOSED, READY_FOR_HUMAN, WAITING_EXTERNAL, or BLOCKED_OWNER. Those eight stay OPEN. This report does not promote them.

### 1. CAP-CORE-02 — Person & Auth Identity

- BEFORE: SYSTEM READY (1.00). Staff ready no. Human commissioned no. `test_real_auth_binding.py` was PASS=44. Unsigned and a bad JWT were 403. `GET /signout` was 404.
- AFTER: Sign-out is deployed. `test_real_auth_binding.py` PASS=51 in the pack file. This session, on Beta pid 78725, unsigned `GET /signout` is 302 to the Access application logout, and unsigned `GET /api/core/me` is 403 `missing_auth`. No seated 200 was observed.
- EVIDENCE: `docs/wolf/p0/P0-CAP-CORE-02-RESULT.md`. Commit `8247252`. Walk: `docs/wolf/p0/HUMAN-TESTS.md`.
- FINAL STATE: READY_FOR_HUMAN. The three sign-ins and the sign-out check are not done. Nobody is commissioned.

### 2. CAP-INTG-07 — Secrets & Environment Separation

- BEFORE: SYSTEM SPECIFIED (0.05). The 2026-09-18 owner audit rejected PROVEN. Repo hygiene was not a vault prove.
- AFTER: The 27 Sep search named the plaintext directory from the 2026-07-21 decision. 1Password has no account. No second vault was built. Ledger stays SPECIFIED.
- EVIDENCE: `docs/wolf/p0/P0-CAP-INTG-07-RESULT.md`. Commit `44cd296`.
- FINAL STATE: BLOCKED_OWNER. Matt names the vault product, or writes that none is authorised.

### 3. CAP-MSC-02 — Access & Cloudflare Posture

- BEFORE: SYSTEM BUILT (0.25). The public hostname already redirected to Access login. The 2026-09-20 review covers an empty framework.
- AFTER: Unsigned, a spoofed email, `X-Wolf-Subject`, and a bad JWT are 403 on `/api/core/me`, `/api/msc/posture`, and `/wolf` in the pack file. This session, unsigned `GET /api/core/me` on pid 78725 is 403, and `https://beta.wolfcommand.net/api/core/me` returns 302 to the Access login. No review note binds this deny prove. Ledger stays BUILT.
- EVIDENCE: `docs/wolf/p0/P0-CAP-MSC-02-RESULT.md`. Commit `025dd13`. `scripts/tests/test_cap_msc_02_live_gate.py` SUMMARY pass=38 fail=0 in that file.
- FINAL STATE: OPEN. The deny half passed. The review half is absent. That absence is not an owner business decision, and it is not a named external provider. This pack did not write the review and did not call Grok.

### 4. CAP-CORE-01 — Organisation Registry

- BEFORE: SYSTEM PROVEN (0.80). The entity list was already fail-closed. On pid 59914 an unsigned read of a real entity returned 200.
- AFTER: Commit `99f5a27` uses `organisation.entity.read` on those reads. The pack file records 403 for unsigned, spoofed, subject, and bad JWT on pid 64196. No seated 200 was observed. Ledger stays PROVEN.
- EVIDENCE: `docs/wolf/p0/P0-CAP-CORE-01-RESULT.md`. `scripts/tests/test_cap_core_01_live_gate.py` SUMMARY pass=123 fail=0 in that file. `test_org_registry.py` was pass=35 fail=3 on the pre-existing census checks. Those were not repaired.
- FINAL STATE: OPEN. The seated allow and deny were not observed. There is no separate org acceptance to commission.

### 5. CAP-CORE-03 — Role / Position / Assignment

- BEFORE: SYSTEM PROVEN (0.80). `ASG-HAIKAL-CD-1` was ACTIVE and primary. `ASG-HAIKAL-VE-1` was ENDED. The board routes did not check identity.
- AFTER: Commit `5a814fe` gates the board with `organisation.role.read`. Live persons stayed 6. Live assignments stayed 10. No grant was added. No seated 200 was observed. Ledger stays PROVEN.
- EVIDENCE: `docs/wolf/p0/P0-CAP-CORE-03-RESULT.md`. `scripts/tests/test_cap_core_03_live_gate.py` SUMMARY pass=172 fail=0 in that file. `test_role_position_assignment.py` was exit 1, pass=33 fail=5, on the pre-existing census checks. Those were not repaired.
- FINAL STATE: OPEN. The seated assignment read was not observed.

### 6. CAP-CORE-04 — Permission & Authority Engine

- BEFORE: SYSTEM PROVEN (0.80). `GET /api/core/permissions` did not check identity. People are not roles. An ended assignment does not grant.
- AFTER: Commit `c49237f` gates the catalog with `organisation.role.read`. Live `org_permissions` stayed 79. Live `org_role_permissions` stayed 139. No grant was added. No seated 200 was observed. Ledger stays PROVEN.
- EVIDENCE: `docs/wolf/p0/P0-CAP-CORE-04-RESULT.md`. `scripts/tests/test_cap_core_04_live_gate.py` SUMMARY pass=116 fail=0 in that file. `test_rbac_permissions.py` was exit 1, pass=39 fail=4, on the pre-existing scope checks. Those were not repaired.
- FINAL STATE: OPEN. The seated statuses for Haikal, Devi, and Matt on the four routes were not observed. The CAP-CORE-02 walk is not commissioning of this row.

### 7. CAP-CORE-05 — Authority Limits Evaluator

- BEFORE: SYSTEM PROVEN (0.80). The evaluator already denies when no limit row matches. Live `org_authority_limits` was 0. That 0 is a row count, not a tolerance.
- AFTER: On a deleted catalog copy, `PERS-MATT` and `PERS-HAIKAL` were denied. An email string was not an allow. Live count stayed 0. Ledger stays PROVEN.
- EVIDENCE: `docs/wolf/p0/P0-CAP-CORE-05-RESULT.md`. Commit `fcae665`. `scripts/tests/test_cap_core_05_empty_deny.py` SUMMARY pass=39 fail=0 in that file. `test_authority_limits.py` was pass=48 fail=1 (`scope required denied`, already in D1). That fail was not repaired.
- FINAL STATE: CLOSED. The closure test is the empty-table deny plus live count 0. The broader Beta prove that would raise READY was not observed and is not claimed.

### 8. CAP-CORE-06 — Work Items / Promises / Decisions

- BEFORE: SYSTEM PROVEN (0.80). Live `core_work_items` was 0. There was no stored live row to replay.
- AFTER: One item on a deleted copy walked OPEN, IN_PROGRESS, BLOCKED, IN_PROGRESS, COMPLETED, VERIFIED. Verify from IN_PROGRESS was denied. Live count stayed 0. Unsigned routes are 403 in the pack file. No seated read was observed. Ledger stays PROVEN.
- EVIDENCE: `docs/wolf/p0/P0-CAP-CORE-06-RESULT.md`. Commit `2229b21`. `scripts/tests/test_cap_core_06_trail.py` SUMMARY pass=48 fail=0 in that file.
- FINAL STATE: OPEN. The seated read of the empty live list was not observed. A live work item was not created to fill it.

### 9. CAP-CORE-07 — Approval Engine

- BEFORE: SYSTEM PROVEN (0.80). Live `core_approval_requests` was 0. Live `core_approval_decisions` was 6. Live `core_governance_policies` was 1.
- AFTER: On a deleted copy, `PERS-MATT` listed zero requests. No policy row was inserted. Live requests stayed 0. Live decisions stayed 6 in that prove. The stored policy is `GPO-HABITAT-CONTENT-PUBLISH`. It is not a wide production pack. Unsigned routes are 403 in the pack file. No seated read was observed. Ledger stays PROVEN.
- EVIDENCE: `docs/wolf/p0/P0-CAP-CORE-07-RESULT.md`. Commit `ab4af72`. `scripts/tests/test_cap_core_07_route.py` SUMMARY pass=56 fail=0 in that file. `test_approval_engine.py` was pass=57 fail=3 on the live decision count 6, already in D1. Those were not repaired.
- FINAL STATE: OPEN. The seated read is absent, so this row is not BLOCKED_OWNER yet. After that read, it is still not CLOSED unless Matt has authored a wide pack or written that none is authorised.

### 10. CAP-CORE-08 — Segregation of Duties

- BEFORE: SYSTEM PROVEN (0.80). A submitter who verifies their own resolved close was already denied. Live `core_sod_constraints` was 0.
- AFTER: On a deleted copy, `PERS-MATT` verifying his own resolved close stayed `RESOLVED` with `sod_self_close`. A display name and an email were forbidden. `PERS-DEVI` on the F&B operations lead role does not hold verify. `ROLE-BZG-CLOSER` has no active assignment. Live constraint count stayed 0. No cash amount was written. Ledger stays PROVEN.
- EVIDENCE: `docs/wolf/p0/P0-CAP-CORE-08-RESULT.md`. Commit `e2cab4f`. `scripts/tests/test_cap_core_08_self_close.py` SUMMARY pass=73 fail=0 in that file. `test_sod_constraints.py` was exit 1, PASS=42 FAIL=2, then an `ApprovalError` already recorded in D1. That was not repaired.
- FINAL STATE: BLOCKED_OWNER. Matt decides whether a broader finance pack is required. The live count 0 is the absence of that pack. It is not a finance rule.

### 11. CAP-CORE-09 — Evidence Requirements

- BEFORE: SYSTEM PROVEN (0.80). Live `core_evidence_records` was 3. The only ACTIVE requirement was `EVR-HABITAT-CONTENT-PUBLISH`. Live `core_approval_decisions` was 6.
- AFTER: Eight actions call the gate. Six stay not gated: `venue.close.declare_cash`, `venue.close.resolve_exception`, `venue.close.verify`, `ggv.nota.submit`, `uma.receive_goods`, `work.item.complete`. `scripts/tests/test_work_loop.py` left `EVD-50e827bd` invalidated, reason `P4-TEST cleanup`, at `2026-09-27T10:06:44Z`. The live evidence count is 4. Live `core_approval_decisions` is 9. Hard delete is refused. The trigger was not dropped. No requirement was inserted. Ledger stays PROVEN.
- EVIDENCE: `docs/wolf/p0/P0-CAP-CORE-09-RESULT.md`. Commit `9d0b83c`. `scripts/tests/test_cap_core_09_gate_list.py` SUMMARY pass=69 fail=0 against the count of 4. That pack's own result line is FAIL.
- FINAL STATE: OPEN. The list half passed. The count half failed. This session did not delete the residue and did not re-run `test_work_loop.py`.

### 12. CAP-CORE-10 — Exception / Override Governance

- BEFORE: SYSTEM PROVEN (0.80). The queue expected live `core_governance_exceptions` of 2. Owner Command listed only `REQUESTED` and `AUTHORISED`.
- AFTER: Commit `b0fa859` lists every stored exception for GGV, AMG, and BZG. Live count is 3, all REJECTED on `ENT-GGV`. `stored_count` is 3. `open_count` is 0. `cadence_done` is false. This session, unsigned `GET /api/owner/command` on pid 78725 is 403 `forbidden`. No seated 200 was observed. Ledger stays PROVEN.
- EVIDENCE: `docs/wolf/p0/P0-CAP-CORE-10-RESULT.md`. Commit `b0fa859`. `scripts/tests/test_cap_core_10_read.py` SUMMARY pass=47 fail=0 in that file. The count half failed.
- FINAL STATE: OPEN. READY_FOR_HUMAN is not met. The seated read, the count of 3 against a closure figure of 2, and the cadence are all still open. One look by Matt would not be the cadence and would not be commissioning.

## Remaining register

`build_war_room()` this session: P0 12, P1 20, P2 42, P3 3. Sale readiness is P2 (`CAP-SALE-01` is P2). It is not in the P1 wave.

The P1 wave is `docs/wolf/p0/P1-QUEUE.json`. It is not started. Eight P0 rows are still OPEN. The ones Cursor can still touch are not actionable: the review note was refused, the seated reads need a real session, and the evidence residue must not be deleted.

Top P1, in the brief's order (remove Matt from daily work, close money controls, let staff run the day, connect a real source, then sale readiness). A dependency that is not done is named on the row.

1. CAP-GGV-02 Publish Gate. SYSTEM READY (1.00). Queue READY_FOR_HUMAN. Haikal's round-3 walk is the human gate. Do not hold it for The One = 0, 4,787 unknown brand, or 124 preview failures.
2. CAP-BZG-03 Venue Daily Close. SYSTEM READY (1.00). Queue BLOCKED_OWNER. This session, `GET /api/venue-close/honesty` on pid 78725 is 200, `variance_policy_display` = BLOCKED BY BUSINESS POLICY, `live_variance_threshold` = 0. The closer seat is empty.
3. CAP-INTG-04 Bank Statement Connector. SYSTEM BUILT (0.25). Read, import, reconcile, and report only. No payment.
4. CAP-FIN-02 Bank Statement Ingest & Reconcile. SYSTEM BUILT (0.25). Requires CAP-INTG-04.
5. CAP-FIN-01 Wolf Accounting Core. SYSTEM BUILT (0.25). Books stay unavailable until Matt opens them. Do not type a balance.
6. CAP-INTG-02 ESB Connector. SYSTEM BUILT (0.25). Read-only truth. The war room human act still says ESB settlement is unavailable.
7. CAP-STRAT-02 Owner Radar. SYSTEM BUILT (0.25). Requires CAP-CORE-01, CAP-CORE-06, and CAP-CORE-07. Those three P0 rows are OPEN.
8. CAP-INTG-01 Yanolja Connector. SYSTEM ABSENT (0.00). Queue WAITING_EXTERNAL. Do not invent a feed. CAP-AMG-01 and CAP-AMG-04 wait on it.

P2 is 42. P3 is 3 (`CAP-GGV-05`, `CAP-AMG-07`, `CAP-BZG-07`). They stay in the follow-after list.

## Matt only

Plain words. Everything else stays with the system.

Decisions and policy:

- Name the vault product for Dev, Beta, and Production, or write that none is authorised.
- Decide whether a broader finance segregation pack is required. If it is, write it. The live constraint count 0 is not that pack.
- Write a wide production approval policy, or write that none is authorised. The Habitat publish policy is not that pack.
- Write a Uma cash-mismatch rule only if a mismatch must be closable. Until then the screen says BLOCKED BY BUSINESS POLICY. The row count 0 is not a tolerance.
- Open the finance books, or leave them unavailable.
- Accept the live evidence count of 4, or authorise a delete past the no-delete trigger. Neither was done. The same choice exists for the third rejected exception (live count 3, closure figure 2).

Commissioning:

- Haikal, Devi, and Matt each sign in on https://beta.wolfcommand.net, open the pages in `docs/wolf/p0/HUMAN-TESTS.md`, and sign out. Write down the statuses. That walk is not done.
- Haikal's content round: sign in, select a brand, find old media, search, preview a photo, preview a video, multi-select, download a ZIP, upload new footage, and confirm it arrived in the NAS library. Not done. A failure becomes a repair pack.
- Matt signs in, opens Wolf, and writes down the three stored exception ids and their statuses. One look is not the operating cadence.

Credentials:

- Vault values stay out of chat, logs, and source. This pack did not build a second vault and did not print a secret.
- Atrium hotel nightly backup is not called LIVE. Entering those credentials is a human action. This pack did not do it.

Seat identities:

- Name the person for the Uma closer seat, or leave `ROLE-BZG-CLOSER` empty. Devi's BZG F&B operations lead authority stays as it is.
- Name the person for the external accountant seat `POS-GGV-EXT-ACCT`, or leave it empty. Amanda's content grant is not that seat.
- Keep or change the stored primary assignment for the person who holds both Content Crew and General Manager. This pack did not move it.
- People are not roles. A display name is not an authorisation.

## What is left

`docs/wolf/wave3/WHAT-IS-LEFT-TO-FINISH-WOLF-COMMAND.md` was edited in place. It was 1,181 lines and is 1,040 lines. The capability set is still 77. No requirement was added. The twelve long P0 entries became one table. The closer note now repeats the sentence already on the honesty route: BLOCKED BY BUSINESS POLICY.

## Verification

- `scripts/tests/test_completion_war_room.py`: PASS=227 FAIL=0. Ledger unchanged.
- `scripts/tests/test_uma_ops_console.py`: PASS=24 FAIL=0.
- `scripts/tests/test_uma_daily_loop_finish.py`: PASS=47 FAIL=0. It printed production pid 15975 and Beta pid 78725.
- `scripts/tests/test_uma_blu_daily_close.py`: 71 passed, 0 failed.
- `scripts/tests/test_progress_dashboard.py`: 198 passed, 0 failed.
- `scripts/tests/test_blocker_explain.py`: PASS=55 FAIL=1. The failure is `issues page keeps Example label`. The S2 queue already recorded it. This pack did not edit that page. It was not repaired.
- Unsigned Beta pid 78725: `/api/core/me` 403 `missing_auth`; `/api/owner/command` 403 `forbidden`; `/signout` 302 Access application logout; `/api/venue-close/honesty` 200, display BLOCKED BY BUSINESS POLICY, threshold field 0.
- Public `https://beta.wolfcommand.net/api/core/me` 302 to the Access login.
- Production pid 15975 was alive after these checks.
- The twelve pack SUMMARY lines were not re-run. `test_work_loop.py` was not re-run, because it writes the live catalog and cannot delete what it leaves.

RESULT: FAIL
