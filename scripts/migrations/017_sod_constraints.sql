-- Wolf Core Segregation of Duties Constraints (Beta only)
-- AUTHORISED ≠ PERMITTED TO PERFORM EVERY STEP.
-- Dual ≠ SoD. Independence is Person-based.
-- Live SoD constraints remain 0. No real business matrix seed.
-- this slice: SAME_PERSON_FORBIDDEN only.

CREATE TABLE IF NOT EXISTS core_sod_constraints (
  constraint_id TEXT NOT NULL,
  constraint_version INTEGER NOT NULL,
  entity_id TEXT NOT NULL,
  scope_id TEXT NULL,
  process_family TEXT NOT NULL,
  prior_action TEXT NOT NULL,
  proposed_action TEXT NOT NULL,
  relationship TEXT NOT NULL CHECK (relationship IN ('SAME_PERSON_FORBIDDEN')),
  effective_from TEXT NOT NULL,
  effective_to TEXT NULL,
  status TEXT NOT NULL CHECK (status IN ('ACTIVE', 'INACTIVE')),
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  created_by_person_id TEXT NULL,
  PRIMARY KEY (constraint_id, constraint_version)
);

CREATE INDEX IF NOT EXISTS idx_core_sod_constraints_entity_action
  ON core_sod_constraints(entity_id, process_family, proposed_action, status);

CREATE INDEX IF NOT EXISTS idx_core_sod_constraints_scope
  ON core_sod_constraints(scope_id);

CREATE INDEX IF NOT EXISTS idx_core_sod_constraints_effective
  ON core_sod_constraints(effective_from, effective_to);

-- Optional participation ledger for generic fixture evidence.
-- APPROVAL family prefers canonical request/decision tables.
CREATE TABLE IF NOT EXISTS core_sod_participation (
  participation_id TEXT PRIMARY KEY,
  person_id TEXT NOT NULL,
  action TEXT NOT NULL,
  subject_id TEXT NOT NULL,
  entity_id TEXT NOT NULL,
  scope_id TEXT NULL,
  recorded_at TEXT NOT NULL,
  source_type TEXT NOT NULL CHECK (source_type IN ('SYSTEM', 'TEST'))
);

CREATE INDEX IF NOT EXISTS idx_core_sod_participation_subject
  ON core_sod_participation(subject_id, action);

CREATE INDEX IF NOT EXISTS idx_core_sod_participation_person
  ON core_sod_participation(person_id, action);

CREATE INDEX IF NOT EXISTS idx_core_sod_participation_entity
  ON core_sod_participation(entity_id);
