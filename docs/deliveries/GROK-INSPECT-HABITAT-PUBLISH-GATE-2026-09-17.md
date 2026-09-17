# GROK INSPECTION — Habitat Content Machine (2026-09-17)

## Verified (Beta `catalog/content_library.sqlite` + `scripts/serve_beta.py`)

### Org
- Persons: PERS-MATT, PERS-AMANDA, PERS-HAIKAL, PERS-MISA (all ACTIVE + email AuthIdentity)
- Assignments: Matt→Owner; Amanda→CONTENT-MGMT; Haikal→Video Editor; Misa→Content Crew; all on SCOPE-GGV-CONTENT
- **No ROLE “Creative Director” exists.** Closest: ROLE-CONTENT-MGMT (Amanda). Must ADD `ROLE-GGV-CREATIVE-DIRECTOR` (empty seat OK) + grant Habitat approve perm to Matt/Amanda/Haikal/Misa roles.
- **Habitat brand NOT in org_brands** (only BZG/AMG brands). Content Machine uses string brand `habitat` on `content_planner`.

### Content object
- Primary pilot object: **`content_planner` slot** (id, brand, platform, scheduled_date, slot_time, title_slug, script_body, raw_asset_id, status)
- Status flow: Draft → AI_Generated → **Human_Approved** → Ready_for_Render
- `POST /api/planner/approve` sets Human_Approved **without Core Approval**
- `assert_publish_allowed(slot_id)` only checks status==Human_Approved (**legacy bypass risk**)
- Parallel: `content_plans` / `plan_revisions` (plan-level) — NOT the Metricool slot path. Pilot = **planner slot**, not fortnight plan.

### Work Item / Approval / Evidence
- serve_beta imports core.work_items + core.approvals but planner approve path does **not** create them yet.

### Metricool
- `BETA_METRICOOL_ENABLED=false`, `BETA_METRICOOL_WRITE_ENABLED=false` (standing Beta fail-closed)
- Only READ sync exists. **No safe write/publish path today.**
- Pilot must: prove gate → READY_TO_PUBLISH; **REAL_EXTERNAL_PUBLISH = NO** unless Matt later enables Beta-local Metricool write creds. Do not fake PUBLISHED.

### UI
- content boards / content-2.0.html; brand habitat in BRANDS tuple.
