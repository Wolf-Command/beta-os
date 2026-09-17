# Progress Dashboard — Canon (v1)

**Status:** BUILT + TESTED 2026-09-17 (Cursor Local Agent)  
**Run:** BF-progress-dashboard-20260917  
**Decision:** `2026-09-17 · PICK: Matt Progress Dashboard v1 on Beta only`  
**Audience:** Owner / `PERS-MATT` only. Staff seats → **403**.

## Honesty

```
progress_type: PARTIAL_ESTIMATE
master_build_csv_staleness: KNOWN
overlay_required: YES
BUILT ≠ HUMAN_COMMISSIONED ≠ LIVE
TARGET profit ≠ ACTUAL (ACTUAL NOT YET TRUSTWORTHY)
```

No invented AI percentages. Peaches recommendations are not APPROVED. Domain weights labelled **ESTIMATED** until a registry owns them.

## Architecture

```
docs/canon/build-dashboard/*.csv
+ state/build-factory/runs/*.json (read-only)
+ state/progress/v1_overlay.json (provenance required)
    → scripts/core/progress_read_model.py
    → GET /api/progress* (Owner only)
    → dashboards/progress.html (+ /progress)
```

Overlay fills gaps where `Master_Build.csv` is stale vs proven commits (Authority, Approval, Dual, SoD, Evidence, Exception, Habitat gate, Uma Close, Auth JWT, Knowledge rule). Each overlay row carries `source`, `as_of`, `confidence` (`DERIVED` | `ESTIMATED` | `CURATED`).

## How is this calculated?

1. **Domain weights** (CURATED, labelled ESTIMATED): Core 25%, GGV 20%, BZG 15%, AMG 15%, Intelligence 10%, Integrations 5%, Sale Readiness 5%, Factory health 5%.
2. **Per-capability maturity** from lifecycle (not file count):
   - IDEA / SPECIFIED = 0.05
   - APPROVED = 0.15
   - BUILDING = 0.35
   - BETA / SCHEMA_BUILT / TESTED = 0.55
   - PILOT = 0.70
   - VERIFIED = 0.85
   - LIVE = 1.0
   - RETIRED / NOT_TARGET = n/a (0)
3. **Commissioning penalty:** if BUILT / TESTED (or equivalent) but `HUMAN_COMMISSIONING ≠ DONE` → score capped at **0.65** (BUILT ≠ LIVE).
4. **Overall** = weighted average of domain scores. Shown as integer % + label **PARTIAL ESTIMATE** while CSV + overlay mix exists.
5. **Reconcile vs prior ~32%:** if computed differs by more than 8 points, UI shows a why note (new Core slices + Habitat / Uma verticals landed after that estimate).

## Views

Menu: Empire · Wolf Core · GGV · AMG · BZG · Intelligence · Integrations · Sale Readiness · Build Factory · Backlog  

Default: **Empire**.

### Mandatory distinctions

- BUILT ≠ HUMAN_COMMISSIONED ≠ LIVE
- WAITING_HUMAN ≠ BLOCKED_SYSTEM ≠ UNAPPROVED_POLICY ≠ INACCESSIBLE_SOURCE
- TARGET profit ≠ ACTUAL — ACTUAL NOT YET TRUSTWORTHY
- ESTIMATED labelled

### Verticals (accurate from canon / state)

**Habitat:** PLAN → WORK → EVIDENCE → APPROVAL → PUBLISH_GATE → METRICOOL → PERFORMANCE  
Metricool write **LOCKED**. APPROVED ≠ PUBLISHED. REAL_EXTERNAL_PUBLISH = no.

**Uma Close:** ESB → SNAPSHOT → CASH → RECONCILE → EXCEPTION → RESOLUTION → VERIFIED  
`WAITING_FOR_CLOSER` (WAITING_HUMAN). Variance policy **NOT_CONFIGURED** (policy gap, not system failure).

### Achievements

Locked until evidence: Foundations · First Real Workflow · First Human Commission · First External Action. Do not award without proof.

## Security

- Resolve CF JWT → Person; gate `person_id == PERS-MATT`.
- RBAC `progress.read` granted only to `ROLE-MATT` (migration `022_progress_dashboard`).
- No secrets, crown jewels, employee PII dumps, or bank numbers on this surface.

## Modules

- `scripts/core/progress_read_model.py`
- `state/progress/v1_overlay.json`
- `scripts/migrations/migrate_progress_dashboard.py`
- `dashboards/progress.html`
- `scripts/serve_beta.py` — `/progress`, `/api/progress*`
- `scripts/tests/test_progress_dashboard.py`
- Owner nav link on `dashboards/content-2.0.html` (PERS-MATT only)

## Forbidden

- ESB / Metricool / Production writes
- Habitat `content_planner` mutations
- Editing Phase 2.6 dirty WIP files for cosmetics
- Invented thresholds or fake % precision
