-- Wolf Core Delegation (Beta only)
-- IDENTITY NEVER DELEGATES. No re-delegation. Live Authority Limits stay 0.
-- Dual / SoD / UI / LLM = NOT BUILT.

CREATE TABLE IF NOT EXISTS core_delegations (
  delegation_id TEXT PRIMARY KEY,
  delegator_person_id TEXT NOT NULL,
  delegator_assignment_id TEXT NOT NULL,
  delegate_person_id TEXT NOT NULL,
  delegate_assignment_id TEXT NOT NULL,
  entity_id TEXT NOT NULL,
  scope_id TEXT NOT NULL,
  permission_id TEXT NOT NULL,
  permission_code TEXT NOT NULL,
  authority_limit_id TEXT NULL,
  delegated_cap_amount TEXT NULL,
  currency TEXT NULL,
  effective_from TEXT NOT NULL,
  effective_to TEXT NOT NULL,
  status TEXT NOT NULL CHECK (status IN (
    'SCHEDULED', 'ACTIVE', 'EXPIRED', 'REVOKED'
  )),
  reason TEXT NULL,
  created_at TEXT NOT NULL,
  created_by_person_id TEXT NOT NULL,
  revoked_at TEXT NULL,
  revoked_by_person_id TEXT NULL,
  revoke_reason TEXT NULL,
  correlation_id TEXT NOT NULL,
  allow_redelegation INTEGER NOT NULL DEFAULT 0 CHECK (allow_redelegation = 0),
  linked_work_item_id TEXT NULL
);

CREATE INDEX IF NOT EXISTS idx_core_delegations_status
  ON core_delegations(status);
CREATE INDEX IF NOT EXISTS idx_core_delegations_delegator
  ON core_delegations(delegator_person_id);
CREATE INDEX IF NOT EXISTS idx_core_delegations_delegate
  ON core_delegations(delegate_person_id);
CREATE INDEX IF NOT EXISTS idx_core_delegations_entity
  ON core_delegations(entity_id);
CREATE INDEX IF NOT EXISTS idx_core_delegations_permission
  ON core_delegations(permission_id);
CREATE INDEX IF NOT EXISTS idx_core_delegations_window
  ON core_delegations(effective_from, effective_to);
CREATE INDEX IF NOT EXISTS idx_core_delegations_corr
  ON core_delegations(correlation_id);
