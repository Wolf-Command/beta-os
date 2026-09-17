# GROK PLAN — Progress Dashboard v2 Owner Cockpit — 2026-09-17

**Factory:** `BF-progress-dashboard-v2-20260917`  
**Input:** Matt human review — ROUTE PASS · OWNER UX FAIL — ITERATE (screenshot).  
**Constraint:** Do NOT redesign from scratch. Keep visual direction, honesty, provenance, Owner-only.

## Scoring challenge (MUST)

### Factory Health 7% — SEMANTICALLY WRONG as mission maturity
Factory already demonstrates Matt→Peaches→Grok→Cursor→tests→red-team→fix→deployed-route verify.
That is **system health**, not **mission completion**.

**Decision:** REMOVE `Factory health` from mission weighted %.  
Factory becomes separate status: **HEALTHY / DEGRADED / FAILING** from deterministic checks
(ACTIVE factory clean, prove_deployed_ui_routes PASS, Beta :8788 up, Production untouched).

Re-normalize remaining domain weights to sum 1.0 (keep relative ratios; label ESTIMATED).

### Core 33% — denominator clarity
Core % = maturity of **tracked approved Core capabilities in Master_Build+overlay** (item_count denominator),
NOT “all imaginable Wolf Core forever”. Owner copy must say this.

### Overall %
Recompute WITHOUT Factory weight. Keep PARTIAL ESTIMATE. Document prior 27% → new value + why.
Do not inflate to look good.

## Empire first viewport (Owner Cockpit)

Hierarchy:
1. HOW FAR ARE WE? — big % + plain-English phase line derived from domains (not hard-coded forever)
2. Status chips: BUILT · HUMAN TESTING · LIVE · WAITING · POLICY NEEDED (tooltips; move MANDATORY DISTINCTIONS out of hero)
3. OWNER PULSE — Working now / Waiting on people / Policy·data needed / Build system (Factory HEALTHY, Production UNTOUCHED)
4. NEXT 3 MOVES — each ACTIVE|WAITING|RECOMMENDED|APPROVED (never confuse recommend vs approve)
5. RECENT WINS — evidence-backed human language (not commits)
6. MILESTONE ROAD — Foundations → … → Buyer Ready (evidence unlock; unlock Foundations + First Real Workflow + Second Business Vertical based on Core verticals + Habitat + Uma built)
7. Domain cards — name · visual bar · plain phase · biggest gap (weights only in How calculated)

Hide raw IDs (PERS-/EVR-/ROLE-/GPO-) behind DETAILS. Progressive disclosure in domain views.

Habitat owner stages: PLAN→WORK→PROOF→APPROVAL→PUBLISH READY→PUBLISH→LEARN  
Uma owner stages: ESB DATA→CASH COUNT→CHECK→EXCEPTION→FIX→VERIFIED CLOSE

Mobile: first screen = progress + phase + working/waiting + next move.

## Files
- `dashboards/progress.html` — primary UX rewrite (Empire)
- `scripts/core/progress_read_model.py` — factory health split, pulse/wins/moves/milestones, owner phase copy
- `state/progress/v1_overlay.json` — owner_pulse / recent_wins / next_moves / milestones evidence (provenance)
- `docs/canon/PROGRESS-DASHBOARD.md` — update denominator + factory health
- tests: extend `test_progress_dashboard.py`; keep deployed-route prove
- Restart Beta via `scripts/beta_restart.py` after serve/static change; run `prove_deployed_ui_routes.py`

## Forbidden
Production · Habitat workflow mutate · Metricool/ESB writes · weaken Owner-only · fake precision · mark HUMAN COMMISSIONED

## Done when
Deployed `/progress` 200 · tests green · Grok review PASS · Peaches verify · report schema to Matt · STOP
