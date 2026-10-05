-- BZG-CLOSE-EDC-BANK-CARDS-1
-- One CURRENT evidence state per bank/day; SUPERSEDED kept for audit; bank cards UX.

ALTER TABLE venue_close_edc_receipts ADD COLUMN evidence_role TEXT NOT NULL DEFAULT 'CURRENT';
ALTER TABLE venue_close_edc_receipts ADD COLUMN superseded_by TEXT NULL;
ALTER TABLE venue_close_edc_receipts ADD COLUMN superseded_at TEXT NULL;
ALTER TABLE venue_close_edc_receipts ADD COLUMN supersede_reason TEXT NULL;
ALTER TABLE venue_close_edc_receipts ADD COLUMN counted_in_totals INTEGER NOT NULL DEFAULT 1;

CREATE INDEX IF NOT EXISTS idx_venue_close_edc_receipts_close_bank_role
  ON venue_close_edc_receipts(close_id, acquirer_label, evidence_role);

-- Outlet configured banks (staff cards). Extensible per outlet — not hardcoded UI.
CREATE TABLE IF NOT EXISTS venue_close_outlet_banks (
  bank_config_id TEXT PRIMARY KEY,
  outlet_id TEXT NOT NULL,
  bank_label TEXT NOT NULL,
  sort_order INTEGER NOT NULL DEFAULT 100,
  status TEXT NOT NULL DEFAULT 'ACTIVE',
  note TEXT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  UNIQUE (outlet_id, bank_label)
);

CREATE INDEX IF NOT EXISTS idx_venue_close_outlet_banks_outlet
  ON venue_close_outlet_banks(outlet_id);
