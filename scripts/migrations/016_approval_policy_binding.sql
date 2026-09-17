-- Wolf Core Approval Policy Binding (Beta only)
-- Deterministic ACTION → REQUIRED CONTROL. Fail closed: no match ≠ allow.
-- Live governance policies remain 0. No real business thresholds.
-- governing_policy_* columns added idempotently by migrate_approval_policy_binding.py
-- (SQLite ALTER TABLE ADD COLUMN).

CREATE TABLE IF NOT EXISTS core_governance_policies (
  policy_id TEXT NOT NULL,
  policy_version INTEGER NOT NULL,
  entity_id TEXT NOT NULL,
  scope_id TEXT NULL,
  action_type TEXT NOT NULL,
  request_type TEXT NULL,
  required_permission_code TEXT NULL,
  authority_required INTEGER NOT NULL DEFAULT 0,
  approval_required INTEGER NOT NULL DEFAULT 0,
  required_decision_count INTEGER NOT NULL DEFAULT 0,
  evidence_required INTEGER NOT NULL DEFAULT 0,
  prohibited INTEGER NOT NULL DEFAULT 0,
  amount_min TEXT NULL,
  amount_max TEXT NULL,
  currency TEXT NULL,
  effective_from TEXT NOT NULL,
  effective_to TEXT NULL,
  status TEXT NOT NULL CHECK (status IN ('ACTIVE', 'INACTIVE')),
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  created_by_person_id TEXT NULL,
  PRIMARY KEY (policy_id, policy_version),
  CHECK (
    (amount_min IS NULL AND amount_max IS NULL AND currency IS NULL)
    OR (currency IS NOT NULL)
  ),
  CHECK (
    approval_required = 0 OR required_decision_count >= 1
  )
);

CREATE INDEX IF NOT EXISTS idx_core_gov_pol_entity_action
  ON core_governance_policies(entity_id, action_type, status);

CREATE INDEX IF NOT EXISTS idx_core_gov_pol_scope
  ON core_governance_policies(scope_id);

CREATE INDEX IF NOT EXISTS idx_core_gov_pol_effective
  ON core_governance_policies(effective_from, effective_to);
