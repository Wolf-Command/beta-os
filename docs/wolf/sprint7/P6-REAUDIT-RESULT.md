# P6 — Completion Register mechanical reaudit — 27 Sep 2026

77 capabilities. Credits locked in `docs/MODEL-C-SYSTEM-NUMERIC-CREDITS.md`: ABSENT 0, SPECIFIED 0.05, BUILT 0.25, PROVEN 0.80, READY 1.00. Catalog `docs/MODEL-C-CAPABILITY-CATALOG.md`. Live ledger `state/model-c-baseline-assessments.json` was read and not rewritten. No application code was changed. Production `:8787` stayed pid 15975. Beta `:8788` stayed pid 4443.

ENGINEERING PASS for the reaudit. Not staff ready. Not human commissioned.

## BEFORE

The canonical register is the 77-row ledger `state/model-c-baseline-assessments.json`, scored with `scripts/core/progress_read_model.py` `compute_system_from_ledger` and the locked credits. The completion-register JSON stubs under `state/completion-register/` are pack records. They are not a second 77-row score.

Counted from that ledger at the start of this run:

| state | caps | credit | subtotal |
| --- | ---: | ---: | ---: |
| ABSENT | 1 | 0.00 | 0.00 |
| SPECIFIED | 41 | 0.05 | 2.05 |
| BUILT | 20 | 0.25 | 5.00 |
| PROVEN | 12 | 0.80 | 9.60 |
| READY | 3 | 1.00 | 3.00 |
| **SUM** | **77** |  | **19.65** |

`19.65 / 77 × 100 = 25.519480…%`. Half-up to 1 decimal is **25.5%**. Half-up to 2 decimals is **25.52%**. The reported `19.65/77 = 25.5%` is arithmetically correct under the 1-decimal half-up used in `docs/deliveries/MODEL-C-EVIDENCE-RECON-2026-09-19.md`. It was not carried forward as tonight's score.

The three READY rows were CAP-CORE-02, CAP-GGV-02, and CAP-BZG-03. Model E dimensions have definitions and no approved measurement model (`docs/MODEL-C-CAPABILITY-CATALOG.md`, scoring rules §10, `MODEL_E_UNSCORED` in the progress read model).

## BUILT-REPAIRED

No application code. The ledger file was not rewritten. This run wrote `state/completion-register/REAUDIT-20260927.json` (77 rows) and this result.

Rule used: a cited proof suite that exits 0 can stay PROVEN. READY also needs staff-usable proof, which none of tonight's packs recorded for these capabilities. A red cited suite drops PROVEN or READY to BUILT when the code is still there. Pass counts do not raise a row. Skeletons whose own reviews say the owner ledger stays SPECIFIED were left SPECIFIED. Human commissioning is a separate false flag on every row.

12 rows changed, all downward:

| id | name | previous | new | why |
| --- | --- | --- | --- | --- |
| CAP-CORE-01 | Organisation Registry | PROVEN 0.80 | BUILT 0.25 | Cited proof scripts/tests/test_org_registry.py exited 1 on 2026-09-27 (PASS=33 FAIL=4: brand seed 12 not 7, Habitat brand, GGV client brands, invalid-entity 404). Implementation scripts/core/organisation.py remains. PROVEN needs a green suite. Not raised. |
| CAP-CORE-02 | Person & Auth Identity | READY 1.00 | BUILT 0.25 | READY withdrawn: staff Cloudflare sign-in on :8788 was not walked (P3/P4/P5). test_real_auth_binding.py PASS=44 FAIL=0, but cited test_person_auth_identity.py exited 1 (PASS=28 FAIL=4: 6 persons not 4, org_roles table now exists, person 404). Mixed suite is not PROVEN. Binding code remains. |
| CAP-CORE-03 | Role / Position / Assignment | PROVEN 0.80 | BUILT 0.25 | scripts/tests/test_role_position_assignment.py exited 1 (PASS=33 FAIL=5), including stale 'no org_scopes' and seed counts 12/10 not 4/4. Role module remains. Not PROVEN while the suite is red. |
| CAP-CORE-04 | Permission & Authority Engine | PROVEN 0.80 | BUILT 0.25 | test_rbac_permissions.py exited 1 (PASS=39 FAIL=4) and test_phase2_5a_permissions.py exited 1 (PASS=16 FAIL=10, including a stale :8787 pid check). RBAC code remains. Not PROVEN. |
| CAP-CORE-05 | Authority Limits Evaluator | PROVEN 0.80 | BUILT 0.25 | test_authority_limits.py exited 1 (PASS=48 FAIL=1: scope required denied). P4's work-loop pass does not restore this suite. Not PROVEN. |
| CAP-CORE-06 | Work Items / Promises / Decisions | PROVEN 0.80 | BUILT 0.25 | test_core_work_items.py exited 1 (PASS=49 FAIL=5: migrate exit 2, HTTP assign). P4 test_work_loop.py PASS=52 is a slice on temporary seats and is not staff-usable. Pass count does not keep PROVEN. |
| CAP-CORE-07 | Approval Engine | PROVEN 0.80 | BUILT 0.25 | test_approval_engine.py exited 1 (live decisions 6 not 0). test_dual_approval.py and test_approval_policy_binding.py raised ApprovalError: required permission denied. Engine code remains. Not PROVEN. |
| CAP-CORE-08 | Segregation of Duties | PROVEN 0.80 | BUILT 0.25 | test_sod_constraints.py raised ApprovalError: required permission denied. P4 showed one SoD denial on a temporary constraint, then removed it. Not a green SoD suite. Not PROVEN. |
| CAP-CORE-09 | Evidence Requirements | PROVEN 0.80 | BUILT 0.25 | test_evidence_requirements.py exited 1 (PASS=65 FAIL=8), live evidence records 3 not 0 and approvals 6 not 0. Implementation remains. Not PROVEN. |
| CAP-CORE-10 | Exception / Override Governance | PROVEN 0.80 | BUILT 0.25 | test_exception_override.py exited 1 (PASS=77 FAIL=11); live exceptions 2 not 0. Implementation remains. Not PROVEN. |
| CAP-GGV-02 | Publish Gate & Operator Loop | READY 1.00 | BUILT 0.25 | READY withdrawn. test_habitat_publish_gate.py exited 1 (live exceptions not 0). Content CRs staff_ready=false; Haikal retest required; P1 staff_ready false. Publish-gate code remains. Not PROVEN, not staff-usable. |
| CAP-BZG-03 | Venue Daily Close | READY 1.00 | PROVEN 0.80 | READY withdrawn: P5 STAFF READY no, no Cloudflare role session, no live closer, variance policies 0, settlement UNAVAILABLE. Automated proof did pass: test_uma_blu_daily_close.py 70 passed, 0 failed; P5 test_uma_daily_loop_finish.py PASS=44 FAIL=0. Cash-to-bank is not staff-finishable, so not READY. Petty-cash PASS=50 FAIL=3 and nav PASS=110 FAIL=1 stay red and do not raise this score. |
New counts: ABSENT 1, SPECIFIED 41, BUILT 31, PROVEN 4 (CAP-BZG-03, CAP-INTEL-02, CAP-INTEL-03, CAP-INTEL-04), READY 0.

**SUM = 13.00 / 77 × 100 = 16.883116…% → 16.88%** (half-up, 2 decimals).

Check: `1×0 + 41×0.05 + 31×0.25 + 4×0.80 + 0×1 = 2.05 + 7.75 + 3.20 = 13.00`.

## VERIFIED

Arithmetic of the previous ledger:

```
python3 ledger sum
n 77
{'PROVEN': 12, 'READY': 3, 'SPECIFIED': 41, 'BUILT': 20, 'ABSENT': 1}
sum 19.65
exact 25.51948051948051948051948052
1dp 25.5
2dp 25.52
```

Cited commits in the ledger all resolve with `git cat-file -t` (none missing). Cited test filenames exist.

Proof suites run tonight (`WOLF_TEST_MODE=1 PYTHONPATH=scripts`), exit codes:

```
test_org_registry.py                  EXIT 1  PASS=33 FAIL=4
test_real_auth_binding.py             EXIT 0  PASS=44 FAIL=0
test_person_auth_identity.py          EXIT 1  PASS=28 FAIL=4
test_role_position_assignment.py      EXIT 1  PASS=33 FAIL=5
test_rbac_permissions.py              EXIT 1  PASS=39 FAIL=4
test_phase2_5a_permissions.py         EXIT 1  PASS=16 FAIL=10
test_authority_limits.py              EXIT 1  PASS=48 FAIL=1
test_core_work_items.py               EXIT 1  PASS=49 FAIL=5
test_approval_engine.py               EXIT 1  pass=57 fail=3
test_dual_approval.py                 EXIT 1  ApprovalError: required permission denied: test.spend.approve
test_approval_policy_binding.py       EXIT 1  ApprovalError: required permission denied: test.spend.approve
test_sod_constraints.py               EXIT 1  ApprovalError: required permission denied: test.spend.approve
test_evidence_requirements.py         EXIT 1  pass=65 fail=8
test_exception_override.py            EXIT 1  pass=77 fail=11
test_delegation.py                    EXIT 1  DelegationError: delegate assignment not ACTIVE
test_habitat_publish_gate.py          EXIT 1  live exceptions not 0
test_uma_blu_daily_close.py           EXIT 0  70 passed, 0 failed
test_intel_orchestration.py           EXIT 0  PASS=65 FAIL=0
test_decision_memory.py               EXIT 0  PASS=85 FAIL=0
test_authorised_knowledge.py          EXIT 0  PASS=51 FAIL=0
test_authorised_knowledge_live.py     EXIT 0  PASS=36 FAIL=0  LIVE font=voice=conflict=empty=absent=PASS
test_metricool_isolation.py           EXIT 0  ALL PASS
```

Listeners after those runs:

```
PROD:15975
BETA:4443
```

One repair pass was not applied to application code. This pack forbids that. The repair is the lower scores.

Tonight's pack files read, not re-executed: `docs/wolf/sprint7/P1-CONTENT-RESULT.md` (staff ready no), `P2-FINANCE-RESULT.md` (Atrium scratch ledger staff-startable, backup no, human commissioned no), `P3-STAFFHOME-RESULT.md` (staff ready no), `P4-LOOP-RESULT.md` (staff ready no), `P5-UMA-RESULT.md` (staff ready no). P4's `test_work_loop.py` PASS=52 and P5's loop PASS=44 are recorded there. They were not used to raise any cap.

## STAFF READY?

NO.

READY is now 0 of 77. P1, P3, P4, and P5 each say staff ready no. P2's yes is an empty Atrium ledger on a scratch database in another repo, with backup unproven, and it does not make CAP-FIN-01 staff-usable group accounting. Content completion-register rows still have `staff_ready: false`.

## HUMAN COMMISSIONED?

NO

## BLOCKERS

- The Wolf Core proof suites named above are red on this catalog. Several failures are stale live counts (approvals 6, evidence 3, exceptions 2, persons 6) left by later packs. They still mean those suites are not a current PROVEN stamp.
- No Cloudflare staff session was opened on `:8788` tonight. Unsigned routes return 403.
- CAP-BZG-03 close tests pass and the live till still cannot finish a mismatch: variance policies 0, no person on `ROLE-BZG-CLOSER`, settlement UNAVAILABLE. Petty-cash suite PASS=50 FAIL=3 and nav suite PASS=110 FAIL=1 were already red in P5 and were not repaired.
- CAP-GGV-02 publish-gate suite is red and the content desk `staff_ready` flag is false.
- CAP-INTG-01 has no Yanolja connector. CAP-DR-01 and CAP-INTG-07 stay SPECIFIED because the owner rejected PROVEN on 2026-09-18, and P2 did not restore a backup.

## NEXT HUMAN TEST

Do not treat 25.5% as the current SYSTEM figure. The reaudit figure is 13.00/77 = 16.88%.

A person with a Cloudflare seat signs in on Beta `:8788` and opens `/my-work` and `/bzg/uma-blu`. That walk is the missing staff-usable proof. It does not, by itself, move any cap to READY or to human commissioned.

## FOUNDER DEPENDENCY

Operating Adoption, Data/Measurement, Founder Independence, Financial Control, and Sale Readiness: **no canonical model — not scored**.

Per capability, remaining Matt dependency. No new Matt dependency was added to get a row green.

| id | tag |
| --- | --- |
| CAP-CORE-01 | AUGMENT — org registry exists; changing the hierarchy is still an owner act, not a new Matt login. |
| CAP-CORE-02 | RETAIN — granting a Cloudflare seat stays an owner Access flip. Day-to-day JWT binding does not need Matt once the seat exists. Tonight's missing staff sign-in is not a new Matt step. |
| CAP-CORE-03 | AUGMENT — roles and assignments exist. Seating a person is a human act on the role, not a name key, and not a new Matt dependency. |
| CAP-CORE-04 | AUTOMATE — server RBAC denies without a grant. Matt is not in the allow path. |
| CAP-CORE-05 | RETAIN — limit values stay an owner setting. The evaluator does not add a Matt check to get a pass. |
| CAP-CORE-06 | ELIMINATE — P4 assigns work by role and scope. Matt is not the assignee key. |
| CAP-CORE-07 | RETAIN — a material decision still needs the authorised person. That person is not required to be Matt. |
| CAP-CORE-08 | AUTOMATE — same-person conflicts deny. No Matt bypass was added. |
| CAP-CORE-09 | AUGMENT — evidence is attached by the role that holds the work. Matt is not the uploader. |
| CAP-CORE-10 | RETAIN — authorising an exception stays an owner step. P4 leaves it REQUESTED. |
| CAP-CORE-11 | RETAIN — there is no SOP loop, so operating SOP changes still sit with the owner. No new Matt step was added. |
| CAP-CORE-12 | SIMPLIFY — delegation exists and is time-bounded in code. 7/30/90/365 burn-down is not proven, so accidental founder load is not yet measured out. |
| CAP-GGV-01 | AUTOMATE — NAS recheck and library search run without Matt. UNKNOWN folders and calling the desk staff-ready stay with a person who knows the brands, not a new Matt login. |
| CAP-GGV-02 | RETAIN — publish still needs the designated approver. staff_ready is false. Matt was not added as that approver. |
| CAP-GGV-03 | RETAIN — no client P&L machine. Commercial judgement stays outside Wolf. No new Matt dependency. |
| CAP-GGV-04 | AUGMENT — lead boards exist. Speed-to-lead is not a governed Matt-free SLA. |
| CAP-GGV-05 | AUTOMATE — Metricool read path and isolation checks run without a Matt post. Writes stay off. |
| CAP-GGV-06 | RETAIN — intercompany client mode is specified only. No Matt step was added to fake it. |
| CAP-AMG-01 | RETAIN — no Yanolja connector. Hotel facts stay in the PMS. No Matt integration was added. |
| CAP-AMG-02 | RETAIN — journey is specified. Empty operator depth does not create a Matt queue. |
| CAP-AMG-03 | RETAIN — packages are specified. No Matt price entry was added to look live. |
| CAP-AMG-04 | RETAIN — daily hotel state is specified. No invented occupancy. |
| CAP-AMG-05 | RETAIN — yield is specified. No invented ADR. |
| CAP-AMG-06 | RETAIN — SLA trail is specified. No Matt ticket desk was added. |
| CAP-AMG-07 | RETAIN — service-improve is specified. Reviews are not solicited. |
| CAP-BZG-01 | AUGMENT — ESB snapshot feeds Uma close. ESB stays the transactional source. No ESB write. |
| CAP-BZG-02 | RETAIN — venue P&L skeleton stays empty. No invented margin. |
| CAP-BZG-03 | ELIMINATE — the closer role counts the till, not Matt. RETAIN — a variance with no policy stops, and verify stays on a separate role. Payment stays off. |
| CAP-BZG-04 | RETAIN — variance/waste skeleton is empty. ESB is not mutated. |
| CAP-BZG-05 | RETAIN — allocation skeleton is empty. No invented shares. |
| CAP-BZG-06 | RETAIN — BOM skeleton is empty. No invented recipe cost. |
| CAP-BZG-07 | RETAIN — observe-only. Wolf does not solicit reviews. |
| CAP-HR-01 | AUGMENT — org_persons is the people record used by My Work. A legal-entity HR master beyond that is not a separate proven machine. Not keyed on a person name. |
| CAP-HR-02 | RETAIN — hiring skeleton stays empty. No Matt recruiter step was added. |
| CAP-HR-03 | RETAIN — training skeleton stays empty. |
| CAP-HR-04 | RETAIN — payroll-input skeleton stays empty. No payroll execute. |
| CAP-HR-05 | RETAIN — succession skeleton stays empty. The point of the cap is to avoid accidental Matt dependency; it is not operating. |
| CAP-FIN-01 | ELIMINATE — Atrium ledger sign-in is by role id (P2, separate app, scratch database). RETAIN — a controller must enter real figures. Matt was not added as that controller. Backup is not proven. |
| CAP-FIN-02 | AUGMENT — statement ingest exists. Bank truth stays at the bank. No payment. |
| CAP-FIN-03 | AUGMENT — entity finance surfaces exist. P2 empty Atrium ledger is staff-startable on :8790 and is not Wolf group books. |
| CAP-FIN-04 | AUGMENT — invoice paths exist. Issuing a real invoice is a role act, not a Matt act added tonight. |
| CAP-FIN-05 | RETAIN — management pack is specified. No invented statements. |
| CAP-FIN-06 | RETAIN — intercompany billing skeleton stays empty. No money movement. |
| CAP-FIN-07 | RETAIN — budget/forecast/cash skeleton stays empty. No invented forecast. |
| CAP-FIN-08 | RETAIN — leakage skeleton stays empty. No invented waste numbers. |
| CAP-PROC-01 | RETAIN — supplier register is specified only. |
| CAP-PROC-02 | RETAIN — purchase flow is specified only. No pay action. |
| CAP-PROC-03 | RETAIN — payment tracking is specified. PAID still needs settlement evidence that is not in Wolf. No money movement. |
| CAP-CRM-01 | AUGMENT — lead boards exist. Follow-up is not a proven Matt-free SLA. |
| CAP-CRM-02 | RETAIN — identity graph stays specified. Operator depth does not raise it. |
| CAP-CRM-03 | RETAIN — package intelligence stays specified. No invented margin. |
| CAP-CRM-04 | AUGMENT — connector honesty exists. No send was added. |
| CAP-MSC-01 | RETAIN — asset register stays specified. |
| CAP-MSC-02 | RETAIN — Cloudflare and Access flips stay Matt-owned. Posture notes do not move that. |
| CAP-MSC-03 | RETAIN — compliance pack stays specified. No invented licence status. |
| CAP-MSC-04 | RETAIN — cybersecurity baseline stays specified. |
| CAP-MSC-05 | RETAIN — records/legal hold stays specified. No silent delete. |
| CAP-STRAT-01 | AUGMENT — 12-week surfaces exist. Cadence is not a proven operating loop without Matt. |
| CAP-STRAT-02 | AUGMENT — radar and the owner pulse exist. P3/P4 pulse is empty because Wolf Core has no live work. Not a new Matt board. |
| CAP-INTEL-01 | AUGMENT — one orchestration surface exists and its test is green. It does not replace an owner decision, and the pass does not raise the cap. |
| CAP-INTEL-02 | AUTOMATE — live authorised retrieval passed (font, voice, conflict, empty, absent). Matt is not in the lookup. |
| CAP-INTEL-03 | AUTOMATE — the same live prove marks conflict, empty, and absent without inventing a source. |
| CAP-INTEL-04 | AUGMENT — decision recall tests passed. Writing a decision is still a human act. Not a Matt-only memory. |
| CAP-INTEL-05 | RETAIN — approve-to-rule stays specified. No rule was auto-approved. |
| CAP-INTG-01 | RETAIN — no Wolf Yanolja connector. Vendor existence is not maturity. |
| CAP-INTG-02 | AUTOMATE — ESB is read into the close snapshot. No ESB write. No Matt export step. |
| CAP-INTG-03 | AUGMENT — Workspace connectors are used. This reaudit did not broaden scopes. |
| CAP-INTG-04 | AUGMENT — statement file import exists. No bank API and no payment. |
| CAP-INTG-05 | AUTOMATE — Metricool read and isolation passed. Writes stay fail-closed. |
| CAP-INTG-06 | RETAIN — technology registry stays specified. |
| CAP-INTG-07 | RETAIN — owner rejected PROVEN on 2026-09-18. Secrets and prod separation stay an owner control. Repo checks are not that prove. |
| CAP-DR-01 | RETAIN — owner rejected PROVEN on 2026-09-18. P2 found no B2 key and did not restore. Nothing is called backed up. |
| CAP-DR-02 | RETAIN — crown-jewel playbook stays Matt-only by spec. Not built out tonight. |
| CAP-SALE-01 | RETAIN — sale evidence pack is specified. Diligence cells are not capabilities and were not scored up. |
| CAP-SALE-02 | RETAIN — buyer data room is specified. No export. |
| CAP-SALE-03 | RETAIN — buyer mode is specified. No controlled export was turned on. |
| CAP-SALE-04 | RETAIN — attack/transition pack is specified. No buyer session. |

RESULT: PASS
