# P0 CAP-CORE-05 — Authority Limits Evaluator — 27 Sep 2026

Pack S2. Beta/local only. This uses the existing Wolf Core authority evaluator. It does not start a new system. Production `:8787` stayed pid 15975 (`serve.py`). Beta `:8788` stayed pid 64196 (`scripts/serve_beta.py`). No restart. No money, bank, payment, ESB, or NAS write. No authority-limit row inserted. No amount stored. No JWT minted. No Access include changed. No push. Grok was not called.

TECHNICAL PROOF is the empty-copy deny in `scripts/tests/test_cap_core_05_empty_deny.py`. DEPLOYED ROUTE PROOF is the unsigned, spoofed, and bad-JWT deny on pid 64196, and the public Access login redirect. A seated check was not observed, so `DEPLOYED-ROUTE-PROOF-20260927` stays FAIL for that reason. STAFF READINESS stays no. HUMAN COMMISSIONING stays no. OPERATING ADOPTION stays not measured. SYSTEM stays 19.65 / 77 = 25.52%.

The row was taken because the open items ahead of it cannot be advanced by this queue. CAP-MSC-02 still needs a review note that is not this queue. CAP-CORE-01 and CAP-CORE-06 still need a real Cloudflare session. CAP-CORE-03 and CAP-CORE-04 close on that same session, and their queue prerequisites are not final. The critical path records no extra prerequisite for this row. Its closure test is the empty-table deny. It does not use the seat matrix.

## BEFORE

SYSTEM PROVEN (0.80). `scripts/core/authority.py` already denies when no matching limit row exists (`higher_approval_required`, `no_matching_authority_limit`). Live `org_authority_limits` count was 0. That count is configuration. It is not a tolerance. No limit row was waiting to be inserted. The ledger READY bar is a broader runtime prove on Beta. That bar was not this closure test.

## AFTER

The queue row is CLOSED. The ledger stays PROVEN.

On a copy of the catalog, `org_authority_limits` was 0. No row was inserted. `within_authority` for `PERS-MATT` on `content.plan.approve`, and for `PERS-HAIKAL` on `content.plan.edit`, both returned `allowed` false, reason `higher_approval_required`, detail `no_matching_authority_limit`, `matched_limit` null. The person id on the Matt decision was `PERS-MATT`. An email string was not an allow. The copy still had 0 rows and was deleted.

Live `org_authority_limits` stayed 0. No amount was written.

On pid 64196, these four callers are denied on `GET /api/core/authority/check` and `GET /api/core/me/authority-limits`. None of them returns a limit or a decision:

| caller | status | error |
| --- | --- | --- |
| no header | 403 | `missing_auth` |
| `Cf-Access-Authenticated-User-Email: spoofed@example.invalid` | 403 | `missing_auth` |
| `X-Wolf-Subject: PERS-MATT` | 403 | `missing_auth` |
| `Cf-Access-Jwt-Assertion: a.b.c` | 403 | `invalid_token` |

On `https://beta.wolfcommand.net`, those two GET paths return 302 to `https://wolfcommand.cloudflareaccess.com/cdn-cgi/access/login/beta.wolfcommand.net`, `server: cloudflare`, `www-authenticate` starting `Cloudflare-Access`. The login query string was not recorded.

No seated session was opened. The ledger was not edited. There is no `wolf_completion_items` row for CAP-CORE-05. None was inserted.

## EVIDENCE

Commit `fcae665`. Test: `scripts/tests/test_cap_core_05_empty_deny.py`.

```
WOLF_TEST_MODE=1 python3 scripts/tests/test_cap_core_05_empty_deny.py
NOTE  beta_pid=64196 prod_pid=15975
NOTE  live_authority_limits=0
NOTE  empty_deny=higher_approval_required no_matching_authority_limit
NOTE  live_authority_limits_after=0
SUMMARY pass=39 fail=0
EXIT: SUCCESS
```

`test_authority_limits.py` this session: `SUMMARY pass=48 fail=1`. The fail is `scope required denied`. D1 already recorded it: ending scopes only on `ASG-MATT-OWNER-1` still leaves `ASG-INTEL-OPERATOR-MATT` covering the content department, so the allow is the evaluator. It was not repaired. `seeded_live=0`. A development-subject 200 inside that suite is not this proof.

Previously green suites, this session, exit 0:

| suite | result |
| --- | --- |
| `test_real_auth_binding.py` | PASS=51 FAIL=0 |
| `test_msc_posture_prove.py` | PASS=151 FAIL=0 |
| `test_dashboard_truth.py` | PASS=62 FAIL=0 |
| `test_owner_command.py` | PASS=66 FAIL=0 |
| `test_business_dashboard.py` | PASS=131 FAIL=0 |
| `test_role_dashboard.py` | PASS=144 FAIL=0 |
| `test_completion_war_room.py` | PASS=227 FAIL=0 |
| `test_lead_spine.py` | PASS=33 FAIL=0 |
| `test_haikal_content_ux_wave1.py` | PASS=21 FAIL=0 |
| `test_cap_msc_02_live_gate.py` | SUMMARY pass=38 fail=0 |
| `test_cap_core_01_live_gate.py` | SUMMARY pass=123 fail=0 |
| `test_cap_core_06_trail.py` | SUMMARY pass=48 fail=0 |

Listeners after the suites, unchanged:

```
Python  15975  127.0.0.1:8787  serve.py
Python  64196  127.0.0.1:8788  scripts/serve_beta.py
```

`state/model-c-baseline-assessments.json` was not edited. SHA256 `852f267a4bc71fe86f8972d077ec1c83f93a2de64735a2b2c8713488ddea3305`. `CAP-CORE-05` is still `PROVEN`. Row count 77. Score was not raised. `staff_ready` and `human_commissioned` stay false. Live `org_authority_limits` after the suites was still 0.

## FINAL STATE

CLOSED.

The closure test is met: an action with no authority-limit row is denied, and the live count is still 0. No amount was written. The empty table is configuration. It is not a tolerance, and it was not filled in. READY_FOR_HUMAN is not met: there is no staff walk. There is no named external provider. There is no owner decision left on this row. The ledger stays PROVEN. The broader Beta runtime prove that would raise it to READY was not observed and is not claimed.

## HUMAN NEXT

None. Do not insert a limit to make the table look finished. Do not read the live count 0 as a chosen tolerance. Do not mark anyone commissioned from this file.

RESULT: PASS
