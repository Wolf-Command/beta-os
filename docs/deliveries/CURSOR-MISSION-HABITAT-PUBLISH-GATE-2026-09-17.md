# CURSOR MISSION — Habitat Publish Gate on Wolf Core

Workspace `/Users/wolfterminal/beta-os` branch `build/wolf-command-rebuild`
Commit: `feat(content): habitat publish gate on wolf core`
Production sacred. Metricool write stays disabled unless already true (do NOT flip .env).

Read first:
- docs/deliveries/GROK-INSPECT-HABITAT-PUBLISH-GATE-2026-09-17.md
- docs/deliveries/GROK-PLAN-HABITAT-PUBLISH-GATE-2026-09-17.md
- scripts/serve_beta.py (approve, assert_publish_allowed)
- scripts/core/{approvals,evidence,governance_policy,work_items,rbac}.py

## Implement

### Org/policy seed (Habitat pilot ONLY — Matt locked)
- Brand habitat under ENT-GGV if missing
- ROLE-GGV-CREATIVE-DIRECTOR + perms content.habitat.approve / content.habitat.publish.request
- Grant approve to ROLE-MATT, ROLE-GGV-CREATIVE-DIRECTOR, ROLE-CONTENT-MGMT, ROLE-GGV-EDIT, ROLE-CONTENT-CREW
- evidence type content_draft
- ONE governance policy + ONE evidence requirement for action habitat.content.publish (ENT-GGV / SCOPE-GGV-CONTENT)
- Backup DB before migration; record SHA-256
- Migration 020_habitat_publish_gate.sql + migrate script; idempotent
- LIVE monetary authority stays 0; no SoD/Exception seed

### content_planner columns
content_version_hash, work_item_id, core_approval_request_id, approved_version_hash nullable

### content_versions table (append)
slot_id, version_hash PK-ish, fingerprint fields, created_by_person_id, created_at

### scripts/core/content_publish.py (or content_habitat.py)
- compute_version_hash(slot)
- ensure_work_item_for_slot
- submit_for_approval (evidence + create_approval_request bind_policy+enforce_evidence)
- assert_habitat_publish_allowed(slot_id, verified_person) — Core canonical; legacy status alone DENY; version mismatch DENY; return {ok, stage: READY_TO_PUBLISH|DENIED, reason, metricool: DISABLED}

### Wire serve_beta
- POST /api/planner/approve → Core path only (thin wrapper). Derive Human_Approved from Core APPROVED. Reject spoof.
- assert_publish_allowed + GET publish-gate → new Core gate
- Block save from setting Human_Approved (already) + block any path that publishes on legacy alone
- Do not enable Metricool write

### Tests scripts/tests/test_habitat_publish_gate.py
All Matt mandatory cases. Metricool write remains blocked. Core regressions green.

### Docs
docs/canon/HABITAT-PUBLISH-GATE.md honesty table. Commit message exact. EXIT:0/1.
