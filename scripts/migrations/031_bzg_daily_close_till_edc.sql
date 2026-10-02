-- BZG-DAILY-CLOSE-TILL-EDC-1 — outlet close config + till/EDC evidence (Beta)
-- Extends venue_daily_closes (021). No invented terminals. No ACTIVE variance policies.
-- settlement_api remains UNAVAILABLE. Till float only where Owner-cited.

CREATE TABLE IF NOT EXISTS venue_close_outlet_config (
  outlet_id TEXT PRIMARY KEY,
  entity_id TEXT NOT NULL,
  venue_brand_id TEXT NOT NULL,
  owner_title TEXT NOT NULL,
  registry_display_name TEXT,
  human_close_enabled INTEGER NOT NULL DEFAULT 0 CHECK (human_close_enabled IN (0, 1)),
  till_float_idr REAL NULL,
  till_float_citation TEXT NULL,
  title_map_status TEXT NOT NULL DEFAULT 'NEEDS CONFIGURATION',
  edc_terminal_config_status TEXT NOT NULL DEFAULT 'NEEDS CONFIGURATION',
  note TEXT NOT NULL DEFAULT '',
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_venue_close_outlet_config_enabled
  ON venue_close_outlet_config(human_close_enabled);

-- Physical EDC terminal registry per outlet. Empty = NEEDS CONFIGURATION (do not invent).
CREATE TABLE IF NOT EXISTS venue_close_edc_terminals (
  terminal_config_id TEXT PRIMARY KEY,
  outlet_id TEXT NOT NULL,
  terminal_label TEXT NOT NULL,
  acquirer_label TEXT NULL,
  status TEXT NOT NULL DEFAULT 'NEEDS CONFIGURATION',
  note TEXT NOT NULL DEFAULT '',
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_venue_close_edc_terminals_outlet
  ON venue_close_edc_terminals(outlet_id);

-- Per-close EDC settlement slip lines (evidence-bound). Not ESB card payments.
CREATE TABLE IF NOT EXISTS venue_close_edc_lines (
  edc_line_id TEXT PRIMARY KEY,
  close_id TEXT NOT NULL,
  outlet_id TEXT NOT NULL,
  terminal_config_id TEXT NULL,
  acquirer_label TEXT NOT NULL,
  batch_total REAL NOT NULL,
  txn_count INTEGER NULL,
  evidence_id TEXT NOT NULL,
  created_by_person_id TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  FOREIGN KEY (close_id) REFERENCES venue_daily_closes(close_id)
);

CREATE INDEX IF NOT EXISTS idx_venue_close_edc_lines_close
  ON venue_close_edc_lines(close_id);

-- Till / POS Z-report evidence binding (declared tender ≠ verified).
CREATE TABLE IF NOT EXISTS venue_close_till_evidence (
  till_row_id TEXT PRIMARY KEY,
  close_id TEXT NOT NULL,
  outlet_id TEXT NOT NULL,
  evidence_id TEXT NOT NULL,
  declared_cash_amount REAL NOT NULL,
  declared_card_amount REAL NULL,
  declared_qris_amount REAL NULL,
  declared_gross_amount REAL NULL,
  z_report_object_ref TEXT NULL,
  created_by_person_id TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  FOREIGN KEY (close_id) REFERENCES venue_daily_closes(close_id)
);

CREATE INDEX IF NOT EXISTS idx_venue_close_till_evidence_close
  ON venue_close_till_evidence(close_id);
