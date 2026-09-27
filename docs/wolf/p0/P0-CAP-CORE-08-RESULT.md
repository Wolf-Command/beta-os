# P0 CAP-CORE-08 — Segregation of Duties — 27 Sep 2026

Pack S2. Beta/local only. This uses the existing Wolf Core venue-close SoD check. It does not start a new system. Production `:8787` stayed pid 15975 (`serve.py`). Beta `:8788` stayed pid 64196 (`scripts/serve_beta.py`). No restart. No money, bank, payment, ESB, or NAS write. No SoD constraint inserted. No variance policy inserted. No cash amount stored. No closer seated. No JWT minted. No Access include changed. No push. Grok was not called.

TECHNICAL PROOF is the temporary-catalog deny in `scripts/tests/test_cap_core_08_self_close.py`. DEPLOYED ROUTE PROOF is the unsigned, spoofed, and bad-JWT deny on pid 64196, and the public Access login redirect for the close list. A seated check was not observed, so `DEPLOYED-ROUTE-PROOF-20260927` stays FAIL for that reason. STAFF READINESS stays no. HUMAN COMMISSIONING stays no. OPERATING ADOPTION stays not measured. SYSTEM stays 19.65 / 77 = 25.52%.

The row was taken because the open items ahead of it cannot be advanced by this queue. CAP-MSC-02 still needs a review note that is not this queue. CAP-CORE-01 and CAP-CORE-06 still need a real Cloudflare session. CAP-CORE-03 and CAP-CORE-04 close on that same session, and their queue prerequisites are not final. CAP-CORE-05 is already CLOSED. CAP-CORE-07 stays OPEN because its seated read was not observed. The queue lists CAP-CORE-04 and CAP-CORE-07 as prerequisites. The critical path records no extra prerequisite. This slice does not use the seat matrix or the approval seated read.

## BEFORE

SYSTEM PROVEN (0.80). `scripts/core/venue_close.py` already denies a submitter who verifies their own resolved close (`sod_self_close`). Live `core_sod_constraints` count was 0. Live `core_sod_participation` count was 0. Live `venue_daily_closes` count was 0. Live `venue_close_variance_policies` count was 0. `ROLE-BZG-CLOSER` had no active assignment. `ROLE-MATT` already held `venue.close.verify`. `ROLE-BZG-FB-OPS-LEAD` did not. Broader finance SoD live packs were the READY bar. No pack had been authored. A temporary constraint is not this row.

## AFTER

The queue row is BLOCKED_OWNER. The ledger stays PROVEN.

On a copy of the catalog, one resolved close was inserted with no declared cash, no variance amount, and no variance policy. `submitted_by_person_id` was `PERS-MATT`. `resolved_by_person_id` was `PERS-DEVI`. `verify_close` as `PERS-MATT` raised `sod_self_close` at HTTP 403. The close stayed `RESOLVED`. `verified_by_person_id` and `verified_at` stayed null.

`rbac.evaluate` allowed `PERS-MATT` on `venue.close.verify` for `ENT-BZG` / `BZG-UMA` through `ROLE-MATT` and `ASG-MATT-OWNER-1`. That allow did not override the SoD deny. A display name was not an allow. An email string was not an allow. Both were `forbidden`, and the close stayed `RESOLVED`. `PERS-DEVI` on the active seat `ROLE-BZG-FB-OPS-LEAD` does not hold `venue.close.verify`, so her verify was `forbidden`. `PERS-HAIKAL` was `forbidden`. No person row was inserted. The copy's SoD constraint count stayed 0. The copy's permission grants were unchanged. The closer seat stayed empty. The copy was deleted.

Live `core_sod_constraints` stayed 0. Live `core_sod_participation` stayed 0. Live `venue_daily_closes` stayed 0. Live `venue_close_variance_policies` stayed 0. Live `venue_close` audits stayed 0. The closer seat stayed empty. No amount was written.

On pid 64196, these four callers are denied on `GET /api/venue-close/list` and `POST /api/venue-close/verify`. None of them returns a close:

| caller | status | error |
| --- | --- | --- |
| no header | 403 | `missing_auth` |
| `Cf-Access-Authenticated-User-Email: spoofed@example.invalid` | 403 | `missing_auth` |
| `X-Wolf-Subject: PERS-MATT` | 403 | `missing_auth` |
| `Cf-Access-Jwt-Assertion: a.b.c` | 403 | `invalid_token` |

On `https://beta.wolfcommand.net`, `GET /api/venue-close/list` returns 302 to `https://wolfcommand.cloudflareaccess.com/cdn-cgi/access/login/beta.wolfcommand.net`, `server: cloudflare`, `www-authenticate` starting `Cloudflare-Access`. The login query string was not recorded.

No seated session was opened. The ledger was not edited.

## EVIDENCE

Commit `e2cab4f`. Test: `scripts/tests/test_cap_core_08_self_close.py`.

```
WOLF_TEST_MODE=1 python3 scripts/tests/test_cap_core_08_self_close.py
NOTE  beta_pid=64196 prod_pid=15975
NOTE  live_constraints=0 live_closes=0 live_policies=0 live_closer=0 live_venue_audits=0
NOTE  self_close=sod_self_close submitter=PERS-MATT resolver=PERS-DEVI copy_constraints=0 copy_closes=1 copy_audits=0
NOTE  live_constraints_after=0 live_closes_after=0 live_policies_after=0 live_venue_audits_after=0 live_closer_after=0
SUMMARY pass=73 fail=0
EXIT: SUCCESS
```

`test_sod_constraints.py` this session: exit 1, PASS=42 FAIL=2, then `ApprovalError: required permission denied: test.spend.approve`. The two fails are `live approvals before=0` and `live approval decisions=0` got 6. D1 already recorded that abort and those two fails. They were not repaired. A green repository suite would not author a finance pack.

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
| `test_cap_core_05_empty_deny.py` | SUMMARY pass=39 fail=0 |
| `test_cap_core_07_route.py` | SUMMARY pass=56 fail=0 |

Listeners after the suites, unchanged:

```
Python  15975  127.0.0.1:8787  serve.py
Python  64196  127.0.0.1:8788  scripts/serve_beta.py
```

`state/model-c-baseline-assessments.json` was not edited. SHA256 `852f267a4bc71fe86f8972d077ec1c83f93a2de64735a2b2c8713488ddea3305`. `CAP-CORE-08` is still `PROVEN`. Row count 77. Score was not raised. `staff_ready` and `human_commissioned` stay false. Completion row `CR-d92de8a365ef37ce` stays OPEN. Live `core_sod_constraints` after the suites was still 0.

## FINAL STATE

BLOCKED_OWNER.

The closure test is met: the submitter cannot verify their own resolved close, and no SoD pack row was written to the live catalog. No amount was written. The empty constraint table is the absence of a finance pack. It is not a finance rule, and it was not filled in. CLOSED is not met: the READY bar is a broader finance pack, and Matt has not authored one or recorded that none is authorised. READY_FOR_HUMAN is not met: there is no staff walk. There is no named external provider. The ledger stays PROVEN.

## HUMAN NEXT

Matt decides whether a broader finance SoD pack is required. If it is, he authors it. Cursor does not write that pack, does not invent a threshold, and does not seat `ROLE-BZG-CLOSER`. There is no one-minute staff walk for this row. Do not mark anyone commissioned from this file. Do not treat this deny as staff ready.

RESULT: PASS
