# P0 CAP-MSC-02 — Access & Cloudflare Posture — 27 Sep 2026

Pack S2. Beta/local only. Production `:8787` stayed pid 15975 (`serve.py`). Beta `:8788` stayed pid 59914 (`scripts/serve_beta.py`). No restart. No money, bank, payment, ESB, or NAS write. No Access include change. No JWT minted. No secret value printed. No push. Grok was not called.

TECHNICAL PROOF is `scripts/tests/test_cap_msc_02_live_gate.py`. DEPLOYED ROUTE PROOF is the unsigned and public statuses below. A seated allow was not observed, so `DEPLOYED-ROUTE-PROOF-20260927` stays FAIL for that reason. STAFF READINESS stays no. HUMAN COMMISSIONING stays no. OPERATING ADOPTION stays not measured. SYSTEM stays 19.65 / 77 = 25.52%.

## BEFORE

SYSTEM BUILT (0.25). The public hostname already redirected to Cloudflare Access login. Matt-owned include flips stayed with the owner. The posture module `scripts/core/msc_posture_prove.py` names empty slots. An empty framework is not a prove. The 2026-09-20 review binds that empty framework. It does not bind a live-gate deny prove. No CAP-bound test of the live gate was in the queue.

## AFTER

The deny prove is recorded. The row stays OPEN.

On the origin, these four callers are denied. None of them returns a person:

| caller | status | error |
| --- | --- | --- |
| no header | 403 | `missing_auth` |
| `Cf-Access-Authenticated-User-Email: spoofed@example.invalid` | 403 | `missing_auth` |
| `X-Wolf-Subject: PERS-MATT` | 403 | `missing_auth` |
| `Cf-Access-Jwt-Assertion: a.b.c` | 403 | `invalid_token` |

Those four were checked on `/api/core/me`, `/api/msc/posture`, and `/wolf`.

On `https://beta.wolfcommand.net`, the same three paths return 302 to `https://wolfcommand.cloudflareaccess.com/cdn-cgi/access/login/beta.wolfcommand.net`, `server: cloudflare`, `www-authenticate` starting `Cloudflare-Access`. The login query string was not recorded.

Access includes were not changed. No seated session was opened. The ledger was not edited.

## EVIDENCE

Commit `025dd13`. Test: `scripts/tests/test_cap_msc_02_live_gate.py`.

```
WOLF_TEST_MODE=1 python3 scripts/tests/test_cap_msc_02_live_gate.py
NOTE  beta_pid=59914 prod_pid=15975
SUMMARY pass=38 fail=0
EXIT: SUCCESS
```

Previously green suites, this session, exit 0:

| suite | result |
| --- | --- |
| `test_msc_posture_prove.py` | PASS=151 FAIL=0 |
| `test_real_auth_binding.py` | PASS=51 FAIL=0 |
| `test_dashboard_truth.py` | PASS=62 FAIL=0 |
| `test_owner_command.py` | PASS=66 FAIL=0 |
| `test_business_dashboard.py` | PASS=131 FAIL=0 |
| `test_role_dashboard.py` | PASS=144 FAIL=0 |
| `test_completion_war_room.py` | PASS=227 FAIL=0 |
| `test_lead_spine.py` | PASS=33 FAIL=0 |
| `test_haikal_content_ux_wave1.py` | PASS=21 FAIL=0 |

Listeners after the suite, unchanged:

```
Python  15975  127.0.0.1:8787  serve.py
Python  59914  127.0.0.1:8788  scripts/serve_beta.py
```

`state/model-c-baseline-assessments.json` was not edited. SHA256 `852f267a4bc71fe86f8972d077ec1c83f93a2de64735a2b2c8713488ddea3305`. `CAP-MSC-02` is still `BUILT`. Row count 77. Score was not raised. `staff_ready` and `human_commissioned` stay false. Completion row `CR-80296d7bc9c35452` stays OPEN. `catalog/msc_posture_prove.sqlite` is still absent.

The 2026-09-20 file `docs/deliveries/GROK-REVIEW-MSC-POSTURE-PROVE-V1-36ce088-2026-09-20.md` reviews the empty framework. It says an empty framework is not a prove. It does not bind this deny prove. This pack does not write a substitute review.

## FINAL STATE

OPEN.

The closure test has two halves. The deny test exits 0. The review note that is not this queue does not exist. CLOSED is not met. READY_FOR_HUMAN is not met: the deny prove has no staff walk, and the seated observation is the CAP-CORE-02 walk, which is not commissioning of this row. There is no named external provider. Naming a review is not an owner business decision this pack can record as BLOCKED_OWNER. The remaining Cursor cannot do is that review note.

## HUMAN NEXT

No new one-minute walk. The seated allow, if someone signs in, is the walk already in `docs/wolf/p0/HUMAN-TESTS.md` for CAP-CORE-02. Write those statuses there. Do not mark anyone commissioned from this file. Do not treat this deny prove as staff ready.

RESULT: PASS
