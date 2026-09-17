-- Wolf Core Dual Approval (Beta only)
-- Extends Approval Engine. No PARTIALLY_APPROVED status.
-- Live Authority Limits remain 0. No dual business policy seed.
-- required_decision_count column added idempotently by migrate_dual_approval.py
-- (SQLite ALTER TABLE ADD COLUMN).

-- One Person may contribute at most one APPROVED decision per request.
CREATE UNIQUE INDEX IF NOT EXISTS idx_core_approval_dec_one_approve_per_person
  ON core_approval_decisions(approval_request_id, decided_by_person_id)
  WHERE decision = 'APPROVED';
