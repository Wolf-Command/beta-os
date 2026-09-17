# GROK PLAN — Matt Progress Dashboard v1

**Run:** BF-progress-dashboard-20260917  
**Date:** 2026-09-17  
**Audience:** PERS-MATT / Owner only (RBAC). Normal staff → 403.

## Dirty tree (precondition — DONE)

See `docs/deliveries/DIRTY-TREE-CLASSIFICATION-2026-09-17.md`.  
Uma Blu DIRTY = parallel docs + Phase2.6 WIP + sha256 backups — **not** a failed close commit. Preserve all. Do not clean for cosmetics.

## Architecture

```
EXISTING CSVs (docs/canon/build-dashboard/)
+ delivery artifacts / git log (read-only)
+ state/build-factory/runs/*.json
+ controlled overlay state/progress/v1_overlay.json (PROVENANCE required)
    → scripts/core/progress_read_model.py
    → GET /api/progress/* (Owner only)
    → dashboards/progress.html (+ /progress redirect)
```

**NO second PM truth.** Overlay only fills gaps where Master_Build.csv is stale vs proven commits (Authority, Approval, Dual, SoD, Evidence, Exception, Habitat gate, Uma Close, Auth JWT, Knowledge rule). Each overlay row: `source`, `as_of`, `confidence` (DERIVED|ESTIMATED|CURATED).

## Progress calculation (transparent v1)

Document in UI "How is this calculated?" and `docs/canon/PROGRESS-DASHBOARD.md`:

1. Domain weights (CURATED, labelled ESTIMATED until registry owns weights): Core 25%, GGV 20%, BZG 15%, AMG 15%, Intelligence 10%, Integrations 5%, Sale Readiness 5%, Factory health 5%.
2. Per-capability maturity score from lifecycle (not file count):
   - IDEA/SPECIFIED=0.05 · APPROVED=0.15 · BUILDING=0.35 · BETA/SCHEMA_BUILT/TESTED=0.55 · PILOT=0.7 · VERIFIED=0.85 · LIVE=1.0 · RETIRED=n/a
3. **Commissioning penalty:** if BUILT/TESTED but HUMAN_COMMISSIONING ≠ DONE → cap at 0.65 (BUILT ≠ LIVE).
4. Overall = weighted average. Show as integer % + label **PARTIAL ESTIMATE** while overlay+CSV mix exists.
5. Reconcile vs prior ~32%: if computed differs by >8 pts, show "why" note (new Core slices + two verticals landed after that estimate).

Never invent AI 47.3%. Never treat Peaches recommendation as APPROVED.

## Views (SPA-ish tabs, no full reload hell)

Menu: Empire · Wolf Core · GGV · AMG · BZG · Intelligence · Integrations · Sale Readiness · Build Factory · Backlog

Default: Empire.

Each view fed by read-model JSON. Mobile collapse nav. Wolf typography. Premium clean — no sci-fi cheese.

### Mandatory distinctions
- BUILT ≠ HUMAN_COMMISSIONED ≠ LIVE
- WAITING_HUMAN ≠ BLOCKED_SYSTEM ≠ UNAPPROVED_POLICY ≠ INACCESSIBLE_SOURCE
- TARGET profit ≠ ACTUAL (show NOT YET TRUSTWORTHY)
- ESTIMATED labelled

### Current verticals (hard-require accurate)
**Habitat:** PLAN→WORK→EVIDENCE→APPROVAL→PUBLISH_GATE→METRICOOL→PERFORMANCE with real states (Write LOCKED).  
**Uma Close:** ESB→SNAPSHOT→CASH→RECONCILE→EXCEPTION→RESOLUTION→VERIFIED with WAITING FOR CLOSER + variance NOT CONFIGURED (policy, not failure).

### Achievements
Locked until evidence: Foundations · First Real Workflow · First Human Commission · First External Action · …  
Do not award without proof.

## Security
- Resolve CF JWT → PERS-MATT only for progress API + page data.
- Staff seats 403. No secrets, no crown jewels, no employee PII dumps, no bank numbers.

## Files to add/change
- `scripts/core/progress_read_model.py`
- `state/progress/v1_overlay.json` (curated, documented)
- `scripts/migrations/migrate_progress_dashboard.py` if needed (minimal)
- `dashboards/progress.html`
- wire `serve_beta.py`: `/progress`, `/dashboards/progress.html`, `/api/progress/...`
- nav entry for Owner only
- `docs/canon/PROGRESS-DASHBOARD.md`
- `scripts/tests/test_progress_dashboard.py` — Matt brief mandatory cases
- Do **not** mutate Habitat commissioning data, Uma closes, ESB, Metricool, Production
- Do **not** touch Phase2.6 dirty WIP files

## Honesty
```
progress_type: PARTIAL_ESTIMATE
master_build_csv_staleness: KNOWN
overlay_required: YES
```
