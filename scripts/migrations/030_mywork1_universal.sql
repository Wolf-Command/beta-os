-- MYWORK-1 — Universal My Work extensions (Beta only).
-- Extends core_work_items; does not invent a second task engine.
-- COMPLETED (DONE claimed) ≠ VERIFIED.

-- Task handoff chain (distinct from permission-cap core_delegations).
CREATE TABLE IF NOT EXISTS core_work_delegations (
  delegation_id TEXT PRIMARY KEY,
  work_item_id TEXT NOT NULL,
  from_person_id TEXT NOT NULL,
  to_person_id TEXT NOT NULL,
  from_assignment_id TEXT NULL,
  to_assignment_id TEXT NULL,
  status TEXT NOT NULL CHECK (status IN (
    'OFFERED', 'ACCEPTED', 'DECLINED', 'REVOKED'
  )),
  offered_at TEXT NOT NULL,
  accepted_at TEXT NULL,
  note TEXT NULL,
  created_at TEXT NOT NULL,
  FOREIGN KEY (work_item_id) REFERENCES core_work_items(work_item_id)
);

CREATE INDEX IF NOT EXISTS idx_core_work_delegations_item
  ON core_work_delegations(work_item_id);
CREATE INDEX IF NOT EXISTS idx_core_work_delegations_to
  ON core_work_delegations(to_person_id, status);

-- Evidence file blobs linked to work items (object_ref points here).
CREATE TABLE IF NOT EXISTS core_work_evidence_files (
  file_id TEXT PRIMARY KEY,
  work_item_id TEXT NOT NULL,
  evidence_id TEXT NULL,
  filename TEXT NOT NULL,
  content_type TEXT NULL,
  byte_size INTEGER,
  storage_path TEXT NOT NULL,
  sha256 TEXT NULL,
  uploaded_by_person_id TEXT NOT NULL,
  created_at TEXT NOT NULL,
  FOREIGN KEY (work_item_id) REFERENCES core_work_items(work_item_id)
);

CREATE INDEX IF NOT EXISTS idx_core_work_evidence_files_item
  ON core_work_evidence_files(work_item_id);

-- Configurable venue closers list (person holds ROLE-BZG-CLOSER assignment).
-- No code change required to add more closers later.
CREATE TABLE IF NOT EXISTS venue_closer_roster (
  roster_id TEXT PRIMARY KEY,
  brand_id TEXT NOT NULL,
  position_id TEXT NOT NULL,
  person_id TEXT NULL,
  assignment_id TEXT NULL,
  status TEXT NOT NULL CHECK (status IN ('ACTIVE', 'VACANT', 'ENDED')),
  note TEXT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_venue_closer_roster_brand
  ON venue_closer_roster(brand_id, status);

-- Derived-view freshness stamps (canonical change → STALE until refresh).
CREATE TABLE IF NOT EXISTS core_derived_view_stamps (
  view_id TEXT PRIMARY KEY,
  source_fingerprint TEXT NOT NULL,
  refreshed_at TEXT NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('LIVE', 'STALE'))
);
