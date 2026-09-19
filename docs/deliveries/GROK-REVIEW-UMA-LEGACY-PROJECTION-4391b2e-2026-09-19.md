# Grok review — Uma legacy projection (working tree on 4391b2e)

Date: 19 September 2026 (WITA)
Commit base: 4391b2e (slice files uncommitted at review start; commit follows PASS)
Run: BF-26c2148684de / BF-uma-legacy-projection-20260919
Reviewer: Peaches (Grok actual-diff + Peaches verify)

## Verdict

PASS. Close the lane.

## Prove

- Tests: `python3 scripts/tests/test_uma_legacy_projection.py` — PASS=48 FAIL=0 (includes live Alchemist RO check; cutover_at stays null).
- Cursor log: EXIT: SUCCESS / CURSOR_DONE / shell exit 0 after inspect-recover relaunch (empty-log nohup deaths → shell_tool_background_tracked).
- Module prove (PYTHONPATH=scripts): live Alchemist `source_status=OK`; awaiting Devi 25; received 73; unpaid ledger 10 (sum 7276000); petty movements present with **no** `opening_float`; today `float_status=NOT_FOUND`, `fixture_notice=false`; cards include opening-balance blocker, unpaid existing ledger, received follow-up (legacy), and history.
- Deployed route: `python3 scripts/beta_restart.py` PASS (:8788 relaunched; :8787 untouched). `prove_deployed_ui_routes.py` PASS. `prove_deployed_routes.py` PASS.
- Live HTML GET 200: `/bzg/uma-blu`, `/bzg/uma-blu/bills`, `/bzg/uma-blu/petty` — Existing chip CSS present.
- Live API without JWT: 403 `missing_auth` fail-closed (not 404) on today/prs/petty/history.
- `state/uma/cutover.json`: `cutover_at` null, sources `[alchemist]`.
- WIP four preserved (not edited this slice; mtimes 2026-09-17): `migrate_phase2_6_team_readiness.py`, `phase26_team.py`, `skills/__init__.py`, `wolf_intelligence.py`.
- Production untouched.

## Red team

- Phone browser screenshots not taken this pass (Cursor noted payload/HTML tests only). Not a scope fail; Devi phone check remains a commissioning follow-up, not a factory blocker.
- Provenance `source_id` remains numeric inside machine payloads; staff UI shows `pr_num` (e.g. PR-1385) and tests assert no raw source_id render.
- Live JWT-authenticated API paint not exercised from this desk (fail-closed by design). Module + unit live-DB prove covers projection truth; HTML routes are deployed.
- Pre-existing dirty nav on issues/close (11:22 WITA, prior slice) left untouched — not part of this commit.

## Scope files

- `scripts/core/uma_alchemist_ro.py`
- `scripts/core/uma_ops_console.py`
- `scripts/serve_beta.py`
- `state/uma/cutover.json`
- `dashboards/bzg-uma-blu.html`
- `dashboards/bzg-uma-blu-bills.html`
- `dashboards/bzg-uma-blu-petty.html`
- `scripts/tests/test_uma_legacy_projection.py`
