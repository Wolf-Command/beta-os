# F1 — Test isolation — 28 Sep 2026

Pack F1 of the five-pack sprint. Extends Wolf Core. This is not a new system. Beta/local only. Production `:8787` stayed pid 15975 (`serve.py`). Beta `:8788` stayed pid 17892 (`scripts/serve_beta.py`). Neither was restarted. No money, bank, payment, ESB, or NAS write. No row deleted. No no-delete trigger dropped. No push. Grok was not called.

TECHNICAL PROOF is `scripts/tests/test_canonical_guard.py` run through `scripts/tests/run_guarded.py`. DEPLOYED ROUTE PROOF was not added: there is no new HTTP route. STAFF READINESS stays no. HUMAN COMMISSIONING stays no. OPERATING ADOPTION stays not measured. SYSTEM stays 19.65 / 77 = 25.52%.

## Guard

`scripts/core/canonical_guard.py` is installed when `WOLF_TEST_MODE=1` or the process argv is under `scripts/tests` (`scripts/core/__init__.py`). `scripts/tests/run_guarded.py` sets that mode, clears `WOLF_ALLOW_LIVE_AUDIT` and `WOLF_CANONICAL_WRITE_OVERRIDE`, installs the hook, then runs the suite.

A test process is refused any path whose text contains `wolf-system` or `/Production/`, and any file named `money.sqlite`. That refusal happens before `sqlite3` opens the file. A test process is refused a write to a canonical Beta file (parent directory exactly `catalog/`, suffix `.sqlite`). `WOLF_ALLOW_LIVE_AUDIT` does not open that path. `WOLF_CANONICAL_WRITE_OVERRIDE=1` is ignored for a test. A non-test process may write canonical Beta, because `scripts/serve_beta.py` is the operational writer. The same override on a non-test process is logged as `allow-override` at `state/build-factory/logs/canonical-write-override.log` (kind, pid, filename; no credential values). A non-test write to a prod path is refused.

The hook patches `sqlite3.connect` and sets an authorizer that denies insert, update, delete, and schema changes on a canonical connection. `CREATE TABLE` is an insert into `sqlite_master`, so a test that issues DDL against the live catalog is refused. Copies live under `state/build-factory/tmp-f1/` (gitignored) so `identity.db_connect` still sees a path inside `beta-os`. `bind_loaded_catalogs` retargets `CATALOG_DB` only. `LIVE_CATALOG_DB` stays the real file.

This continuation re-ran the proof:

```
PASS=20 FAIL=0
EXIT: SUCCESS
```

That run refused an insert into `core_evidence_records`, left the evidence count unchanged, left `EVD-50e827bd-2a51-4ed2-8e3b-4e88a1fff153` `INVALIDATED` / `P4-TEST cleanup`, and left these triggers in place: `trg_core_evidence_records_no_delete`, `trg_core_governance_exceptions_no_delete`, `trg_core_approval_decisions_no_delete`. A temp copy accepted `CREATE TABLE`. The canonical evidence count did not change.

## Ledger classification

Read-time only, in `scripts/core/ledger_class.py`. No `UPDATE`. No `DELETE`.

| ledger | before | after | valid operational | INVALID/TEST |
| --- | ---: | ---: | ---: | ---: |
| `core_evidence_records` | 4 | 4 | 0 | 4 |
| `core_governance_exceptions` | 3 | 3 | 0 | 3 |
| `core_approval_decisions` | 9 | 9 | 0 | 9 |

After the guarded suites and after the proof re-run above, a read-only count was still 4, 3, and 9. `EVD-50e827bd-2a51-4ed2-8e3b-4e88a1fff153` is still `INVALIDATED`, reason `P4-TEST cleanup`.

INVALID/TEST evidence ids: `EVD-LEAD-DEMO-VERIFIED`, `EVD-f537c61a-6541-4fa7-8ea5-c972eab2ef95`, `EVD-ebe6df48-4676-4e69-ad70-fd7e54882d2f`, `EVD-50e827bd-2a51-4ed2-8e3b-4e88a1fff153`.

INVALID/TEST exception ids, all stored `REJECTED`: `GEX-a8165674-68a6-4033-ab5b-d310d7ded0cd`, `GEX-0973743f-c838-4545-92c5-25fea51f21c8`, `GEX-41967006-311f-4ab0-9802-1e6db54ce18e`. The third is the 27 Sep P4 row. It stays.

INVALID/TEST approval decision ids, all `decided_by` `PERS-P4-*`: `APD-822ce9a5-bae6-4176-b173-dad019ebfbd8`, `APD-c5227355-5834-4050-9c68-ea2508c4133a`, `APD-3e9bcf02-c491-4865-a667-d1430ac179c6`, `APD-43ec9406-c06b-4bba-b2dd-916376153d10`, `APD-9247fa66-2f9d-46d0-be9d-821a227a8195`, `APD-ddda7311-5d04-4870-83c1-a7a5abf1d5a0`, `APD-94bacc16-d184-4f8f-86d5-b46cb246791f`, `APD-0208eeb0-2d4a-453a-8946-32cfcd44ed46`, `APD-1b7a9d12-8ff3-4159-b054-dd79318e8a02`.

Owner Command exception cards use the valid operational count as `value` and carry `invalid_test`. `stored_count` stays the physical non-demo total (3). The answer text states how many are valid operational and how many are INVALID/TEST. The owner “what changed” feed skips `PERS-P4-*` actors. War room JSON and `dashboards/finish-war-room.html` show the split. The business dashboard section note shows it. Staff home evidence rows skip `INVALIDATED`, `source_type` `TEST`, `PERS-P4-*`, and fixture/DEMO references. One `delegation.created` audit row for `PERS-MATT` at `2026-09-27T10:06:44Z` is not classified INVALID/TEST: its actor is not `PERS-P4-*`.

Also still present, not dropped: `trg_core_audit_events_no_delete`, `trg_core_lead_events_no_delete`, `trg_bzg_receipt_events_no_delete`, `trg_bzg_receipt_lines_no_delete`.

## Offenders

The hole was `WOLF_ALLOW_LIVE_AUDIT=1` returning early from `assert_catalog_writable`. Those early returns now call `assert_write_allowed`. Same for the decision-memory and intel-rule live bypasses.

Rehomed onto a catalog copy:

| script | what it did to the live catalog |
| --- | --- |
| `scripts/tests/test_work_loop.py` | set the live-audit bypass and wrote evidence, exceptions, and approval decisions. This is the writer of `EVD-50e827bd`. |
| `scripts/tests/test_role_dashboard.py` | deleted `WI-W3P3-` / `ASG-W3P3-` / `PERS-W3P3-` rows on the live catalog |
| `scripts/tests/test_real_auth_binding.py` | in-process Beta handler called `ensure_schema` on the live catalog |
| `scripts/tests/test_uma_blu_daily_close.py` | `mig.DB = LIVE_DB` then `mig.main()` |
| `scripts/tests/test_sale_operator_depth.py` | `WOLF_ALLOW_LIVE_AUDIT=1` then `ensure_operator_depth_rbac(commit=True)` |
| `scripts/tests/test_crm_operator_depth.py` | same |
| `scripts/tests/test_amg_operator_depth.py` | same |
| `scripts/tests/test_ggv_content_ops_depth.py` | same |
| `scripts/tests/test_ggv_operator_depth.py` | same |
| `scripts/tests/test_intel_operator_depth.py` | same |
| `scripts/tests/test_core_operator_depth.py` | same |

`scripts/core/completion_register.py` `ensure_schema` returns when `wolf_completion_items` already exists, so a read path does not issue `CREATE` against the live catalog.

`scripts/tests/test_canonical_guard.py` still sets both bypass env vars. That is the refusal proof. It is the only remaining assignment of `WOLF_ALLOW_LIVE_AUDIT=1`.

Still pointing a migrate or patch at the live catalog. Not rehomed. Not re-run. If they import core first, the authorizer refuses the write and the suite fails closed. A connection opened before the hook is not covered:

- `scripts/tests/test_exception_override.py` (`mig.DB = LIVE_DB`)
- `scripts/tests/test_sod_constraints.py` (`mig.DB = LIVE_DB`)
- `scripts/tests/test_devi_fb_ops_lead.py` (`mig.DB = LIVE_DB`)
- `scripts/tests/test_bzg_operator_depth.py` (`patch(LIVE_DB)`)
- `scripts/tests/test_bzg_loop_closure.py` (`patch(LIVE_DB)`)
- `scripts/tests/test_bzg_ops_pack.py` (`patch(LIVE_DB)`)

The seven operator-depth files and `test_uma_blu_daily_close.py` were edited and were not re-run.

## Guarded re-runs

Previously green suites, via `run_guarded.py`. Canonical counts stayed 4 / 3 / 9 after the batch.

| suite | result |
| --- | --- |
| `test_canonical_guard.py` | PASS=20 FAIL=0. Re-run this continuation: same. |
| `test_work_loop.py` | PASS=52 FAIL=0 |
| `test_real_auth_binding.py` | first run SUMMARY pass=33 fail=1 (`not authorized` on live `ensure_schema`). After isolating the in-process server: SUMMARY pass=51 fail=0 |
| `test_dashboard_truth.py` | first run failed in `completion_register.ensure_schema`. After the skip-if-exists repair: PASS=62 FAIL=0 |
| `test_msc_posture_prove.py` | PASS=151 FAIL=0 |
| `test_owner_command.py` | PASS=66 FAIL=0 |
| `test_business_dashboard.py` | PASS=131 FAIL=0 |
| `test_completion_war_room.py` | PASS=227 FAIL=0 |
| `test_lead_spine.py` | PASS=33 FAIL=0 |
| `test_haikal_content_ux_wave1.py` | PASS=21 FAIL=0 |
| `test_cap_msc_02_live_gate.py` | pass=38 fail=0 |
| `test_cap_core_01_live_gate.py` | pass=123 fail=0 |
| `test_cap_core_06_trail.py` | pass=48 fail=0 |
| `test_cap_core_05_empty_deny.py` | pass=39 fail=0 |
| `test_cap_core_07_route.py` | pass=56 fail=0 |
| `test_cap_core_08_self_close.py` | pass=73 fail=0 |
| `test_cap_core_09_gate_list.py` | pass=69 fail=0 |
| `test_cap_core_10_read.py` | pass=49 fail=0 |
| `test_role_dashboard.py` | PASS=142 FAIL=2. EXIT: FAILED |

The two role-dashboard failures are `owner succession fingerprint` and `http owner succession`. The only fingerprint key that differs is `audience`: `OWNER` for `PERS-MATT`, `CLIENT` for the replacement seat. `ROLE-MATT` is not in `ROLE_AUDIENCE`, so `audience_for` falls through to `PERSON_AUDIENCE`. That is a person map, not a ledger write. One repair pass was used on the auth, dashboard-truth, and role isolation failures. The audience mismatch was not changed. CAP-CORE-09 recorded this suite at PASS=144. 142 + 2 = 144, so these two checks are the regression against that record.

## Listeners

Checked after the proof re-run: pid 15975 is still `serve.py 8787`. pid 17892 is still `scripts/serve_beta.py` on `:8788`.

RESULT: FAIL
