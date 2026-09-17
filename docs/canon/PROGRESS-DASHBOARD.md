# Progress Dashboard — Canon (v2.1 semantic Owner Cockpit)

**Status:** BUILT + TESTED 2026-09-17 (Cursor Local Agent) — v2.1 semantic correction  
**Run:** `BF-progress-dashboard-v21-20260917`  
**Decision:** `2026-09-17 · PICK: Matt Progress Dashboard v1 on Beta only` (v2 / v2.1 extend same surface)  
**Audience:** Owner / `PERS-MATT` only. Staff seats → **403**.

## Honesty

```
progress_type: PARTIAL_ESTIMATE
master_build_csv_staleness: KNOWN
overlay_required: YES
BUILT ≠ HUMAN_COMMISSIONED ≠ LIVE
WAITING ≠ BLOCKED ≠ PLANNED ≠ UNAPPROVED_POLICY
TARGET profit ≠ ACTUAL (ACTUAL NOT YET TRUSTWORTHY)
Factory HEALTHY ≠ mission complete
```

No invented AI percentages. Peaches recommendations are not APPROVED. Domain weights labelled **ESTIMATED** until a registry owns them. Empire hero shows **status vocabulary without exclusive aggregate counts** (categories overlap).

## Architecture

```
docs/canon/build-dashboard/*.csv
+ state/build-factory/runs/*.json (read-only → factory_health status)
+ state/progress/v1_overlay.json (provenance + owner_cockpit + commissioning_missions + policy_decisions)
    → scripts/core/progress_read_model.py
    → GET /api/progress* (Owner only)
    → dashboards/progress.html (+ /progress)
```

Overlay fills gaps where `Master_Build.csv` is stale vs proven commits. Each overlay row carries `source`, `as_of`, `confidence` (`DERIVED` | `ESTIMATED` | `CURATED`). Owner cockpit fields live under `owner_cockpit`. Curated `commissioning_missions[]` and `policy_decisions[]` drive Empire NEEDS YOU / WAITING ON OTHERS / POLICY DECISIONS.

## How is this calculated?

1. **Domain weights** (CURATED, labelled ESTIMATED; **Factory health EXCLUDED**): Core ~26%, GGV ~21%, BZG ~16%, AMG ~16%, Intelligence ~11%, Integrations ~5%, Sale Readiness ~5% (prior ratios ÷0.95 after removing Factory 5%).
2. **Factory health** is separate system status ∈ {**HEALTHY**, **DEGRADED**, **FAILING**} from deterministic checks. **Not** mission maturity.
3. **Tracked denominator (unchanged):** Core 18 · GGV 3 · BZG 2 · AMG 1 · Intelligence 2 · Integrations 5 · Sale Readiness 61 · **total 92**. Overall **~28%** PARTIAL ESTIMATE — do not change unless scoring inputs change.
4. **Core %** = maturity of **tracked approved Core capabilities in Master_Build+overlay** (`item_count` denominator) — **NOT** “all imaginable Wolf Core forever”.
5. **Per-capability maturity** from lifecycle (not file count):
   - IDEA / SPECIFIED = 0.05
   - APPROVED = 0.15
   - BUILDING = 0.35
   - BETA / SCHEMA_BUILT / TESTED = 0.55
   - PILOT = 0.70
   - VERIFIED = 0.85
   - LIVE = 1.0
   - RETIRED / NOT_TARGET = n/a (0)
6. **Commissioning penalty:** if BUILT / TESTED (or equivalent) but `HUMAN_COMMISSIONING ≠ DONE` → score capped at **0.65** (BUILT ≠ LIVE).
7. **Waiting class:** SPECIFIED / IDEA / APPROVED → **PLANNED**. `UNAPPROVED_POLICY` only from curated `policy_decisions[]` (or explicit row / vertical flags) — never auto-mapped from every not-yet-built capability.
8. **Human commissioning** = curated evidence list only (`needs_you` / `waiting_on_others`). Core is proven through verticals — **no Matt-per-primitive Core governance commission queue**.
9. **Overall** = weighted average of **mission** domain scores (no Factory). Shown as integer % + label **PARTIAL ESTIMATE**.
10. **Prior 27% → new value:** v1 overall included Factory at 5% weight (~27%). v2 removes Factory and re-normalizes. Why-vs-prior and builder honesty (`progress_type`, CSV staleness, overlay required) live under HOW CALCULATED / DETAILS — not Empire hero.

## Owner Cockpit (Empire)

Hierarchy: How far are we? (phase + vocabulary chips, no fake counts) → **Needs you** → **Waiting on others** → **Policy decisions** (individual cards) → Owner pulse → Next 3 moves → Recent wins → Milestone road → Domain cards.

Genuine queues (evidence):
- **NEEDS YOU:** Progress Dashboard UX commissioning (Matt, ACTIVE while iterating).
- **WAITING ON OTHERS:** Habitat → Haikal/Amanda; Uma Blu → verified closer.
- **POLICY:** Uma variance threshold; optional Authorised Knowledge Resolution as Owner decision.

Raw IDs (`PERS-` / `EVR-` / `ROLE-` / `GPO-`) stay in DETAILS / technical_details.

## Views

Menu: Empire · Wolf Core · GGV · AMG · BZG · Intelligence · Integrations · Sale Readiness · Build Factory · Backlog  

Default: **Empire**.

### Mandatory distinctions

- BUILT ≠ HUMAN_COMMISSIONED ≠ LIVE
- WAITING_HUMAN ≠ BLOCKED_SYSTEM ≠ UNAPPROVED_POLICY ≠ INACCESSIBLE_SOURCE ≠ PLANNED
- TARGET profit ≠ ACTUAL — ACTUAL NOT YET TRUSTWORTHY
- ESTIMATED labelled
- Factory HEALTHY ≠ mission complete

### Verticals (owner stages)

**Habitat (owner):** PLAN → WORK → PROOF → APPROVAL → PUBLISH READY → PUBLISH → LEARN  
Metricool write **LOCKED**. APPROVED ≠ PUBLISHED. REAL_EXTERNAL_PUBLISH = no.

**Uma Close (owner):** ESB DATA → CASH COUNT → CHECK → EXCEPTION → FIX → VERIFIED CLOSE  
`WAITING_FOR_CLOSER` (WAITING_HUMAN). Variance policy **NOT_CONFIGURED** (policy gap, not system failure).

### Milestone road

Foundations → First Real Workflow → Second Business Vertical → First Human Commission → First External Action → Buyer Ready.  
Evidence unlock: Foundations + First Real Workflow + Second Business Vertical when Core verticals + Habitat + Uma built. Commission / external / buyer stay locked without proof.

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
- Putting Factory health back into mission weighted %
- Inventing Matt Core governance commission missions
- Inflating POLICY from every SPECIFIED / IDEA / APPROVED row
