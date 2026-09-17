-- Wolf Core Exception / Override Governance (Beta only)
-- EXCEPTION ≠ COMPLIANCE. Normal control failure is preserved.
-- Live exceptions remain 0. No business exception seed.
-- Matt Person (PERS-MATT) only may authorise/revoke (enforced in application).

CREATE TABLE IF NOT EXISTS core_exceptionable_controls (
  control_type TEXT NOT NULL,
  control_reference TEXT NOT NULL,
  exceptionable INTEGER NOT NULL CHECK (exceptionable IN (0, 1)),
  required_for_authorise INTEGER NOT NULL DEFAULT 0
    CHECK (required_for_authorise IN (0, 1)),
  status TEXT NOT NULL CHECK (status IN ('ACTIVE', 'INACTIVE')),
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  PRIMARY KEY (control_type, control_reference)
);

CREATE INDEX IF NOT EXISTS idx_core_exceptionable_controls_type
  ON core_exceptionable_controls(control_type, exceptionable, status);

CREATE TABLE IF NOT EXISTS core_governance_exceptions (
  exception_id TEXT PRIMARY KEY,
  entity_id TEXT NOT NULL,
  scope_id TEXT NULL,
  governed_object_type TEXT NOT NULL,
  governed_object_id TEXT NOT NULL,
  control_type TEXT NOT NULL,
  control_reference TEXT NOT NULL,
  requested_by_person_id TEXT NOT NULL,
  authorised_by_person_id TEXT NULL,
  reason TEXT NOT NULL,
  evidence_id TEXT NULL,
  effective_from TEXT NOT NULL,
  expires_at TEXT NULL,
  status TEXT NOT NULL CHECK (
    status IN (
      'REQUESTED',
      'AUTHORISED',
      'CONSUMED',
      'REJECTED',
      'REVOKED',
      'EXPIRED'
    )
  ),
  usage_limit INTEGER NOT NULL DEFAULT 1 CHECK (usage_limit >= 1),
  used_count INTEGER NOT NULL DEFAULT 0 CHECK (used_count >= 0),
  created_at TEXT NOT NULL,
  authorised_at TEXT NULL,
  rejected_at TEXT NULL,
  revoked_at TEXT NULL,
  consumed_at TEXT NULL,
  correlation_id TEXT NULL,
  revoke_reason TEXT NULL,
  reject_reason TEXT NULL
);

CREATE INDEX IF NOT EXISTS idx_core_gov_exc_entity_control
  ON core_governance_exceptions(entity_id, control_type, control_reference, status);

CREATE INDEX IF NOT EXISTS idx_core_gov_exc_object
  ON core_governance_exceptions(governed_object_type, governed_object_id);

CREATE INDEX IF NOT EXISTS idx_core_gov_exc_scope
  ON core_governance_exceptions(scope_id);

CREATE INDEX IF NOT EXISTS idx_core_gov_exc_effective
  ON core_governance_exceptions(effective_from, expires_at);

CREATE INDEX IF NOT EXISTS idx_core_gov_exc_status
  ON core_governance_exceptions(status);

-- Defense-in-depth: refuse hard DELETE (lifecycle only).
CREATE TRIGGER IF NOT EXISTS trg_core_governance_exceptions_no_delete
BEFORE DELETE ON core_governance_exceptions
BEGIN
  SELECT RAISE(ABORT, 'core_governance_exceptions refuses hard delete; use revoke/reject lifecycle');
END;
