-- Habitat Publish Gate on Wolf Core (Beta only)
-- Vertical-first. Core Approval = canonical. Legacy Human_Approved derived only.
-- ONE governance policy + ONE evidence requirement for habitat.content.publish.
-- No SoD / Exception / monetary Authority seed.
-- content_planner columns + content_versions added idempotently by migrate script
-- (SQLite ALTER TABLE ADD COLUMN).

CREATE TABLE IF NOT EXISTS content_versions (
  slot_id INTEGER NOT NULL,
  version_hash TEXT NOT NULL,
  brand TEXT NULL,
  platform TEXT NULL,
  title_slug TEXT NULL,
  script_body TEXT NULL,
  raw_asset_id INTEGER NULL,
  payload_json TEXT NULL,
  created_by_person_id TEXT NULL,
  created_at TEXT NOT NULL,
  PRIMARY KEY (slot_id, version_hash)
);

CREATE INDEX IF NOT EXISTS idx_content_versions_slot
  ON content_versions(slot_id, created_at);
