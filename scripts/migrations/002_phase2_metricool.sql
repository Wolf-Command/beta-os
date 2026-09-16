-- Phase 2 Metricool READ + planning context (additive, idempotent)
-- Timezone: published_at_utc stored as UTC ISO; planning/display day = Asia/Makassar (WITA).
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS brand_external_ids (
  id INTEGER PRIMARY KEY,
  brand_key TEXT NOT NULL,
  external_system TEXT NOT NULL,
  external_id TEXT NOT NULL,
  label TEXT,
  status TEXT NOT NULL DEFAULT 'ACTIVE',
  created_at TEXT NOT NULL,
  updated_at TEXT,
  UNIQUE(brand_key, external_system, external_id)
);

CREATE TABLE IF NOT EXISTS performance_records (
  id INTEGER PRIMARY KEY,
  brand_key TEXT NOT NULL,
  external_system TEXT NOT NULL DEFAULT 'metricool',
  external_profile_id TEXT NOT NULL,
  network TEXT NOT NULL,
  surface TEXT NOT NULL,
  external_post_id TEXT NOT NULL,
  permalink TEXT,
  published_at_utc TEXT,
  content_type TEXT,
  caption TEXT,
  reach REAL,
  impressions REAL,
  views REAL,
  likes REAL,
  comments REAL,
  shares REAL,
  saves REAL,
  engagement REAL,
  engagement_rate_pct REAL,
  fetched_at TEXT NOT NULL,
  data_lane TEXT NOT NULL DEFAULT 'operational',
  dual_count_risk INTEGER NOT NULL DEFAULT 0,
  content_hash TEXT,
  raw_ref TEXT
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_perf_unique
  ON performance_records(external_profile_id, network, surface, external_post_id);
CREATE INDEX IF NOT EXISTS idx_perf_brand_lane
  ON performance_records(brand_key, data_lane, published_at_utc);
CREATE INDEX IF NOT EXISTS idx_perf_surface
  ON performance_records(brand_key, surface, data_lane);

CREATE TABLE IF NOT EXISTS planning_context_snapshots (
  id INTEGER PRIMARY KEY,
  brand_key TEXT NOT NULL,
  plan_id INTEGER,
  plan_revision_id INTEGER,
  created_at TEXT NOT NULL,
  created_by_subject TEXT,
  snapshot_json TEXT NOT NULL,
  content_hash TEXT,
  data_lane TEXT NOT NULL DEFAULT 'operational'
);
CREATE INDEX IF NOT EXISTS idx_pcs_plan ON planning_context_snapshots(plan_id);

CREATE TABLE IF NOT EXISTS planning_context_refs (
  id INTEGER PRIMARY KEY,
  snapshot_id INTEGER NOT NULL,
  ref_type TEXT NOT NULL,
  ref_id TEXT,
  version_or_hash TEXT,
  meta_json TEXT,
  FOREIGN KEY(snapshot_id) REFERENCES planning_context_snapshots(id)
);
CREATE INDEX IF NOT EXISTS idx_pcr_snap ON planning_context_refs(snapshot_id, ref_type);
