# P0 CAP-CORE-03 — Role / Position / Assignment — 27 Sep 2026

Pack S2. Beta/local only. This gates the existing Wolf Core assignment board. It does not start a new system. Production `:8787` stayed pid 15975 (`serve.py`). Beta `:8788` was restarted from pid 64196 to pid 74540 (`scripts/serve_beta.py`) so the gate loaded. No money, bank, payment, ESB, or NAS write. No person created. No assignment written. No grant added. No JWT minted. No Access include changed. No push. Grok was not called.

TECHNICAL PROOF is `scripts/tests/test_cap_core_03_live_gate.py`. DEPLOYED ROUTE PROOF is the unsigned, spoofed, and bad-JWT deny on pid 74540, and the public Access login redirect. A seated allow was not observed, so `DEPLOYED-ROUTE-PROOF-20260927` stays FAIL for that reason. STAFF READINESS stays no. HUMAN COMMISSIONING stays no. OPERATING ADOPTION stays not measured. SYSTEM stays 19.65 / 77 = 25.52%.

The row was taken because the open items ahead of it cannot be advanced by this queue. CAP-MSC-02 still needs a review note that is not this queue. CAP-CORE-01 and CAP-CORE-06 still need a real Cloudflare session. CAP-CORE-04 closes on that same session, and its queue prerequisite is not final. CAP-CORE-05 is already CLOSED. CAP-CORE-07 stays OPEN because its seated read was not observed. CAP-CORE-08 is BLOCKED_OWNER. CAP-CORE-09 stays OPEN because the live evidence count is 4, not 3. The queue lists CAP-CORE-01 as a prerequisite. The critical path records no extra prerequisite. This slice does not use the seated organisation read.

## BEFORE

SYSTEM PROVEN (0.80). `ASG-HAIKAL-CD-1` was already ACTIVE and primary. `ASG-HAIKAL-VE-1` was already ENDED at `2026-09-24T17:34:12+08:00`. People are not roles.

On Beta `:8788` pid 64196 these reads did not check identity:

| path | unsigned | spoofed email | `X-Wolf-Subject` | bad JWT |
| --- | --- | --- | --- | --- |
| `/api/core/roles` | 200 | 200 | 200 | 200 |
| `/api/core/roles/ROLE-NOPE` | 404 `not_found` | 404 | 404 | 404 |
| `/api/core/positions` | 200 | 200 | 200 | 200 |
| `/api/core/positions/POS-NOPE` | 404 `not_found` | 404 | 404 | 404 |
| `/api/core/persons/PERS-NOPE/assignments` | 404 `not_found` | 404 | 404 | 404 |

`/api/core/me/assignments` was already 403 `missing_auth` for the first three callers and 403 `invalid_token` for `Cf-Access-Jwt-Assertion: a.b.c`.

On `https://beta.wolfcommand.net`, `/api/core/roles`, `/api/core/persons/PERS-HAIKAL/assignments`, and `/api/core/me/assignments` already returned 302 to the Access login. The other board paths were not probed before the restart.

There is no separate assignment UI page in this slice.

## AFTER

The queue row stays OPEN. The ledger stays PROVEN.

`_require_org_role_read` is the board gate. The actor is `person_id` plus `organisation.role.read` on the same content target the entity list already used. A display name is not the allow reason. A missing id is checked only after that gate. No grant was inserted. `/api/core/me/assignments` was already identity-gated and was not given a second permission.

On pid 74540, these four callers are denied on all eleven paths. None of them returns a role, a position, an assignment, or a person:

| caller | status | error |
| --- | --- | --- |
| no header | 403 | `missing_auth` |
| `Cf-Access-Authenticated-User-Email: spoofed@example.invalid` | 403 | `missing_auth` |
| `X-Wolf-Subject: PERS-MATT` | 403 | `missing_auth` |
| `Cf-Access-Jwt-Assertion: a.b.c` | 403 | `invalid_token` |

The eleven paths are `/api/core/roles`, `/api/core/roles/ROLE-NOPE`, `/api/core/roles/ROLE-GGV-CREATIVE-DIRECTOR`, `/api/core/positions`, `/api/core/positions/POS-NOPE`, `/api/core/positions/POS-GGV-CREATIVE-DIRECTOR-1`, `/api/core/positions/POS-NOPE/assignments`, `/api/core/positions/POS-GGV-CREATIVE-DIRECTOR-1/assignments`, `/api/core/persons/PERS-NOPE/assignments`, `/api/core/persons/PERS-HAIKAL/assignments`, and `/api/core/me/assignments`.

On `https://beta.wolfcommand.net`, those eleven paths return 302 to `https://wolfcommand.cloudflareaccess.com/cdn-cgi/access/login/beta.wolfcommand.net`, `server: cloudflare`, `www-authenticate` starting `Cloudflare-Access`. The login query string was not recorded.

Catalog projection, read-only, not an HTTP session: `PERS-MATT` and `PERS-AMANDA` hold `organisation.role.read`. `PERS-HAIKAL`, `PERS-DEVI`, `PERS-MISA`, and `PERS-LEAD-DEMO` lack it. Stored `ASG-HAIKAL-CD-1` is ACTIVE, `end_at` empty, primary. Stored `ASG-HAIKAL-VE-1` is ENDED. The only active Haikal seat is `ASG-HAIKAL-CD-1`. Live `org_persons` stayed 6. Live `org_roles` stayed 12. Live `org_positions` stayed 12. Live `org_assignments` stayed 10. No seated session was opened. The ledger was not edited. `wolf_completion_items` has no `CAP-CORE-03` row. None was inserted.

## EVIDENCE

Commit `5a814fe`. Test: `scripts/tests/test_cap_core_03_live_gate.py`.

```
WOLF_TEST_MODE=1 python3 scripts/tests/test_cap_core_03_live_gate.py
NOTE  beta_pid=74540 prod_pid=15975
SUMMARY pass=172 fail=0
EXIT: SUCCESS
```

`test_role_position_assignment.py` this session: exit 1, pass=33 fail=5. The fails are the pre-existing census checks: positions seeded = 4 got 12, assignments seeded = 4 got 10, positions by entity GGV, org context scope NOT_BUILT, and org_scopes present. D1 already recorded that census. It was not repaired. After the suite, `ASG-HIST-TEST`, `ASG-MATT-SECOND`, and `ASG-DUP-PRIMARY` were absent. Live assignments stayed 10. Live persons stayed 6. A green repository suite would not close this item.

`scripts/tests/test_work_loop.py` was not re-run. The previous pack recorded that it writes the live catalog and left `EVD-50e827bd` invalidated. Another run would add another residue.

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
| `test_cap_core_08_self_close.py` | SUMMARY pass=73 fail=0 |
| `test_cap_core_09_gate_list.py` | SUMMARY pass=69 fail=0 |

Listeners after the suites, production unchanged, Beta the restarted process:

```
Python  15975  127.0.0.1:8787  serve.py
Python  74540  127.0.0.1:8788  scripts/serve_beta.py
```

`state/model-c-baseline-assessments.json` was not edited. SHA256 `852f267a4bc71fe86f8972d077ec1c83f93a2de64735a2b2c8713488ddea3305`. `CAP-CORE-03` is still `PROVEN`. Row count 77. Score was not raised. `staff_ready` and `human_commissioned` stay false.

## FINAL STATE

OPEN. The unsigned half of the closure test passed. The seated half is absent. No new person row. The ended seat is not stored as active. The ledger was not raised. Staff ready, human commissioned, and operating adoption stay unset.

## HUMAN NEXT

No new one-minute walk. The sign-in already in `docs/wolf/p0/HUMAN-TESTS.md` is the session this row needs. After that session exists, a person who holds `organisation.role.read` opens `GET /api/core/persons/PERS-HAIKAL/assignments` and writes down the status. The stored active seat is `ASG-HAIKAL-CD-1`. The stored ended seat is `ASG-HAIKAL-VE-1`. A person who lacks the grant should be refused. Do not send `X-Wolf-Subject`. Do not mark anyone commissioned from this file. Do not treat this unsigned deny as staff ready.

RESULT: PASS
