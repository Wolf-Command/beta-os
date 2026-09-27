# P0 CAP-CORE-04 — Permission & Authority Engine — 27 Sep 2026

Pack S2. Beta/local only. This gates the existing Wolf Core permission catalog. It does not start a new system. Production `:8787` stayed pid 15975 (`serve.py`). Beta `:8788` was restarted from pid 74540 to pid 76910 (`scripts/serve_beta.py`) so the gate loaded. No money, bank, payment, ESB, or NAS write. No grant added. No person created. No JWT minted. No Access include changed. No push. Grok was not called.

TECHNICAL PROOF is `scripts/tests/test_cap_core_04_live_gate.py`. DEPLOYED ROUTE PROOF is the unsigned, spoofed, and bad-JWT deny on pid 76910, and the public Access login redirect. A seated allow was not observed, so `DEPLOYED-ROUTE-PROOF-20260927` stays FAIL for that reason. STAFF READINESS stays no. HUMAN COMMISSIONING stays no. OPERATING ADOPTION stays not measured. SYSTEM stays 19.65 / 77 = 25.52%.

The row was taken because the open items ahead of it cannot be advanced by this queue. CAP-MSC-02 still needs a review note that is not this queue. CAP-CORE-01 and CAP-CORE-06 still need a real Cloudflare session. CAP-CORE-03 stays OPEN because its seated assignment read was not observed. CAP-CORE-05 is already CLOSED. CAP-CORE-07 stays OPEN because its seated read was not observed. CAP-CORE-08 is BLOCKED_OWNER. CAP-CORE-09 stays OPEN because the live evidence count is 4, not 3. The queue lists CAP-CORE-03 as a prerequisite. The critical path records no extra prerequisite. This slice does not use the seated assignment read.

## BEFORE

SYSTEM PROVEN (0.80). `ROLE-GGV-CREATIVE-DIRECTOR` did not hold `organisation.entity.read`. `ROLE-GGV-EDIT` did. `ASG-HAIKAL-VE-1` was already ENDED, so that grant did not allow `PERS-HAIKAL`. People are not roles.

On Beta `:8788` pid 74540, `GET /api/core/permissions` did not check identity. Unsigned, a spoofed email, `X-Wolf-Subject`, and `Cf-Access-Jwt-Assertion: a.b.c` each returned 200. The body contained the permission list and the role grants.

`/api/core/me/permissions` was already 403 `missing_auth` for the first three callers and 403 `invalid_token` for the bad JWT.

On the same process, these seat routes were already denied:

| path | unsigned, spoofed email, `X-Wolf-Subject` | bad JWT |
| --- | --- | --- |
| `/content-2.0` | 403 `forbidden` | 403 `forbidden` |
| `/bzg/uma-blu` | 403 `missing_auth` | 403 `invalid_token` |
| `/wolf` | 403 `missing_auth` | 403 `invalid_token` |
| `/ggv/finance` | 403 `missing_auth` | 403 `invalid_token` |

On `https://beta.wolfcommand.net`, `/api/core/permissions` already returned 302 to the Access login.

## AFTER

The queue row stays OPEN. The ledger stays PROVEN.

`_get_core_permissions` now uses `_require_org_role_read`. The actor is `person_id` plus `organisation.role.read` on the same content target the assignment board already used. A display name is not the allow reason. No grant was inserted. `/api/core/me/permissions` was already identity-gated and was not given a second permission.

On pid 76910, these four callers are denied on `GET /api/core/permissions`. None of them returns a permission list or a role grant:

| caller | status | error |
| --- | --- | --- |
| no header | 403 | `missing_auth` |
| `Cf-Access-Authenticated-User-Email: spoofed@example.invalid` | 403 | `missing_auth` |
| `X-Wolf-Subject: PERS-MATT` | 403 | `missing_auth` |
| `Cf-Access-Jwt-Assertion: a.b.c` | 403 | `invalid_token` |

The four seat routes stay denied as in the table above. The public hostname returns 302 to `https://wolfcommand.cloudflareaccess.com/cdn-cgi/access/login/beta.wolfcommand.net` for the catalog path, `/api/core/me/permissions`, and the four seat routes. `server: cloudflare`. `www-authenticate` starts `Cloudflare-Access`. The login query string was not recorded.

Catalog projection, not a session. `content.plan.read` and `progress.read` use the content target. `venue.close.read` uses `ENT-BZG` / `BZG-UMA`. `finance.nota.read` uses `ENT-GGV`.

| person | content.plan.read | venue.close.read | finance.nota.read | progress.read |
| --- | --- | --- | --- | --- |
| `PERS-HAIKAL` | yes | no | no | no |
| `PERS-DEVI` | no | yes | no | no |
| `PERS-MATT` | yes | yes | yes | yes |

`/wolf` also requires `person_id` `PERS-MATT`. That HTTP allow was not observed. `PERS-AMANDA` holds `organisation.role.read` and `finance.nota.read`. She is not one of the three seats in this closure. Live `org_permissions` stayed 79. Live `org_role_permissions` stayed 139. No seated 200 was observed.

## EVIDENCE

Commit `c49237f`. Test: `scripts/tests/test_cap_core_04_live_gate.py`.

```
python3 scripts/tests/test_cap_core_04_live_gate.py
NOTE  beta_pid=76910 prod_pid=15975
SUMMARY pass=116 fail=0
EXIT: SUCCESS
```

`test_rbac_permissions.py` this session: exit 1, pass=39 fail=4. The catalog smoke check passed (`permissions catalog ok`). The four fails are `GGV assignment denied BZG Uma brand`, `permission without scope denied`, `person path ignores leftover email grant when role revoked`, and `entities Haikal authorised (entity.read)`. Those checks were already red against the stored grants. They were not repaired. Live `org_role_permissions` stayed 139.

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
| `test_cap_core_03_live_gate.py` | SUMMARY pass=172 fail=0 |
| `test_cap_core_05_empty_deny.py` | SUMMARY pass=39 fail=0 |
| `test_cap_core_06_trail.py` | SUMMARY pass=48 fail=0 |
| `test_cap_core_07_route.py` | SUMMARY pass=56 fail=0 |
| `test_cap_core_08_self_close.py` | SUMMARY pass=73 fail=0 |
| `test_cap_core_09_gate_list.py` | SUMMARY pass=69 fail=0 |

Listeners after the suites, unchanged from the restart:

```
Python  15975  127.0.0.1:8787  serve.py
Python  76910  127.0.0.1:8788  scripts/serve_beta.py
```

`state/model-c-baseline-assessments.json` was not edited. SHA256 `852f267a4bc71fe86f8972d077ec1c83f93a2de64735a2b2c8713488ddea3305`. `CAP-CORE-04` is still `PROVEN`. Row count 77. Score was not raised. `staff_ready` and `human_commissioned` stay false. No `CAP-CORE-04` completion row was inserted.

## FINAL STATE

OPEN.

The closure test has two halves. Unsigned callers are 403, including the permission catalog. The seated allow and deny for `PERS-HAIKAL`, `PERS-DEVI`, and `PERS-MATT` were not observed. CLOSED is not met. READY_FOR_HUMAN is not met: the seated statuses are still missing, and the CAP-CORE-02 walk is not commissioning of this row. There is no named external provider. A missing session is not an owner business decision this pack can record as BLOCKED_OWNER. The ledger was not raised. Staff ready, human commissioned, and operating adoption stay unset.

## HUMAN NEXT

No new one-minute walk. The three sign-ins are already in `docs/wolf/p0/HUMAN-TESTS.md` for CAP-CORE-02. After those sessions exist, record the status of `/content-2.0`, `/bzg/uma-blu`, `/wolf`, and `/ggv/finance` for each person. Do not mark anyone commissioned from this file.

RESULT: PASS
