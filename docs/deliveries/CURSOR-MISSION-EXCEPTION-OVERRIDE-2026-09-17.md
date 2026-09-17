# CURSOR MISSION — Exception / Override Governance

**Workspace:** `/Users/wolfterminal/beta-os`
**Branch:** `build/wolf-command-rebuild`
**Commit message:** `feat(core): add governed exception control`
**Production:** DO NOT TOUCH. Live exceptions/policies/SoD/evidence-reqs/authority = 0.

You are Cursor Local. Peaches does not write application code.

## Read

- docs/deliveries/GROK-PLAN-EXCEPTION-OVERRIDE-2026-09-17.md
- docs/canon/EXCEPTION-OVERRIDE.md
- evidence.py, sod.py, approvals.py, audit.py, identity patterns (PERS_MATT = "PERS-MATT")

## Implement

### Migration `019_exception_override.sql` + migrate_exception_override.py
- Backup catalog/backups/pre-exception-override-<ts>.sqlite + SHA-256
- Tables per plan; permissions governance.exception.*; Matt-only authorize/revoke grants
- NO live exception seed
- Idempotent

### scripts/core/exceptions.py
- request / authorise / reject / revoke / evaluate / consume
- Matt gate via verified Person id == PERS-MATT
- Delegation ignored for authorise
- Client override flags ignored
- Reason validation; evidence_id optional but if required_for_authorise then canonical ACTIVE evidence
- Atomic consume
- Audit all lifecycle via audit.record_event (refs only)

### Wire (minimal)
- evidence._enforce / approvals evidence gate: if DENY, check exception for EVIDENCE_REQUIREMENT; if ok → ALLOWED_UNDER_EXCEPTION + consume; preserve normal DENY codes in response
- sod / approvals _decide: similar for SOD_CONSTRAINT only when exception bound to that constraint
- Never rewrite normal PASS
- Authentication / Entity isolation / NON_EXCEPTIONABLE never bypassable

### Tests scripts/tests/test_exception_override.py
Matt mandatory list. Re-run APR, DLG, Dual, Policy, SoD, Evidence — all green.

### Docs + Commit
Canon honesty. Commit exact message. Print BACKUP+SHA. EXIT:0 / EXIT:1.
