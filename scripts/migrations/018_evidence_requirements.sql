-- Wolf Core Evidence Requirement Enforcement (Beta only)
-- CLAIMED ≠ EVIDENCED ≠ VERIFIED.
-- Extends Audit/Evidence Spine — does not replace append-only audit events.
-- Live evidence requirements / evidence records remain 0. No business seed.
-- Cryptographic immutability NOT BUILT. object_ref = string only (no blobs).

CREATE TABLE IF NOT EXISTS core_evidence_types (
  evidence_type TEXT PRIMARY KEY,
  description TEXT NULL,
  status TEXT NOT NULL CHECK (status IN ('ACTIVE', 'INACTIVE')),
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS core_evidence_records (
  evidence_id TEXT PRIMARY KEY,
  entity_id TEXT NOT NULL,
  scope_id TEXT NULL,
  evidence_type TEXT NOT NULL,
  source_type TEXT NOT NULL,
  source_reference TEXT NULL,
  object_ref TEXT NULL,
  content_hash TEXT NULL,
  submitted_by_person_id TEXT NOT NULL,
  submitted_by_assignment_id TEXT NULL,
  submitted_at TEXT NOT NULL,
  captured_at TEXT NULL,
  status TEXT NOT NULL CHECK (status IN ('ACTIVE', 'INVALIDATED')),
  verification_status TEXT NOT NULL CHECK (
    verification_status IN ('SUBMITTED', 'VERIFIED', 'REJECTED')
  ),
  verified_by_person_id TEXT NULL,
  verified_at TEXT NULL,
  verification_reason TEXT NULL,
  governed_object_type TEXT NOT NULL,
  governed_object_id TEXT NOT NULL,
  classification TEXT NULL,
  metadata_json TEXT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  invalidated_at TEXT NULL,
  invalidate_reason TEXT NULL,
  FOREIGN KEY (evidence_type) REFERENCES core_evidence_types(evidence_type)
);

CREATE INDEX IF NOT EXISTS idx_core_evidence_entity_type
  ON core_evidence_records(entity_id, evidence_type, status);

CREATE INDEX IF NOT EXISTS idx_core_evidence_object
  ON core_evidence_records(governed_object_type, governed_object_id);

CREATE INDEX IF NOT EXISTS idx_core_evidence_scope
  ON core_evidence_records(scope_id);

CREATE INDEX IF NOT EXISTS idx_core_evidence_verification
  ON core_evidence_records(verification_status, status);

CREATE TABLE IF NOT EXISTS core_evidence_requirements (
  requirement_id TEXT NOT NULL,
  requirement_version INTEGER NOT NULL,
  entity_id TEXT NOT NULL,
  scope_id TEXT NULL,
  action_type TEXT NOT NULL,
  request_type TEXT NULL,
  evidence_type TEXT NOT NULL,
  min_count INTEGER NOT NULL CHECK (min_count >= 1),
  verification_needed INTEGER NOT NULL CHECK (verification_needed IN (0, 1)),
  effective_from TEXT NOT NULL,
  effective_to TEXT NULL,
  status TEXT NOT NULL CHECK (status IN ('ACTIVE', 'INACTIVE')),
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  created_by_person_id TEXT NULL,
  PRIMARY KEY (requirement_id, requirement_version),
  FOREIGN KEY (evidence_type) REFERENCES core_evidence_types(evidence_type)
);

CREATE INDEX IF NOT EXISTS idx_core_evidence_req_entity_action
  ON core_evidence_requirements(entity_id, action_type, status);

CREATE INDEX IF NOT EXISTS idx_core_evidence_req_scope
  ON core_evidence_requirements(scope_id);

CREATE INDEX IF NOT EXISTS idx_core_evidence_req_effective
  ON core_evidence_requirements(effective_from, effective_to);

-- Defense-in-depth: refuse hard DELETE (invalidate path only).
CREATE TRIGGER IF NOT EXISTS trg_core_evidence_records_no_delete
BEFORE DELETE ON core_evidence_records
BEGIN
  SELECT RAISE(ABORT, 'core_evidence_records refuses hard delete; use invalidate');
END;
