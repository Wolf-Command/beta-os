-- Uma Blu Daily Close + Exception Handover (Beta only)
-- ESB read-only reconciliation. No settlement API. Live variance thresholds = 0.
-- Client cannot submit totals / variance / state (enforced in application).

CREATE TABLE IF NOT EXISTS venue_daily_closes (
  close_id TEXT PRIMARY KEY,
  entity_id TEXT NOT NULL,
  venue_brand_id TEXT NOT NULL,
  business_date TEXT NOT NULL,
  state TEXT NOT NULL CHECK (
    state IN (
      'OPEN',
      'DATA_CAPTURED',
      'EVIDENCE_SUBMITTED',
      'RECONCILED',
      'VARIANCE_REQUIRES_POLICY',
      'EXCEPTION',
      'RESOLVED',
      'VERIFIED_CLOSED',
      'CANCELLED'
    )
  ),
  esb_fingerprint_sha256 TEXT NULL,
  esb_pulled_at TEXT NULL,
  esb_query_meta_json TEXT NULL,
  esb_totals_json TEXT NULL,
  declared_cash_amount REAL NULL,
  declared_cash_evidence_id TEXT NULL,
  variance_cash_amount REAL NULL,
  variance_policy_id TEXT NULL,
  work_item_id TEXT NULL,
  fingerprint_stale INTEGER NOT NULL DEFAULT 0 CHECK (fingerprint_stale IN (0, 1)),
  submitted_by_person_id TEXT NULL,
  resolved_at TEXT NULL,
  resolved_by_person_id TEXT NULL,
  resolve_evidence_id TEXT NULL,
  verified_at TEXT NULL,
  verified_by_person_id TEXT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  UNIQUE (entity_id, venue_brand_id, business_date)
);

CREATE INDEX IF NOT EXISTS idx_venue_daily_closes_state
  ON venue_daily_closes(state);

CREATE INDEX IF NOT EXISTS idx_venue_daily_closes_brand_date
  ON venue_daily_closes(venue_brand_id, business_date);

CREATE INDEX IF NOT EXISTS idx_venue_daily_closes_work_item
  ON venue_daily_closes(work_item_id);

-- Authorised variance policy rows. Live seed MUST remain 0 (no invented thresholds).
CREATE TABLE IF NOT EXISTS venue_close_variance_policies (
  variance_policy_id TEXT PRIMARY KEY,
  entity_id TEXT NOT NULL,
  venue_brand_id TEXT NULL,
  currency TEXT NOT NULL DEFAULT 'IDR',
  abs_threshold_amount REAL NOT NULL,
  comparison_rule TEXT NOT NULL DEFAULT 'LTE_INCLUSIVE'
    CHECK (comparison_rule IN ('LTE_INCLUSIVE', 'LT')),
  status TEXT NOT NULL CHECK (status IN ('ACTIVE', 'INACTIVE')),
  effective_from TEXT NOT NULL,
  effective_to TEXT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_venue_close_variance_policies_live
  ON venue_close_variance_policies(entity_id, venue_brand_id, status);
