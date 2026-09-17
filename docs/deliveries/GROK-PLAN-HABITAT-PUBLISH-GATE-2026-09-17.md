# GROK PLAN — Habitat Publish Gate on Wolf Core

**Vertical-first.** Reuse Content Machine slots. Core Approval = canonical.

## Object model (smallest)

`content_planner` slot (existing)
+ `content_version_hash` TEXT + `core_approval_request_id` TEXT nullable + `work_item_id` TEXT nullable
+ optional `content_versions` append table: (slot_id, version_hash, caption, media_ref, platform, payload_json, created_at, created_by_person_id)

Fingerprint = SHA-256 of canonical JSON: brand, platform, title_slug, script_body, raw_asset_id (normalize whitespace). Material edit → new hash → prior approval invalid for publish.

## Org corrections (Matt-approved policy)

1. Add brand `GGV-HABITAT` / brand_id habitat under ENT-GGV if missing (align string `habitat`).
2. Add SCOPE-GGV-HABITAT (brand target) OR bind policy on action `habitat.content.publish` + entity ENT-GGV + scope SCOPE-GGV-CONTENT (narrow by action_type — preferred smallest).
3. Add ROLE-GGV-CREATIVE-DIRECTOR (no person unless known) + Position optional.
4. Permission `content.habitat.approve` + `content.habitat.publish.request`
5. Grant approve to: ROLE-MATT, ROLE-GGV-CREATIVE-DIRECTOR, ROLE-CONTENT-MGMT, ROLE-GGV-EDIT, ROLE-CONTENT-CREW
6. Grant publish.request to roles that schedule (CONTENT-CREW + CONTENT-MGMT + MATT at minimum)
**No hard-coded name lists.** No creator≠approver SoD.

## Live Habitat policy (Matt locked — ALLOWED seed)

`core_governance_policies` row:
- entity ENT-GGV, scope SCOPE-GGV-CONTENT (or Habitat scope), action_type=`habitat.content.publish`
- required_decision_count=1, evidence_required=1, prohibited=0
- required_permission = content.habitat.approve

`core_evidence_requirements`:
- same action: evidence_type=`content_draft` (add to types registry), min_count=1, verification_needed=0

Do NOT seed SoD/Exception/Authority money.

## Flow

1. Producer edits slot → compute version hash → create/update Work Item (owner=producer Person)
2. Submit for approval: attach Core Evidence (content_draft ref = slot_id+version_hash+preview) → create Approval Request (bind_policy=True, enforce_evidence=True, source=content_planner:{id}, snapshot includes version_hash)
3. Approver decides via Core `/api/core/approvals/...` OR thin wrapper `/api/planner/approve` that **only** calls Core decide after evidence check; on APPROVED set legacy Human_Approved **derived** from Core (never reverse)
4. Publish gate `assert_publish_allowed`:
   - verified auth
   - brand==habitat
   - current version_hash matches approval snapshot
   - Core request APPROVED for this slot+version
   - evidence satisfied
   - approver had content.habitat.approve (already in decision)
   - Metricool: if write disabled → return READY_TO_PUBLISH + reason metricool_write_disabled (HTTP 200 gate status, not PUBLISHED)
5. Legacy Human_Approved alone: **DENY** publish (Core required)

## Metricool

Keep write disabled. Gate proves READY. Report REAL_EXTERNAL_PUBLISH=NO reason standing Beta lock.

## Tests

Isolated fixtures + one Habitat slot path. All Matt mandatory cases. No Metricool network in tests.
