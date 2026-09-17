-- Wolf Core Work Items (Beta only)
-- Something that must be done. NOT Organisation Assignment (org_assignments).
-- COMPLETED = claimed; VERIFIED = separate step. No Evidence File Store this slice.

CREATE TABLE IF NOT EXISTS core_work_items (
  work_item_id TEXT PRIMARY KEY,
  title TEXT NOT NULL,
  description TEXT NULL,
  work_type TEXT NOT NULL CHECK (work_type IN (
    'GENERAL', 'FOLLOW_UP', 'EXCEPTION', 'MAINTENANCE',
    'APPROVAL_REQUIRED', 'AUDIT_FINDING', 'CONTENT', 'SYSTEM'
  )),
  status TEXT NOT NULL CHECK (status IN (
    'OPEN', 'IN_PROGRESS', 'BLOCKED', 'COMPLETED', 'VERIFIED', 'CANCELLED'
  )),
  priority INTEGER NOT NULL DEFAULT 3 CHECK (priority BETWEEN 1 AND 5),
  owning_entity_id TEXT NOT NULL,
  source_type TEXT NOT NULL CHECK (source_type IN (
    'HUMAN', 'SYSTEM', 'AUDIT', 'ROUTINE', 'RECOMMENDATION_ACCEPTED', 'EXTERNAL'
  )),
  source_id TEXT NULL,
  created_by_actor_type TEXT NOT NULL CHECK (created_by_actor_type IN ('PERSON', 'SYSTEM')),
  created_by_person_id TEXT NULL,
  owner_person_id TEXT NULL,
  owner_org_assignment_id TEXT NULL,
  due_at TEXT NULL,
  started_at TEXT NULL,
  completed_at TEXT NULL,
  verified_at TEXT NULL,
  outcome TEXT NULL,
  completion_evidence_reference TEXT NULL,
  parent_work_item_id TEXT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  CHECK (
    (created_by_actor_type = 'SYSTEM' AND created_by_person_id IS NULL)
    OR (created_by_actor_type = 'PERSON' AND created_by_person_id IS NOT NULL)
  )
);

CREATE INDEX IF NOT EXISTS idx_core_work_items_entity ON core_work_items(owning_entity_id);
CREATE INDEX IF NOT EXISTS idx_core_work_items_owner ON core_work_items(owner_person_id);
CREATE INDEX IF NOT EXISTS idx_core_work_items_status ON core_work_items(status);
CREATE INDEX IF NOT EXISTS idx_core_work_items_due ON core_work_items(due_at);
CREATE INDEX IF NOT EXISTS idx_core_work_items_parent ON core_work_items(parent_work_item_id);
