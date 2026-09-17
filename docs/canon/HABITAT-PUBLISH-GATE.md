# Habitat Publish Gate — Canon

**LOCKED 2026-09-17.** Vertical-first. Core Approval Decision = canonical. Legacy Human_Approved is derived only. APPROVED ≠ PUBLISHED. Metricool write fail-closed on Beta until Matt enables Beta-local write. No creator≠approver SoD. Habitat approvers via Role/Permission: Creative Director, Content Mgmt, Video Editor, Content Crew, Owner.

## Honesty table

| Claim | Status |
|---|---|
| Core Approval = canonical for Habitat publish | **TRUE** |
| Legacy `Human_Approved` alone allows publish | **FALSE** (DENY) |
| `Human_Approved` derived from Core APPROVED | **TRUE** |
| APPROVED = PUBLISHED | **FALSE** |
| Metricool write on Beta | **DISABLED** (do not flip `.env`) |
| REAL_EXTERNAL_PUBLISH | **NO** |
| Gate stage when Core+version+evidence OK | `READY_TO_PUBLISH` |
| Version hash mismatch after edit | **DENY** |
| Live monetary Authority Limits | **0** |
| Live SoD / Exception seed | **0** |
| Live governance policies | **1** (`GPO-HABITAT-CONTENT-PUBLISH`) |
| Live evidence requirements | **1** (`EVR-HABITAT-CONTENT-PUBLISH`) |
| Action | `HABITAT.CONTENT.PUBLISH` |
| Entity / Scope | `ENT-GGV` / `SCOPE-GGV-CONTENT` |
| Brand | `habitat` under `ENT-GGV` |
| Creator ≠ approver SoD | **NOT REQUIRED** (Matt locked) |

## Flow

1. Edit slot → `content_version_hash` (SHA-256 fingerprint)
2. `POST /api/planner/submit-for-approval` → evidence `content_draft` + Core APR (`bind_policy` + `enforce_evidence`)
3. `POST /api/planner/approve` `{approve:true}` → Core decide only; on APPROVED set legacy `Human_Approved` + `approved_version_hash`
4. `GET /api/planner/publish-gate?id=` / `assert_publish_allowed` → Core gate; Metricool write stays disabled

## Migration

`scripts/migrations/020_habitat_publish_gate.sql` + `migrate_habitat_publish_gate.py` (idempotent; backs up DB + SHA-256).
