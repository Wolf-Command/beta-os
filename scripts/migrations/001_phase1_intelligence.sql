-- Phase 1 Content Intelligence schema (additive, idempotent)
-- RULE (app-enforced): memory_items.status may be ACTIVE only when approval_state=APPROVED

PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS brands (
  id TEXT PRIMARY KEY,
  display_name TEXT NOT NULL,
  aliases_json TEXT,
  cadence_json TEXT,
  status TEXT NOT NULL DEFAULT 'ACTIVE',
  created_at TEXT NOT NULL,
  updated_at TEXT
);

CREATE TABLE IF NOT EXISTS permissions (
  id INTEGER PRIMARY KEY,
  subject TEXT NOT NULL,
  permission TEXT NOT NULL,
  brand_id TEXT,
  granted_at TEXT NOT NULL,
  granted_by TEXT
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_permissions_unique
  ON permissions(subject, permission, ifnull(brand_id, ''));

CREATE TABLE IF NOT EXISTS memory_items (
  id INTEGER PRIMARY KEY,
  brand_id TEXT,
  type TEXT NOT NULL,
  scope TEXT,
  text TEXT NOT NULL,
  source_type TEXT,
  source_id TEXT,
  evidence_refs TEXT,
  confidence REAL,
  status TEXT NOT NULL,
  approval_state TEXT NOT NULL,
  approved_by TEXT,
  created_at TEXT NOT NULL,
  expires_at TEXT,
  supersedes INTEGER,
  version INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS evidence_items (
  id INTEGER PRIMARY KEY,
  kind TEXT,
  ref TEXT,
  content TEXT,
  content_hash TEXT,
  brand_id TEXT,
  linked_memory_id INTEGER,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS content_plans (
  id INTEGER PRIMARY KEY,
  brand_id TEXT NOT NULL,
  title TEXT,
  period_start TEXT,
  period_end TEXT,
  status TEXT NOT NULL,
  strategy_json TEXT,
  checklist_json TEXT,
  created_by TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT
);

CREATE TABLE IF NOT EXISTS plan_revisions (
  id INTEGER PRIMARY KEY,
  plan_id INTEGER NOT NULL,
  role TEXT NOT NULL,
  full_json TEXT NOT NULL,
  diff_json TEXT,
  actor TEXT,
  created_at TEXT NOT NULL,
  FOREIGN KEY(plan_id) REFERENCES content_plans(id)
);

CREATE TABLE IF NOT EXISTS content_cards (
  id INTEGER PRIMARY KEY,
  plan_id INTEGER NOT NULL,
  card_type TEXT NOT NULL,
  sequence INTEGER,
  title TEXT,
  body_json TEXT,
  asset_status TEXT,
  status TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT,
  FOREIGN KEY(plan_id) REFERENCES content_plans(id)
);

CREATE TABLE IF NOT EXISTS card_revisions (
  id INTEGER PRIMARY KEY,
  card_id INTEGER NOT NULL,
  role TEXT NOT NULL,
  full_json TEXT NOT NULL,
  diff_json TEXT,
  actor TEXT,
  created_at TEXT NOT NULL,
  FOREIGN KEY(card_id) REFERENCES content_cards(id)
);

CREATE TABLE IF NOT EXISTS skill_runs (
  id INTEGER PRIMARY KEY,
  skill_name TEXT NOT NULL,
  brand_id TEXT,
  plan_id INTEGER,
  input_json TEXT,
  result_json TEXT,
  evidence_json TEXT,
  confidence REAL,
  assumptions_json TEXT,
  missing_information_json TEXT,
  status TEXT,
  created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_memory_brand ON memory_items(brand_id);
CREATE INDEX IF NOT EXISTS idx_memory_status ON memory_items(status, approval_state);
CREATE INDEX IF NOT EXISTS idx_permissions_subject ON permissions(subject, permission);
CREATE INDEX IF NOT EXISTS idx_plans_brand ON content_plans(brand_id, status);
CREATE INDEX IF NOT EXISTS idx_cards_plan ON content_cards(plan_id, card_type);
CREATE INDEX IF NOT EXISTS idx_plan_revisions_plan ON plan_revisions(plan_id);
CREATE INDEX IF NOT EXISTS idx_card_revisions_card ON card_revisions(card_id);
CREATE INDEX IF NOT EXISTS idx_skill_runs_plan ON skill_runs(plan_id, skill_name);
