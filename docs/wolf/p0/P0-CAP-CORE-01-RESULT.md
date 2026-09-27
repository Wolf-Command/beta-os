# P0 CAP-CORE-01 — Organisation Registry — 27 Sep 2026

Pack S2. Beta/local only. Production `:8787` stayed pid 15975 (`serve.py`). Beta `:8788` was restarted from pid 59914 to pid 64196 (`scripts/serve_beta.py`) so the gate loaded. No money, bank, payment, ESB, or NAS write. No person created. No assignment written. No grant added. No JWT minted. No Access include changed. No push. Grok was not called.

TECHNICAL PROOF is the gate in `scripts/serve_beta.py` plus the catalog projection in the suite. DEPLOYED ROUTE PROOF is the unsigned, spoofed, and bad-JWT deny on pid 64196, and the public Access login redirect. A seated allow was not observed, so `DEPLOYED-ROUTE-PROOF-20260927` stays FAIL for that reason. STAFF READINESS stays no. HUMAN COMMISSIONING stays no. OPERATING ADOPTION stays not measured. SYSTEM stays 19.65 / 77 = 25.52%.

## BEFORE

SYSTEM PROVEN (0.80). `GET /api/core/entities` on Beta `:8788` pid 59914 was already 403 `missing_auth` with no header, with a spoofed email, and with `X-Wolf-Subject`. A bad JWT was 403 `invalid_token`.

These reads did not check identity. An unsigned caller received the registry:

| path | unsigned status |
| --- | --- |
| `/api/core/entities/ENT-BZG` | 200 |
| `/api/core/entities/ENT-BZG/brands` | 200 |
| `/api/core/entities/ENT-BZG/locations` | 200 |
| `/api/core/entities/ENT-BZG/departments` | 200 |
| `/api/core/brands/BZG-UMA` | 200 |
| `/api/core/entities/ENT-NOPE` | 404 `not_found` |
| `/api/core/brands/NOPE` | 404 `not_found` |

The same eight outcomes held for a spoofed email header, `X-Wolf-Subject: PERS-MATT`, and `Cf-Access-Jwt-Assertion: a.b.c`. The 404 answers named the missing id with no identity check. There is no separate organisation UI page in `scripts/serve_beta.py`.

## AFTER

The row stays OPEN.

`_require_org_entity_read` is the list gate, now used by the entity, brand, location, and department reads. The actor is `person_id` plus `organisation.entity.read` on the same content target the list already used. A display name is not the allow reason. A missing id is checked only after that gate.

On pid 64196, these four callers are denied on all eight paths. None of them returns a registry body or a person:

| caller | status | error |
| --- | --- | --- |
| no header | 403 | `missing_auth` |
| `Cf-Access-Authenticated-User-Email: spoofed@example.invalid` | 403 | `missing_auth` |
| `X-Wolf-Subject: PERS-MATT` | 403 | `missing_auth` |
| `Cf-Access-Jwt-Assertion: a.b.c` | 403 | `invalid_token` |

The eight paths are `/api/core/entities`, `/api/core/entities/ENT-NOPE`, `/api/core/entities/ENT-BZG`, `/api/core/entities/ENT-BZG/brands`, `/api/core/entities/ENT-BZG/locations`, `/api/core/entities/ENT-BZG/departments`, `/api/core/brands/BZG-UMA`, and `/api/core/brands/NOPE`.

On `https://beta.wolfcommand.net`, those eight paths return 302 to `https://wolfcommand.cloudflareaccess.com/cdn-cgi/access/login/beta.wolfcommand.net`, `server: cloudflare`, `www-authenticate` starting `Cloudflare-Access`. The login query string was not recorded.

Content `GET /api/brands` still responds. That route is not this registry.

Catalog projection, read-only, not an HTTP session: `PERS-HAIKAL` and `PERS-DEVI` lack `organisation.entity.read`. `PERS-MATT` holds it. Org table counts were unchanged. No seated session was opened. The ledger was not edited.

## EVIDENCE

Commit `99f5a27`. Test: `scripts/tests/test_cap_core_01_live_gate.py`.

```
WOLF_TEST_MODE=1 python3 scripts/tests/test_cap_core_01_live_gate.py
NOTE  beta_pid=64196 prod_pid=15975
SUMMARY pass=123 fail=0
EXIT: SUCCESS
```

`test_org_registry.py` this session: `SUMMARY pass=35 fail=3`. The live unsigned checks passed. The three fails are the pre-existing census checks: brands seed = 7 got 12, Habitat is seeded as an org brand, GGV owns 5 client brands. D1 already recorded that census. It was not repaired. A green repository suite would not close this item.

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

Listeners after the suites, production unchanged, Beta the restarted process:

```
Python  15975  127.0.0.1:8787  serve.py
Python  64196  127.0.0.1:8788  scripts/serve_beta.py
```

`state/model-c-baseline-assessments.json` was not edited. SHA256 `852f267a4bc71fe86f8972d077ec1c83f93a2de64735a2b2c8713488ddea3305`. `CAP-CORE-01` is still `PROVEN`. Row count 77. Score was not raised. `staff_ready` and `human_commissioned` stay false. Completion row `CR-dddbefbb61c98008` stays OPEN.

## FINAL STATE

OPEN.

The closure test has two halves. Unsigned stays fail-closed, and that half exits 0. The Beta status under a real session, including a denial for a person who lacks organisation read, was not observed. CLOSED is not met. READY_FOR_HUMAN is not met: the seated read is still missing, and there is no separate org acceptance for a person to perform. There is no named external provider. The missing session is the CAP-CORE-02 walk, not a new owner decision, so this row is not BLOCKED_OWNER.

## HUMAN NEXT

No new one-minute walk. The sign-in already in `docs/wolf/p0/HUMAN-TESTS.md` is the session this row needs. After that session exists, record the status of `/api/core/entities` and one entity read for that person. Do not send `X-Wolf-Subject`. Do not mark anyone commissioned from this file. Do not treat this unsigned deny as staff ready.

RESULT: PASS
