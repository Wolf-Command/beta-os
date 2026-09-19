# CURSOR MISSION — CAP-GGV-05 Social DERIVE views — 2026-09-19

**Class:** FIX / deepen BUILT. Not a new system.  
**Capability:** CAP-GGV-05 Brand Social Performance stays **BUILT**. Not promoted to PROVEN.  
**Lane:** Beta `:8788` only. Production `:8787` not touched.  
**Change request:** `CR-e20099e21930b9a6` stays **OPEN**. Next action stays `Governed DERIVE views + PROVEN red-team`. The PROVEN red-team is not claimed done.

Owner and authorised staff can read a governed view of Metricool numbers already stored for a brand that has an ACTIVE Metricool mapping. Habitat is that case. A missing number stays missing. Surfaces are not blended. Wolf does not call Metricool, write Metricool, or spend on ads.

## What landed

- `scripts/core/ggv_social_derive.py` — `derive_view`. Reads `performance_records` where `external_system='metricool'` and `data_lane='operational'`, and only rows whose `external_profile_id` matches an ACTIVE `brand_external_ids` mapping. NULL is excluded from medians. Reel is omitted when there are no reel rows. Clicks, conversions, followers, and paid ads spend are named as not in the store.
- `scripts/serve_beta.py` — `GET /api/ggv/social` and `GET /ggv-social` use `resolve_request_identity`. Unauth is 403. Staff without `ggv.social.read` is 403. Owner (`PERS-MATT`) can read. `POST` Metricool, ads, and invented metrics are 405. `PUT` and `PATCH` are read-only 405.
- `scripts/migrations/migrate_ggv_social_permissions.py` — adds `ggv.social.read`. Role grants stay 0.
- `dashboards/ggv-social.html` — Habitat view. Honesty copy stays on the page.
- `scripts/tests/test_ggv_social_derive.py` — temp sqlite plus one read-only pass over the live store. No live performance write.

## Refused

Production / wolf-system / `:8787`. Metricool write and Metricool network calls. Paid ads spend. Invented metrics, blended scores, and zero-filled gaps. CAP-GGV-05 PROVEN promotion. Resolving `CR-e20099e21930b9a6`. Model C score and ledger writes. Alchemist writes. WIP four edits (`migrate_phase2_6_team_readiness.py`, `phase26_team.py`, `skills/__init__.py`, `wolf_intelligence.py`). Staff role grants.

## Prove

- `python3 scripts/tests/test_ggv_social_derive.py` → `PASS=104 FAIL=0`
- Beta restarted with `launchctl kickstart -k` of `net.wolfcommand.serve-beta` only. `:8787` pid stayed `20807`. `:8788` pid moved `53359` → `56273`.
- `GET /api/ggv/social` with no cookie → 403 `missing_auth`.
- `GET /ggv-social` with no cookie → 403.
- `state/model-c-baseline-assessments.json` `CAP-GGV-05` first field remains `BUILT`. File bytes unchanged by the test. Ledger stays 77 rows.
- `CR-e20099e21930b9a6` state remains `OPEN`.
- Signed-in phone tap-through was not run. Owner `200` is proved only under `BETA_AUTH_MODE=development_assertion` in the test, not with a live Cloudflare JWT.
