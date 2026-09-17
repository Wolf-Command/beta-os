-- Wolf Core Approval Engine (Beta only)
-- REQUESTED ≠ APPROVED ≠ EXECUTED ≠ OUTCOME.
-- Completing a linked Work Item does NOT approve.
-- Dual approval / SoD / delegation / UI / LLM = NOT BUILT.
-- Live Authority Limits remain 0 (this migration does not seed any).

CREATE TABLE IF NOT EXISTS core_approval_requests (
  approval_request_id TEXT PRIMARY KEY,
  request_type TEXT NOT NULL CHECK (request_type IN (
    'GENERAL', 'SPEND', 'EXCEPTION', 'ACCESS', 'HR', 'CONTRACT'
  )),
  title TEXT NOT NULL,
  description TEXT NULL,
  owning_entity_id TEXT NOT NULL,
  brand_id TEXT NULL,
  location_id TEXT NULL,
  department_id TEXT NULL,
  requested_by_person_id TEXT NOT NULL,
  requested_by_assignment_id TEXT NULL,
  required_permission_code TEXT NOT NULL,
  required_permission_id TEXT NOT NULL,
  material_amount TEXT NULL,
  currency TEXT NULL,
  source_type TEXT NOT NULL CHECK (source_type IN (
    'HUMAN', 'SYSTEM', 'WORK_ITEM', 'EXTERNAL'
  )),
  source_id TEXT NULL,
  evidence_reference TEXT NULL,
  status TEXT NOT NULL CHECK (status IN (
    'PENDING', 'APPROVED', 'REJECTED', 'CANCELLED', 'EXPIRED'
  )),
  requested_at TEXT NOT NULL,
  decided_at TEXT NULL,
  expires_at TEXT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  correlation_id TEXT NOT NULL,
  linked_work_item_id TEXT NULL,
  prior_request_id TEXT NULL,
  snapshot_hash TEXT NULL
);

CREATE INDEX IF NOT EXISTS idx_core_approval_req_status
  ON core_approval_requests(status);
CREATE INDEX IF NOT EXISTS idx_core_approval_req_entity
  ON core_approval_requests(owning_entity_id);
CREATE INDEX IF NOT EXISTS idx_core_approval_req_requester
  ON core_approval_requests(requested_by_person_id);
CREATE INDEX IF NOT EXISTS idx_core_approval_req_corr
  ON core_approval_requests(correlation_id);
CREATE INDEX IF NOT EXISTS idx_core_approval_req_linked_wi
  ON core_approval_requests(linked_work_item_id);

CREATE TABLE IF NOT EXISTS core_approval_decisions (
  approval_decision_id TEXT PRIMARY KEY,
  approval_request_id TEXT NOT NULL,
  decision TEXT NOT NULL CHECK (decision IN ('APPROVED', 'REJECTED')),
  decided_by_person_id TEXT NOT NULL,
  decided_by_assignment_id TEXT NULL,
  identity_assurance TEXT NULL,
  reason TEXT NULL,
  decided_at TEXT NOT NULL,
  authority_allowed INTEGER NOT NULL,
  authority_reason TEXT NULL,
  authority_matched_limit_id TEXT NULL,
  correlation_id TEXT NOT NULL,
  created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_core_approval_dec_request
  ON core_approval_decisions(approval_request_id);
CREATE INDEX IF NOT EXISTS idx_core_approval_dec_decider
  ON core_approval_decisions(decided_by_person_id);
CREATE INDEX IF NOT EXISTS idx_core_approval_dec_corr
  ON core_approval_decisions(correlation_id);

-- Append-only decisions: refuse UPDATE/DELETE at DB layer.
CREATE TRIGGER IF NOT EXISTS trg_core_approval_decisions_no_update
BEFORE UPDATE ON core_approval_decisions
BEGIN
  SELECT RAISE(ABORT, 'core_approval_decisions is append-only');
END;

CREATE TRIGGER IF NOT EXISTS trg_core_approval_decisions_no_delete
BEFORE DELETE ON core_approval_decisions
BEGIN
  SELECT RAISE(ABORT, 'core_approval_decisions is append-only');
END;
