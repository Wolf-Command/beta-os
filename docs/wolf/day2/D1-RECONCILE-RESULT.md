SYSTEM = 19.65 / 77 = 25.52%

# D1 — Reconcile the 77-capability ledger — 27 Sep 2026

Beta/local only. No application code. Production `:8787` stayed pid 15975. Beta `:8788` stayed pid 4443. No repair pass was applied to code. Human commissioned: no.

## BEFORE

Canonical ledger `state/model-c-baseline-assessments.json` (the overnight reaudit read it and did not rewrite it). Credits from `docs/MODEL-C-SYSTEM-NUMERIC-CREDITS.md`: ABSENT 0.00, SPECIFIED 0.05, BUILT 0.25, PROVEN 0.80, READY 1.00.

Counted from that ledger before this pack's note append, and again after it:

| state | caps | credit | subtotal |
| --- | ---: | ---: | ---: |
| ABSENT | 1 | 0.00 | 0.00 |
| SPECIFIED | 41 | 0.05 | 2.05 |
| BUILT | 20 | 0.25 | 5.00 |
| PROVEN | 12 | 0.80 | 9.60 |
| READY | 3 | 1.00 | 3.00 |
| **SUM** | **77** |  | **19.65** |

`19.65 / 77 × 100 = 25.519480…%`. Half-up to 2 decimals is **25.52%**.

The overnight reaudit in `docs/wolf/sprint7/P6-REAUDIT-RESULT.md` proposed dropping the 12 rows below and publishing **13.00 / 77 = 16.88%**. That proposal mixed staff walks, empty-database guards, and ended seats into the SYSTEM credit. It is not the reconciled score.

### What PROVEN and READY require

From `docs/MODEL-C-SYSTEM-SCORING-RULES.md` section 2:

> **PROVEN** — Implementation has deterministic verification appropriate to the capability, including required tests and material red-team/review evidence. **BUILT ≠ PROVEN.**

> **READY** — Capability is technically deployable/available in its intended Beta/runtime environment with required technical dependencies proven. Where a user-facing route is part of the capability: **REPOSITORY TEST ≠ DEPLOYED ROUTE TEST.** **READY ≠ HUMAN COMMISSIONED ≠ LIVE OPERATING ADOPTION.**

Section 3 minimum evidence: PROVEN is "Deterministic verification + required review/red-team evidence". READY is "Deployed/runtime/technical dependency proof appropriate to capability".

From `docs/MODEL-C-SYSTEM-NUMERIC-CREDITS.md`:

> PROVEN = 80% — Deterministic verification plus required review/red-team has retired most technical implementation risk.

> READY = 100% — Technical deployment/runtime/dependency proof is complete for the capability's intended boundary. READY is independent of human operating adoption.

Section 7 of the scoring rules: "Venue Daily Close may become SYSTEM READY once. Uma Blu commissioning affects OPERATING ADOPTION."

A missing human walk does not lower a row. A red test lowers a row only when that test covers this capability's required proof. A red test in another suite does not.

## DONE

All 12 proposed downgrades are rejected. Maturity states stay as the canonical ledger had them. A reconciliation note was appended as the last field on each of those 12 rows. The other 65 rows were not changed.

Backup of the pre-note ledger: `state/model-c-baseline-assessments.backup-20260927.json` (16574 bytes, identical to the ledger before the notes).

Commissioning, staff readiness, and adoption gaps: `state/completion-register/COMMISSIONING-STATE-20260927.json`. They are not in the SYSTEM sum.

| id | name | previous | proposed | reconciled | what the red checks actually cover |
| --- | --- | --- | --- | --- | --- |
| CAP-CORE-01 | Organisation Registry | PROVEN 0.80 | BUILT 0.25 | PROVEN 0.80 | TECHNICAL PROOF of the 2026-09-16 slice census (brands 12 not 7, Habitat org row, GGV brands 5). The labeled 404 fail is the unsigned list returning 403. Direct invalid-entity GET is HTTP 404. Hierarchy and content `org_brand_id` NULL checks passed. |
| CAP-CORE-02 | Person & Auth Identity | READY 1.00 | BUILT 0.25 | READY 1.00 | Binding suite is green. person_auth reds are a person-count drift, a negative "no org_roles" guard, and the same mislabeled 403. STAFF READINESS / HUMAN COMMISSIONING is the missing Cloudflare sign-in. READY's definition excludes that. |
| CAP-CORE-03 | Role / Position / Assignment | PROVEN 0.80 | BUILT 0.25 | PROVEN 0.80 | Seat counts grew (positions 12, assignments 10, GGV positions 8). The "scope NOT_BUILT" and "no org_scopes" checks are negative guards for later slices. Duplicate-primary and history checks passed. |
| CAP-CORE-04 | Permission & Authority Engine | PROVEN 0.80 | BUILT 0.25 | PROVEN 0.80 | The four rbac fails follow active seats, including `SCOPE-WOLF-CONTENT-ALL-BRANDS` listing BZG-UMA and ended `ASG-HAIKAL-VE-1`. `test_phase2_5a_permissions.py` covers content email flags and stale pid 3758, not `rbac.evaluate`. |
| CAP-CORE-05 | Authority Limits Evaluator | PROVEN 0.80 | BUILT 0.25 | PROVEN 0.80 | The one red check ends scopes only on `ASG-MATT-OWNER-1`. `ASG-INTEL-OPERATOR-MATT` still covers `DEPT-GGV-CONTENT`, so allow is the evaluator working. PASS=48. |
| CAP-CORE-06 | Work Items / Promises / Decisions | PROVEN 0.80 | BUILT 0.25 | PROVEN 0.80 | Migrate exit 2 warns that later roles hold `work.*`. HTTP assign 400 is the ended video-editor seat. Lifecycle checks passed. P4 "not staff-usable" is STAFF READINESS. |
| CAP-CORE-07 | Approval Engine | PROVEN 0.80 | BUILT 0.25 | PROVEN 0.80 | Engine file pass=57 fail=3, all live decision count 6 not 0. Dual and policy suites abort after those same guards because the fixture grants `ROLE-GGV-EDIT` and the active seat is `ROLE-GGV-CREATIVE-DIRECTOR`. Dual rules that ran passed. |
| CAP-CORE-08 | Segregation of Duties | PROVEN 0.80 | BUILT 0.25 | PROVEN 0.80 | Conflict checks passed (PASS=42 before the abort). The abort is the same ended-role permission denial, not a failed SoD rule. |
| CAP-CORE-09 | Evidence Requirements | PROVEN 0.80 | BUILT 0.25 | PROVEN 0.80 | pass=65 fail=8 are live-count guards. Migrate REFUSE: evidence records must stay 0, got 3. |
| CAP-CORE-10 | Exception / Override Governance | PROVEN 0.80 | BUILT 0.25 | PROVEN 0.80 | pass=77 fail=11 are live-count guards. Migrate REFUSE: governance exceptions must stay 0, got 2. |
| CAP-GGV-02 | Publish Gate & Operator Loop | READY 1.00 | BUILT 0.25 | READY 1.00 | 46 behavior checks passed. Five fails are live exceptions = 2 and the migrate guard. `staff_ready=false` is STAFF READINESS. Deployed `/api/planner/publish-gate` is HTTP 400 `id required`. `/habitat-operator` is HTTP 403. |
| CAP-BZG-03 | Venue Daily Close | READY 1.00 | PROVEN 0.80 | READY 1.00 | Close suites are green. `/bzg/uma-blu` is HTTP 403 fail-closed. No closer, variance policies 0, and `settlement_api` UNAVAILABLE are HUMAN COMMISSIONING / OPERATING ADOPTION and the no-payment boundary. Section 7 says Uma commissioning is adoption. |

Other 65: left as the reaudit found. The only other PROVEN rows are CAP-INTEL-02, CAP-INTEL-03, and CAP-INTEL-04. Their cited suites were re-run today and exited 0 (below). The reaudit already refused to raise them for a missing staff walk, which matches READY's definition, so they stay PROVEN. CAP-INTEL-01 stays BUILT. No other row was PROVEN or READY.

## VERIFIED

Script (half-up, 2 decimals), run after the notes were appended:

```
python3 ledger sum
n 77
counts {'PROVEN': 12, 'READY': 3, 'SPECIFIED': 41, 'BUILT': 20, 'ABSENT': 1}
sum 19.65
SYSTEM = 19.65 / 77 = 25.52%
noted 12
```

`compute_system_from_ledger()` on the same file:

```
77 19.65 {'ABSENT': 1, 'SPECIFIED': 41, 'BUILT': 20, 'PROVEN': 12, 'READY': 3} OK True
```

Cited suites, `WOLF_TEST_MODE=1 PYTHONPATH=scripts`, this session:

```
test_org_registry.py                  EXIT 1  SUMMARY pass=33 fail=4
  FAIL brands seed = 7  12
  FAIL Habitat not seeded as org brand
  FAIL GGV owns zero client brands this slice  5
  FAIL API invalid entity 404
test_real_auth_binding.py             EXIT 0  SUMMARY pass=44 fail=0
test_person_auth_identity.py          EXIT 1  SUMMARY pass=28 fail=4
  FAIL 4 persons  6
  FAIL 4 auth identities  5
  FAIL no org_roles table this slice
  FAIL person 404
test_role_position_assignment.py      EXIT 1  SUMMARY pass=33 fail=5
  FAIL positions seeded = 4  12
  FAIL assignments seeded = 4  10
  FAIL positions by entity GGV
  FAIL org context scope NOT_BUILT
  FAIL no org_scopes/rbac tables
test_rbac_permissions.py              EXIT 1  SUMMARY pass=39 fail=4
  FAIL GGV assignment denied BZG Uma brand
  FAIL permission without scope denied
  FAIL person path ignores leftover email grant when role revoked
  FAIL entities Haikal authorised (entity.read)
test_phase2_5a_permissions.py         EXIT 1  TOTAL PASS=16 FAIL=10
  includes FAIL 03 :8787 PID 3758 untouched — PID missing
test_authority_limits.py              EXIT 1  SUMMARY pass=48 fail=1
  FAIL scope required denied
test_core_work_items.py               EXIT 1  SUMMARY pass=49 fail=5
  FAIL temp migrate exit 0 — 2
  FAIL temp migrate idempotent — 2
  FAIL no non-Matt work.* grants
  FAIL HTTP assign
  FAIL live migrate exit 0 — 2
test_approval_engine.py               EXIT 1  pass=57 fail=3
  FAIL live approval decisions=0 — 6
  FAIL live approval decisions still 0 — 6
  FAIL FINAL live approvals=0
test_dual_approval.py                 EXIT 1  PASS=40 FAIL=2 then ApprovalError
  FAIL live approvals before=0
  FAIL live approval decisions=0 — 6
  required permission denied: test.spend.approve
test_approval_policy_binding.py       EXIT 1  PASS=49 FAIL=2 then the same ApprovalError
test_sod_constraints.py               EXIT 1  PASS=42 FAIL=2 then the same ApprovalError
test_evidence_requirements.py         EXIT 1  pass=65 fail=8
  REFUSE: live evidence records must stay 0, got 3
test_exception_override.py            EXIT 1  pass=77 fail=11
  REFUSE: live governance exceptions must stay 0, got 2
test_habitat_publish_gate.py          EXIT 1  46 passed, 5 failed
  FAIL live exceptions before=0
  FAIL live migrate exit 0
  FAIL migration idempotent
  FAIL live exceptions after=0
  FAIL live exceptions still 0
test_uma_blu_daily_close.py           EXIT 0  70 passed, 0 failed
test_uma_daily_loop_finish.py         EXIT 0  PASS=44 FAIL=0
test_authorised_knowledge.py          EXIT 0  PASS=51 FAIL=0
test_authorised_knowledge_live.py     EXIT 0  PASS=36 FAIL=0
test_decision_memory.py               EXIT 0  PASS=85 FAIL=0
test_intel_orchestration.py           EXIT 0  PASS=65 FAIL=0
```

Deployed route checks on Beta `:8788` (read only):

```
HTTP 404 /api/core/entities/ENT-NOPE
HTTP 404 /api/core/persons/PERS-NOPE
HTTP 403 /api/core/entities   missing_auth (unsigned Haikal header)
HTTP 400 /api/planner/publish-gate   id required
HTTP 403 /habitat-operator
HTTP 403 /bzg/uma-blu
HTTP 403 /api/bzg/uma-blu/today
HTTP 200 /api/health
```

Catalog reads after the suites (read-only): `org_authority_limits` 0, `core_work_items` 0, `core_approval_requests` 0, `core_approval_decisions` 6, `core_evidence_records` 3, `core_governance_exceptions` 2, `venue_close_variance_policies` 0, `venue_daily_closes` 0, `ROLE-BZG-CLOSER` assignments none. `ASG-HAIKAL-VE-1` status ENDED at `2026-09-24T17:34:12+08:00`. Active Haikal seat `ASG-HAIKAL-CD-1` / `ROLE-GGV-CREATIVE-DIRECTOR`. `SCOPE-WOLF-CONTENT-ALL-BRANDS` includes `BZG-UMA`.

Listeners after the runs:

```
PROD:15975 127.0.0.1:8787
BETA:4443 127.0.0.1:8788
```

## WAITING HUMAN

Not commissioned. No Cloudflare staff session was opened. No closer was seated. No variance policy was written. No payment was turned on.

The gaps that wait on a person are in `state/completion-register/COMMISSIONING-STATE-20260927.json`.

## BLOCKERS

- The cited suites above still exit 1. Their red lines do not currently invalidate these twelve SYSTEM rows, for the mapping in the table. They were not repaired. This pack allows one repair pass and did not use it on application code.
- Unsigned Beta routes stay fail-closed (403) without `Cf-Access-Jwt-Assertion`.
- `PERS-LEAD-DEMO` ("Demo operator") is already in `org_persons`. It was not created here, not used to raise a score, and not deleted.
- Transitional org canon (`docs/canon/ORG-REGISTRY-TRANSITIONAL.md`) still says habitat/selo/tropik are not GGV legal ownership. Content `org_brand_id` for those keys is still NULL (those checks passed). Later content work also stores `habitat` on `org_brands` under `ENT-GGV`. That tension is recorded. It is not a new brand row from this pack.
- CAP-BZG-03 cannot finish a real cash mismatch while variance policies stay 0. That stop is the machine. Inventing a policy to get a green close is refused.

## NEXT HUMAN TEST

A person with a Cloudflare seat signs in on Beta `:8788` and opens `/my-work`, `/habitat-operator`, and `/bzg/uma-blu`. That walk is staff readiness and commissioning. It does not, by itself, move any of these SYSTEM rows, and it does not mark any row human commissioned.

Do not replace 25.52% with the reaudit figure 16.88%.

RESULT: PASS
