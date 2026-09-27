# AUDIT — Wolf Person-Name Coupling — 2026-09-24

**Class:** Cheap/local succession audit (credit conservation).  
**Recorded:** 2026-09-24 15:48 WITA  
**Scope:** Beta workspace `scripts/`, `html/`, `dashboards/` (runtime), `state/` commissioning/runtime, `docs/canon` + active RULE/SPEC deliverables — **not** exhaustive historical chat.  
**Method:** `rg` patterns (Haikal, PERS-HAIKAL, ROLE-HAIKAL, haikalqilbari, Amanda, ROLE-MATT, send-Matt, Devi, Misa, hard-coded emails as authz). Cap ~40 strongest.  
**RULE:** `docs/RULE-Wolf-People-Are-Not-Roles-2026-09-24.md`  
**DB:** `catalog/content_library.sqlite` live facts below.  
**No Cursor launch. No DB mutate. No prod.**

## Live DB role facts (reconcile)

| Fact | Evidence |
| --- | --- |
| `PERS-HAIKAL` | exists (`org_persons`) |
| Haikal seat | `ASG-HAIKAL-VE-1` → `POS-VIDEO-EDITOR-1` → `ROLE-GGV-EDIT` (**Video Editor**) ACTIVE |
| Amanda seat | `ASG-AMANDA-CM-1` → `POS-CONTENT-MGMT-1` → `ROLE-CONTENT-MGMT` (**Content Management (TBD title)**) ACTIVE |
| Creative Director | `ROLE-GGV-CREATIVE-DIRECTOR` display **Creative Director** — **zero Assignments** |
| Content Crew | `ROLE-CONTENT-CREW` TBD; `ASG-MISA-CC-1` ACTIVE |
| `ROLE-MATT` | id person-named; display **Owner / Executive**; `ASG-MATT-OWNER-1` ACTIVE |
| `ROLE-HAIKAL` / `ROLE-CONTENT-DIRECTOR` | **do not exist** in `org_roles` (0 rows) |
| Habitat `default_assignee` | `haikalqilbari123@gmail.com` (email, not Assignment) |

**RECONCILE NEEDED (P0 succession debt):** CE / nav treat Haikal as content authority; seed Assignment is Video Editor.  
**Do NOT** create `ROLE-CONTENT-DIRECTOR` or `ROLE-HAIKAL` from this audit.  
**Candidates:** (A) seat Haikal on `ROLE-GGV-CREATIVE-DIRECTOR` if that is the org content-lead title; (B) rename TBD `ROLE-CONTENT-MGMT` display + re-seat (Amanda currently owns that seat); (C) Owner confirms Identity_Roles / HR title. **Recommend C then A if title = Creative Director; do not invent Content Director role id.**

## Classification legend

- **VALID PERSONALISATION** — greeting / label / fixture label for a human
- **VALID HISTORICAL ATTRIBUTION** — audit, commissioning evidence, who did X
- **VALID PERSON-SPECIFIC AUTHORITY** — rare; decision truly belongs to that human (not their seat)
- **INVALID PERSON COUPLING** — role/permission/workflow/nav/queue/business rule keyed by person/email

---

## INVALID PERSON COUPLING (priority)

### P0

| # | Finding | Where | Why invalid | Fix direction (later) |
| --- | --- | --- | --- | --- |
| 1 | CE / Content Machine ACL still **email-subject** `permissions` rows | `permissions` table: `haikalqilbari123@gmail.com`, `amanda@…`; `scripts/wolf_intelligence.py` `has_permission` transitional email path; canon already states this | Authz by email ≠ Assignment→Role | P0 in active CE pack fold: prefer Assignment→Role; email legacy until RBAC cutover registered |
| 2 | Haikal authority ≠ Video Editor seed | DB ASG vs CE/nav "content" fixture | Succession fails overnight | Owner reconcile A/B/C — no invent role |
| 3 | `brands.default_assignee` = Haikal email (Habitat) | DB + `serve_beta.py` / `skills/__init__.py` read path | Workflow default owner is a person email | Default assignee → Position/Role or Assignment id |
| 4 | `wolf_shell.PERSON_AUDIENCE` / `PERSON_ASSIGNMENTS` hard-map `PERS-HAIKAL` → content nav | `scripts/core/wolf_shell.py` | Nav/audience by person_id, not live Assignment→Role | Drive chrome from Assignment→Role→Audience |
| 5 | `ggv_ops_pack` seat frozensets `HAIKAL`/`AMANDA`/`MISA` person constants | `scripts/core/ggv_ops_pack.py` `READ_SEATS` / `OPERATOR_STAGES` / `CLOSE_SEATS` | Desk authority = named people | Role-permission checks |
| 6 | NAS index sample gate allows `PERS-MATT` \| `PERS-HAIKAL` person allowlist | `scripts/serve_beta.py` ~6500 | Capability gated by person_id | `can_upload` / Role grant only |
| 7 | Migrations grant on non-existent `ROLE-HAIKAL` / `ROLE-AMANDA` | `migrate_decision_memory_permissions.py`, `migrate_habitat_klaviyo_reader.py`, `migrate_lead_spine_operator.py` | Person-named role ids (and missing from `org_roles`) | Use `ROLE-GGV-EDIT` / `ROLE-CONTENT-MGMT` / real role ids |
| 8 | Phase2.5A permissions migration seeds by email | `migrate_phase2_5a_permissions.py`, still live in `permissions` | Authz matrix = emails | Migrate grants onto roles; retire email rows |

### P1

| # | Finding | Where | Why invalid | Fix direction |
| --- | --- | --- | --- | --- |
| 9 | `ROLE-MATT` person-named role **id** | `org_roles`, many migrations | Id encodes person; display already OK | Rename id only with migration plan (debt); never use id as "Matt the human" |
| 10 | Staff Ops / packs hard-code `HAIKAL = "PERS-HAIKAL"` seat constants | `staff_ops_routing.py`, `ggv_content_ops_depth.py`, CRM/GGV connective | Seat routing by person | Route by Role/Scope membership |
| 11 | CMQ card ids encode person as **capability ownership** risk | `CMQ-NAS-HAIKAL`, `CMQ-AMANDA-GGV`, `CMQ-DEVI-UMA-MOBILE`, `CMQ-GGV-FINANCE-NOTA-MATT` in `owner_commissioning_queue.py` | Card id OK if subject-of-test; INVALID if treated as permanent owner class | Keep as commissioning subject cards (VALID if person-under-test); escalate if used as workflow owner |
| 12 | Progress / harden "who": `"Haikal / Amanda"` fallback | `scripts/core/core_harden_pack.py` ~708; Progress canon Waiting-Others | Escalation destination by name | Role/seat label (Content lead / Content Mgmt) |
| 13 | RULE/UX copy "Primary Haikal nav" as architecture | `docs/RULE-Content-Engine-Staff-UX-2026-09-24.md` | Capability nav owned by person name | "Primary Content seat nav" + fixture note |
| 14 | Global Nav rule: "Matt widest; … Haikal content" | `docs/RULE-Wolf-Global-Navigation-Design-System-2026-09-22.md` | Audience described as people | Audience = Owner / BZG ops / Content role |
| 15 | `/api/content/nas-haikal-prep` + UI `haikal-nas-next` | `serve_beta.py`, `dashboards/content-2.0.html` | Endpoint/CSS named for person | Rename to content-seat NAS prep (when pack touches) |
| 16 | DEV subject list embeds Haikal email as default identity switcher | `dashboards/content-2.0.html` DEV_SUBJECTS | Dev fixture OK; must not be authz source | Keep as sim fixture; authz via Assignment |
| 17 | Founder-dep routing default `staff_seats` person map | `founder_dep_routing.py` | Seat presence = person flags | Assignment existence for Role |
| 18 | GGV Finance operating roles comment ties Amanda seat language to ROLE-CONTENT-MGMT OK — but tests/docs still say Matt/Amanda phones | `ggv_finance_nota.py` + commissioning | Mixed: role ids good; human commissioning cards person-subject | Cards = VALID person-under-test; rules stay on roles |
| 19 | Habitat publish approver set includes Creative Director (good) but Haikal not seated there | `migrate_habitat_publish_gate.py` / canon | Approver class role-based (VALID pattern) vs Haikal seed mismatch | Reconcile Assignment (A) |
| 20 | Identity_Roles.csv `ROLE-MATT` row "Matt / Owner" | `docs/canon/build-dashboard/Identity_Roles.csv` | Spreadsheet mixes person label into role | Display = Owner / Executive only |

### P2 (register only)

| # | Finding | Class note |
| --- | --- | --- |
| 21 | Honesty strips "Haikal human not started" across dashboards | Mostly VALID HISTORICAL / commissioning flag — rename eventual `content_seat_human` |
| 22 | Test fixtures using Haikal email / PERS-* | VALID for tests if not copied into runtime authz |
| 23 | `PERSON_HELLO` "Content" for PERS-HAIKAL | Borderline personalisation map — prefer role label from Assignment |
| 24 | Deliverable titles "Haikal Fail Repair" | VALID HISTORICAL pack naming — do not rewrite |
| 25 | Commissioning evidence JSON subject email | VALID HISTORICAL ATTRIBUTION / person-under-test |

---

## VALID (selected — do not "fix")

| # | Finding | Class |
| --- | --- | --- |
| V1 | Commissioning cards `CMQ-*-HAIKAL` as **Haikal-under-test** subject | VALID PERSON-SPECIFIC (commissioning) — not capability ownership |
| V2 | `CONTENT-ENGINE-HAIKAL-2026-09-24.md` / upload trace subject | VALID HISTORICAL ATTRIBUTION |
| V3 | "Good morning" / assignee display person + role | VALID PERSONALISATION (when implemented from authenticated person) |
| V4 | Approval `decided_by_person_id` in dual-approval tests/engine | VALID HISTORICAL ATTRIBUTION |
| V5 | `ROLE-MATT` **display_name** Owner / Executive | Partially remediated display (id still P1) |
| V6 | Nav matrix doc says fixtures not hard-code page logic | VALID intent (runtime `wolf_shell` still P0) |
| V7 | Habitat publish gate approvers listed as **roles** | VALID pattern |

## Surfaces checked (cheap)

Permissions, routes (`serve_beta`), navigation (`wolf_shell`), workflow ownership (GGV/AMG/BZG packs), notifications/queues (CMQ / Needs-You), dashboards (progress, content-2.0, staff-ops), Content Engine, GGV Finance, Owner surfaces. Not every historical GROK chat.

## Credit conservation

- No broad refactor this pass.  
- Active CE pack: fold Assignment→Role authz check only — see fold NOTE.  
- Open INVALID P0/P1 → Completion Register `wolf-people-are-not-roles-20260924`.  
- No `staff_ready`. No prod. Soft head preserved.
