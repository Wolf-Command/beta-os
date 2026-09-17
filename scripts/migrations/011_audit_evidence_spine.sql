-- Wolf Core Audit / Evidence Spine (Beta only)
-- Append-only structured events. No hash-chain / court-grade immutability this slice.
-- Secret fields never stored. Corrections = new INSERT with corrects_event_id.

CREATE TABLE IF NOT EXISTS core_audit_events (
  audit_event_id TEXT PRIMARY KEY,
  occurred_at TEXT NOT NULL,
  recorded_at TEXT NOT NULL,
  created_at TEXT NOT NULL,
  actor_type TEXT NOT NULL CHECK (actor_type IN ('PERSON', 'SYSTEM')),
  actor_person_id TEXT NULL,
  actor_auth_identity_id TEXT NULL,
  actor_assignment_id TEXT NULL,
  identity_assurance TEXT NULL,
  entity_id TEXT NULL,
  brand_id TEXT NULL,
  location_id TEXT NULL,
  department_id TEXT NULL,
  scope_id TEXT NULL,
  action TEXT NOT NULL,
  resource_type TEXT NULL,
  resource_id TEXT NULL,
  result TEXT NOT NULL CHECK (result IN ('ALLOWED', 'DENIED', 'SUCCEEDED', 'FAILED', 'ERROR')),
  reason_code TEXT NULL,
  correlation_id TEXT NOT NULL,
  source TEXT NOT NULL,
  before_hash TEXT NULL,
  after_hash TEXT NULL,
  evidence_reference TEXT NULL,
  corrects_event_id TEXT NULL,
  metadata_json TEXT NULL,
  CHECK (
    (actor_type = 'SYSTEM' AND actor_person_id IS NULL)
    OR (actor_type = 'PERSON' AND actor_person_id IS NOT NULL)
  )
);

CREATE INDEX IF NOT EXISTS idx_core_audit_occurred ON core_audit_events(occurred_at);
CREATE INDEX IF NOT EXISTS idx_core_audit_actor ON core_audit_events(actor_person_id);
CREATE INDEX IF NOT EXISTS idx_core_audit_action ON core_audit_events(action);
CREATE INDEX IF NOT EXISTS idx_core_audit_result ON core_audit_events(result);
CREATE INDEX IF NOT EXISTS idx_core_audit_corr ON core_audit_events(correlation_id);
CREATE INDEX IF NOT EXISTS idx_core_audit_source ON core_audit_events(source);
CREATE INDEX IF NOT EXISTS idx_core_audit_entity ON core_audit_events(entity_id);

-- Defense-in-depth: refuse UPDATE/DELETE at the database layer.
CREATE TRIGGER IF NOT EXISTS trg_core_audit_events_no_update
BEFORE UPDATE ON core_audit_events
BEGIN
  SELECT RAISE(ABORT, 'core_audit_events is append-only');
END;

CREATE TRIGGER IF NOT EXISTS trg_core_audit_events_no_delete
BEFORE DELETE ON core_audit_events
BEGIN
  SELECT RAISE(ABORT, 'core_audit_events is append-only');
END;
