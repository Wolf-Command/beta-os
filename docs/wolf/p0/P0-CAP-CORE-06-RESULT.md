# P0 CAP-CORE-06 — Work Items / Promises / Decisions — 27 Sep 2026

Pack S2. Beta/local only. This extends the existing Wolf Core work-item primitive under the owner brief of 27 Sep 2026 16:32 WITA. It does not start a new system. Production `:8787` stayed pid 15975 (`serve.py`). Beta `:8788` stayed pid 64196 (`scripts/serve_beta.py`). No restart. No money, bank, payment, ESB, or NAS write. No live work item created. No JWT minted. No Access include changed. No push. Grok was not called.

TECHNICAL PROOF is the temporary trail in `scripts/tests/test_cap_core_06_trail.py`. DEPLOYED ROUTE PROOF is the unsigned, spoofed, and bad-JWT deny on pid 64196, and the public Access login redirect. A seated read was not observed, so `DEPLOYED-ROUTE-PROOF-20260927` stays FAIL for that reason. STAFF READINESS stays no. HUMAN COMMISSIONING stays no. OPERATING ADOPTION stays not measured. SYSTEM stays 19.65 / 77 = 25.52%.

## BEFORE

SYSTEM PROVEN (0.80). The work-item primitive and its tests existed. Live `core_work_items` count was 0. There was no stored live row to replay. D1 had kept the ledger at PROVEN. `test_core_work_items.py` was already `pass=49 fail=5`.

## AFTER

The row stays OPEN.

One item was created on a copy of the catalog, then the copy was deleted. The actor was `PERS-MATT` plus assignment `ASG-MATT-OWNER-1` on `ENT-GGV`. A display name was not the allow reason. The stored audit trail on that copy was:

| step | stored status |
| --- | --- |
| `work.create` | OPEN |
| `work.start` | IN_PROGRESS |
| `work.block` | BLOCKED |
| `work.start` | IN_PROGRESS |
| `work.complete` | COMPLETED |
| `work.verify` | VERIFIED |

Verify from IN_PROGRESS was denied (`illegal_transition`) and left the row IN_PROGRESS, with `verified_at` empty. COMPLETED was stored with `completed_at` set and `verified_at` empty. VERIFIED was stored only after the verify step.

Live `core_work_items` stayed 0. Live audit rows whose source is `work_items` stayed 44. The copy was removed. No live work item was inserted.

On pid 64196, these four callers are denied on `GET /api/core/work-items` and `GET /api/core/work-items/WI-NONE`. None of them returns a work item:

| caller | status | error |
| --- | --- | --- |
| no header | 403 | `missing_auth` |
| `Cf-Access-Authenticated-User-Email: spoofed@example.invalid` | 403 | `missing_auth` |
| `X-Wolf-Subject: PERS-MATT` | 403 | `missing_auth` |
| `Cf-Access-Jwt-Assertion: a.b.c` | 403 | `invalid_token` |

Unsigned `POST /api/core/work-items` with a title was 403. The live count stayed 0 after that POST.

On `https://beta.wolfcommand.net`, those two GET paths return 302 to `https://wolfcommand.cloudflareaccess.com/cdn-cgi/access/login/beta.wolfcommand.net`, `server: cloudflare`, `www-authenticate` starting `Cloudflare-Access`. The login query string was not recorded.

No seated session was opened. The ledger was not edited.

## EVIDENCE

Commit `2229b21`. Test: `scripts/tests/test_cap_core_06_trail.py`.

```
WOLF_TEST_MODE=1 python3 scripts/tests/test_cap_core_06_trail.py
NOTE  beta_pid=64196 prod_pid=15975
NOTE  live_work_items=0 live_audit_events=2878 live_work_item_audits=44
NOTE  trail=OPEN>IN_PROGRESS>BLOCKED>IN_PROGRESS>COMPLETED>VERIFIED
NOTE  live_work_items_after=0 live_audit_events_after=2887 live_work_item_audits_after=44
SUMMARY pass=48 fail=0
EXIT: SUCCESS
```

The nine new `core_audit_events` rows are `auth.resolve` / `DENIED` / source `cf_access` from those deny checks. They are not work items. An earlier run of the same checks, before the audit assertion was corrected, moved the same table from 2869 to 2878 the same way. Those rows were not deleted. No work-item row was inserted.

`test_core_work_items.py` this session: `SUMMARY pass=49 fail=5`. The five fails are the pre-existing checks D1 already recorded: temp migrate exit 2, temp migrate idempotent exit 2, non-Matt `work.*` grants, HTTP assign 400, live migrate exit 2. They were not repaired. A green repository suite would not close this item.

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

Listeners after the suites, unchanged:

```
Python  15975  127.0.0.1:8787  serve.py
Python  64196  127.0.0.1:8788  scripts/serve_beta.py
```

`state/model-c-baseline-assessments.json` was not edited. SHA256 `852f267a4bc71fe86f8972d077ec1c83f93a2de64735a2b2c8713488ddea3305`. `CAP-CORE-06` is still `PROVEN`. Row count 77. Score was not raised. `staff_ready` and `human_commissioned` stay false. Completion rows `CR-3cd31e220f788bc6` and `CR-4b78e43ab35126a8` stay OPEN.

## FINAL STATE

OPEN.

The closure test has two halves. The temporary trail has the stored states, and the live work-item count stayed 0. That half exits 0. The Beta read under a real session was not observed. The live table is empty, so the missing read is an empty list, not a row this pack created. CLOSED is not met. READY_FOR_HUMAN is not met: the seated read is still missing, and there is no separate acceptance for a person to perform. There is no named external provider. The missing session is the CAP-CORE-02 walk, not a new owner decision, so this row is not BLOCKED_OWNER.

## HUMAN NEXT

No new one-minute walk. The sign-in already in `docs/wolf/p0/HUMAN-TESTS.md` is the session this row needs. After that session exists, record the status and count of `GET /api/core/work-items`. The stored live list is empty. Do not create a work item to fill it. Do not send `X-Wolf-Subject`. Do not mark anyone commissioned from this file. Do not treat this temporary trail as staff ready.

RESULT: PASS
