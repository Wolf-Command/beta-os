# GROK REVIEW — CAP-INTEL-05 Learning policy v2 — 2026-09-23

- Run: `BF-intel-learning-policy-v2-20260923`
- Plan: `docs/deliveries/GROK-PLAN-INTEL-LEARNING-POLICY-V2-2026-09-23.md`
- Decision served: 2026-09-20 PICK CAP-INTEL-05 approve-to-rule learning loop skeleton (deepened beyond skeleton; no new CAP invent)
- Bound: Beta `:8788` only. Production `:8787` sacred.
- Claim: `bf-intel-learning-policy-v2-20260923` · proven=false · ready=false · staff_ready=false
- Reviewed: 2026-09-23 ~01:15 WITA
- Verdict: **PASS** (append-only stub list/filter + Intel operator next-action read surface + DM/connective-visible recommendations; CAP/CR honesty held)

## What landed

- `scripts/core/intel_approve_to_rule.py` — `list_stubs` / `get_stub` (filterable, append-only stubs)
- `scripts/core/intel_learning_policy.py` — thin v2 read model: operator next-action, stub recommendations (read-only), desk compose; refuse promote/apply/execute/proven/PUT
- `scripts/serve_beta.py` — additive routes: `/api/intel/learning-policy`, `/stubs`, `/stubs/{id}`, `/recommendations`, `/next-action`; refuse promote/apply/PUT; anon 403
- `scripts/core/intel_ops_pack.py` — desk `learning_policy` strip (recommendations + next-action; no auto-apply)
- `scripts/core/intel_connective.py` — operator-depth desk surfaces `learning_policy_stubs` (read-only)
- `scripts/tests/test_intel_learning_policy_v2.py` — **PASS=126 FAIL=0** · `EXIT: SUCCESS`
- Approve-to-rule regression `test_intel_approve_to_rule.py` — **PASS=161 FAIL=0**

## Evidence table

| Check | Claimed | Verified |
|---|---|---|
| Tests | PASS=126 FAIL=0 | PASS=126 FAIL=0 |
| Approve-to-rule regression | PASS=161 FAIL=0 | PASS=161 FAIL=0 |
| Anon desk/stubs/recs/promote | 403 | live `:8788` → **403** ×4 under `development_assertion` |
| Owner desk/stubs/get/recs/next | 200 | live prove under temporary `development_assertion` |
| Owner PUT / promote / apply | 405 / 400 / 400 | `writes_refused` / `promote_refused` / `apply_refused` |
| CAP-INTEL-01 | BUILT | BUILT |
| CAP-INTEL-05 | SPECIFIED | SPECIFIED |
| Denominator | 77 | 77 |
| CR-be51980bd1194448 | OPEN | OPEN |
| proven / ready / staff_ready | false | false / false / false |
| Production `:8787` pid | untouched | **15975** before and after |
| Auth restore | cloudflare_access | launchd Beta restored; spoof subject → **403** `missing_auth` |
| Production learning-policy | absent | `:8787` → **404** |

## Red team

| Attack | Result |
| --- | --- |
| Invent PROVEN / READY | PASS — `score_refused`; CAP-INTEL-05 stays SPECIFIED; ledger not written |
| Auto-promote | PASS — `promote_refused`; stub `promoted` stays 0 |
| Auto-apply stub recommendation | PASS — `apply_refused`; `applied=false` / `read_only=true` |
| Anon / staff open | PASS — live anon GET/POST 403; Owner/role gate |
| PUT shortcut | PASS — 405 `writes_refused` |
| Resolve CR without product exit | PASS — CR stays OPEN; no resolution_evidence |
| Raise maturity via read surface | PASS — honesty ceiling BUILT; CAP stays SPECIFIED; staff_ready=false |
| Relaunch blocked learning-policy-v1 | PASS — `learning_policy_v1_relaunched=false` |
| Production `:8787` mutate | PASS — pid **15975** untouched; route 404 on Production |
| Score / credits / Model C write | PASS — ledger bytes unchanged; 77 rows |

## Live prove (temporary `development_assertion`)

1. `launchctl bootout` Beta only; start `BETA_AUTH_MODE=development_assertion` with `WOLF_INTEL_RULE_DB=catalog/backups/intel-learn-v2-prove.sqlite`
2. Anon desk/stubs/recs/promote → **403**
3. Owner note → approve → stub → list/get/recs/next/desk → **200**; next=`REVIEW_STUBS`; rec `read_only=true`
4. Owner PUT/promote/apply refused
5. Kill temp server; `launchctl bootstrap` + `kickstart` Beta (no `BETA_AUTH_MODE` ⇒ `cloudflare_access`)
6. Spoof `X-Wolf-Subject` → **403** `missing_auth`; Production pid **15975** unchanged

## Honesty

- CAP-INTEL-05 stays **SPECIFIED** (in-code ceiling BUILT ok)
- Do **not** false-resolve `CR-be51980bd1194448` — stays **OPEN**
- proven=false ready=false staff_ready=false
- Stub ≠ live rule. Recommendation ≠ applied. No auto-promote. No auto-apply.
- Distinct from BLOCKED `intel-learning-policy-v1` (inspect_retry_ceiling) — not relaunched

## Peaches verify

```bash
cd /Users/wolfterminal/beta-os && WOLF_TEST_MODE=1 python3 scripts/tests/test_intel_learning_policy_v2.py | tail -3
# PASS=126 FAIL=0 / EXIT: SUCCESS
```

## Completion Register

- CAP-INTEL-01 BUILT (unchanged)
- CAP-INTEL-05 SPECIFIED (unchanged — no invent PROVEN/READY)
- CR-be51980bd1194448 stays **OPEN** (engineering read surface proved; not CAP maturity invent)
- No AU promotion; no money/ESB/payment/CF/Access mutate; no auto-promote/apply/execute
- Production `:8787` sacred

## Next

- Close learning-policy-v2 ENGINEERING_PASS
- Do not invent staff-ready / PROVEN / READY
- Lane after plan: GGV Content x NAS Haikal prep v2 ENGINEERING_PASS (morning Haikal human = Needs Staff)

**EXIT: SUCCESS** · PASS=126 FAIL=0
