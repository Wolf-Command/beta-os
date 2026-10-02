-- BZG-DAILY-CLOSE-MULTI-EDC-VISION-1
-- Multi EDC receipts (0..N) with separate EDC card + QRIS; vision draft ≠ truth;
-- ESB closing receipt dual-source; no invented terminals / tolerances.

-- Per-close EDC receipt (repeating Add). Receipts entered = used today.
-- Configured terminals are options only — unused terminals do not create rows.
CREATE TABLE IF NOT EXISTS venue_close_edc_receipts (
  edc_receipt_id TEXT PRIMARY KEY,
  close_id TEXT NOT NULL,
  outlet_id TEXT NOT NULL,
  acquirer_label TEXT NOT NULL,
  terminal_config_id TEXT NULL,
  terminal_label TEXT NULL,
  settlement_batch_date TEXT NULL,
  edc_card_amount REAL NOT NULL DEFAULT 0,
  qris_amount REAL NOT NULL DEFAULT 0,
  receipt_total REAL NOT NULL DEFAULT 0,
  batch_ref TEXT NULL,
  image_object_ref TEXT NULL,
  content_hash TEXT NULL,
  evidence_id TEXT NULL,
  ocr_confidence REAL NULL,
  ocr_confidence_band TEXT NULL,
  extracted_json TEXT NULL,
  confirmed_json TEXT NULL,
  human_confirm_status TEXT NOT NULL DEFAULT 'DRAFT',
  confirmed_by_person_id TEXT NULL,
  confirmed_at TEXT NULL,
  duplicate_warn INTEGER NOT NULL DEFAULT 0,
  duplicate_warn_json TEXT NULL,
  created_by_person_id TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  FOREIGN KEY (close_id) REFERENCES venue_daily_closes(close_id),
  CHECK (human_confirm_status IN ('DRAFT', 'CONFIRMED', 'EDITED')),
  CHECK (edc_card_amount >= 0),
  CHECK (qris_amount >= 0)
);

CREATE INDEX IF NOT EXISTS idx_venue_close_edc_receipts_close
  ON venue_close_edc_receipts(close_id);

-- ESB closing receipt evidence (photo) — dual source with live ESB API.
-- Never silently overwrites API snapshot; mismatch is a visible exception flag.
CREATE TABLE IF NOT EXISTS venue_close_esb_closing_receipts (
  esb_receipt_id TEXT PRIMARY KEY,
  close_id TEXT NOT NULL,
  outlet_id TEXT NOT NULL,
  image_object_ref TEXT NULL,
  content_hash TEXT NULL,
  evidence_id TEXT NULL,
  extracted_json TEXT NULL,
  confirmed_json TEXT NULL,
  cash_amount REAL NULL,
  edc_card_amount REAL NULL,
  qris_amount REAL NULL,
  gross_amount REAL NULL,
  ocr_confidence REAL NULL,
  ocr_confidence_band TEXT NULL,
  human_confirm_status TEXT NOT NULL DEFAULT 'DRAFT',
  confirmed_by_person_id TEXT NULL,
  confirmed_at TEXT NULL,
  api_mismatch INTEGER NOT NULL DEFAULT 0,
  api_mismatch_json TEXT NULL,
  created_by_person_id TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  FOREIGN KEY (close_id) REFERENCES venue_daily_closes(close_id),
  CHECK (human_confirm_status IN ('DRAFT', 'CONFIRMED', 'EDITED'))
);

CREATE INDEX IF NOT EXISTS idx_venue_close_esb_closing_receipts_close
  ON venue_close_esb_closing_receipts(close_id);

-- Append-only vision/extract audit (AI draft preserved even after human edit).
CREATE TABLE IF NOT EXISTS venue_close_vision_events (
  vision_event_id TEXT PRIMARY KEY,
  close_id TEXT NOT NULL,
  target_kind TEXT NOT NULL,
  target_id TEXT NULL,
  provider TEXT NOT NULL,
  model TEXT NULL,
  confidence REAL NULL,
  confidence_band TEXT NULL,
  extracted_json TEXT NOT NULL,
  image_object_ref TEXT NULL,
  content_hash TEXT NULL,
  actor_person_id TEXT NULL,
  created_at TEXT NOT NULL,
  CHECK (target_kind IN ('EDC_RECEIPT', 'ESB_CLOSING_RECEIPT'))
);

CREATE INDEX IF NOT EXISTS idx_venue_close_vision_events_close
  ON venue_close_vision_events(close_id);
