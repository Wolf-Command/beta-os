# CURSOR MISSION — Evidence Requirement Enforcement

**Workspace:** `/Users/wolfterminal/beta-os`
**Branch:** `build/wolf-command-rebuild`
**Commit:** `feat(core): enforce deterministic evidence requirements`
**Production:** DO NOT TOUCH. Live Authority/Policies/SoD/Evidence-requirements = 0.

You are Cursor Local Agent. Peaches does not write application code.

## Read first

- `docs/deliveries/GROK-PLAN-EVIDENCE-REQUIREMENTS-2026-09-17.md`
- `docs/canon/EVIDENCE-REQUIREMENTS.md`
- `docs/canon/AUDIT-EVIDENCE-SPINE.md`
- `scripts/migrations/011_audit_evidence_spine.sql`, `scripts/core/audit.py`
- `governance_policy.py`, `approvals.py`, `sod.py`
- Prior test suites patterns

## Implement

### Migration `018_evidence_requirements.sql` + migrate script

- Backup `catalog/backups/pre-evidence-requirements-<ts>.sqlite` + SHA-256
- Tables per Grok plan; idempotent; NO live requirement/evidence seed
- Append-only / no hard-delete for evidence used historically (invalidate path)
- Permission codes as planned — no broad live grants

### `scripts/core/evidence.py`

- submit_evidence, invalidate_evidence, verify_evidence (Person from verified id only; ignore forged)
- evaluate_evidence_requirements fail-closed
- metadata size cap + secret stripping (reuse audit patterns)
- object_ref = string only; optional content_hash; no SQLite blobs
- Audit lifecycle via existing audit.record_event

### Wire

- approvals create/decide: when enforce_evidence=True OR (bind_policy and policy.evidence_required): evaluate; deny missing
- Client cannot override evidence_required / evidence_present
- Keep default unbound paths green for existing tests

### Tests `scripts/tests/test_evidence_requirements.py`

Matt mandatory list. Re-run APR, DLG, Dual, Policy Binding, SoD — all green. Live counts stay 0.

### Docs + Commit

Update AUDIT-EVIDENCE-SPINE honesty row pointing to this extension. Commit exact message. Print backup+SHA. `EXIT:0` / `EXIT:1`.
