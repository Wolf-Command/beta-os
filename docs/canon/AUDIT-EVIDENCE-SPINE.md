# AUDIT / EVIDENCE SPINE — honesty table (Beta transitional)

**Canon status:** transitional (Beta OS / `build/wolf-command-rebuild` only)  
**Sibling style:** match Real Auth transitional honesty docs  
**Updated:** 2026-09-17 WITA (Cursor implementation landed; tests green on Mac Beta)

> CLAIMED ≠ VERIFIED for production. This slice is Beta `:8788` only. No hash-chain / court-grade immutability.

| Capability | Status | Notes |
|------------|--------|-------|
| Append-only `core_audit_events` table | BUILT+TESTED | Migration `011_audit_evidence_spine`; structured columns + closed `result` set |
| Service `scripts/core/audit.py` INSERT-only | BUILT+TESTED | `record_event` / `get_event` / `list_events` / `correct_event` |
| Service refuses UPDATE/DELETE | BUILT+TESTED | `NotImplementedError`; correction = new INSERT |
| Optional SQLite triggers deny UPDATE/DELETE | BUILT+TESTED | `trg_core_audit_events_no_update` / `_no_delete` |
| Cryptographic hash-chain / court-grade immutability | NOT BUILT | **Out of scope** this slice |
| Simple row / before-after hash fields | BUILT | Optional columns `before_hash` / `after_hash` — tamper-*evidence* only; no court claim |
| Secret stripping at write | BUILT+TESTED | Never store jwt/password/cookie/api_key/authorization/token |
| PERSON actor from verified identity only | BUILT+TESTED | Requires `verified_person_id` from identity path |
| SYSTEM cannot carry `actor_person_id` | BUILT+TESTED | |
| Permission `audit.event.read` (Matt / Owner only) | BUILT+TESTED | `ROLE-MATT` only; no audit admin UI |
| `GET /api/core/audit` RBAC-gated | BUILT+TESTED | Paginated; `hash_chain: NOT_BUILT` in payload |
| Integration: verified auth success | BUILT+TESTED | PERSON + assurance from request_auth |
| Integration: protected auth failure | BUILT+TESTED | SYSTEM DENIED; no JWT body |
| Integration: RBAC denial (one path) | BUILT+TESTED | `_require_permission` deny → `source=rbac` |
| Integration: Authority denial (amount + no limit) | BUILT+TESTED | `/api/core/authority/check` deny → `source=authority` |
| Integration: one Content Machine mutation | BUILT+TESTED | `POST /api/planner/save` after commit → `source=content_planner` |
| Automated tests `scripts/tests/test_core_audit.py` | BUILT+TESTED | 40/40 pass (2026-09-17) |
| Event bus / Decision Ledger / SIEM / AI scoring | NOT BUILT | Explicit non-goals |
| Production / `:8787` / wolf-system | NOT BUILT | Forbidden this lane |

## Honesty rules

- **BUILT** = code exists on Beta branch and is reachable on `:8788` path.
- **TESTED** = automated tests green on Mac Beta for that capability.
- **NOT BUILT** = absent or only specified in mission.
- Never upgrade a row to BUILT/TESTED from a plan document alone.
- Append-only + triggers ≠ cryptographic immutability.
