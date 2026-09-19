# CURSOR MISSION — GGV Speed-to-Lead ops — 2026-09-19

**Class:** FIX / BUILT deepen. Not a new system.  
**Capability:** CAP-GGV-04 Lead Triage & Speed-to-Lead stays **BUILT**. Not promoted to PROVEN.  
**Extends:** Lead Spine operator path, commit `12ca489` (`dashboards/lead-spine.html`, `/api/leads*`).  
**Lane:** Beta `:8788` only. Production `:8787` not touched.  
**Result:** TRIAGE BOARD READY

Habitat operators who can already read Lead Spine see the open leads that still need a person, with one next action taken from facts already on the row. Speed is the source clock already stored on the lead. A missing clock stays unavailable. No SLA number is invented. No lead row is invented.

## What landed

- `scripts/core/lead_spine.py` — `api_triage_board`. Queue is open, unmapped, or still unanswered / unassigned. Parked and closed stay off it. Next action is Record touch, Assign owner, Link work item, or Update Wolf lifecycle, in that order. Work-item hook links an existing Core work item and does not create one. Claim hook sets CLAIMED only and does not verify; it is not the step on an open lead.
- `scripts/serve_beta.py` — `GET /api/leads/triage?brand=habitat` uses the existing `resolve_request_identity` path (`_lead_identity`). Unauth is 403. Touch uses the server clock when the body omits `touched_at`. That clock is the click time, not an SLA target.
- `dashboards/lead-spine.html` — Needs triage slice above the full list. Demo banner and closed-is-not-a-sale copy stay.
- `scripts/tests/test_ggv_speed_to_lead_ops.py` — temp sqlite under `catalog/backups/`. No live catalog write.
- `scripts/tests/test_lead_spine_operator.py` — the touch call now passes `touched_at`, matching the spine contract that already required it.

## Refused

Production / wolf-system / `:8787`. Klaviyo and Metricool writes. Invented leads or prices. Invented SLA numbers. CAP-GGV-04 PROVEN promotion. Model C score and ledger writes. Alchemist writes. WIP four edits (`migrate_phase2_6_team_readiness.py`, `phase26_team.py`, `skills/__init__.py`, `wolf_intelligence.py`).

## Prove

- `python3 scripts/tests/test_ggv_speed_to_lead_ops.py` → `PASS=71 FAIL=0`
- `python3 scripts/tests/test_lead_spine_operator.py` → `PASS=30 FAIL=0`
- Beta restarted with `launchctl kickstart -k` of `net.wolfcommand.serve-beta` only. `:8787` still listening. `:8788` still listening.
- `GET /lead-spine` → 200. Body contains `Needs triage`, `No SLA number is invented.`, `Demo data`, and `not a sale`.
- `GET /api/leads/triage?brand=habitat` with no cookie → 403 `missing_auth`.
- `GET /api/leads?brand=habitat` with no cookie → 403.
- `state/model-c-baseline-assessments.json` `CAP-GGV-04` first field remains `BUILT`. File bytes unchanged by the test.
- Signed-in phone tap-through was not run. Anonymous fail-closed and the served HTML are the live proof here.
