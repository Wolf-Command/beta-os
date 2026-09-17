# AUDIT / EVIDENCE SPINE — honesty table (Beta transitional)

**Canon status:** transitional (Beta OS / `build/wolf-command-rebuild` only)  
**Sibling style:** match Real Auth transitional honesty docs  
**Updated:** 2026-09-17 WITA (mission authored; implementation pending Cursor)

> Do not claim BUILT or TESTED until Cursor lands the slice and tests pass on Mac Beta.

| Capability | Status | Notes |
|------------|--------|-------|
| Append-only `core_audit_events` table | NOT BUILT | Mission specifies structured columns + closed `result` set |
| Service `scripts/core/audit.py` INSERT-only | NOT BUILT | `record_event` / `get_event` / `list_events` / `correct_event` |
| Service refuses UPDATE/DELETE | NOT BUILT | Raise or omit; correction = new INSERT |
| Optional SQLite triggers deny UPDATE/DELETE | NOT BUILT | Defense-in-depth; preferred |
| Cryptographic hash-chain / court-grade immutability | NOT BUILT | **Out of scope** this slice unless explicitly added+tested |
| Simple row / before-after hash fields | NOT BUILT | Optional tamper-*evidence* only — no court claim |
| Secret stripping at write | NOT BUILT | Never store jwt/password/cookie/api_key |
| PERSON actor from verified identity only | NOT BUILT | Never from client subject headers |
| SYSTEM cannot carry `actor_person_id` | NOT BUILT | |
| Permission `audit.event.read` (Matt / Owner only) | NOT BUILT | No audit admin UI |
| `GET /api/core/audit` RBAC-gated | NOT BUILT | |
| Integration: verified auth success | NOT BUILT | PERSON + cloudflare_access_verified |
| Integration: protected auth failure | NOT BUILT | DENIED; no JWT body |
| Integration: RBAC denial (one path) | NOT BUILT | |
| Integration: Authority denial (amount + no limit) | NOT BUILT | |
| Integration: one Content Machine mutation | NOT BUILT | After successful commit |
| Automated tests `tests/test_core_audit.py` | NOT BUILT | |
| Event bus / Decision Ledger / SIEM / AI scoring | NOT BUILT | Explicit non-goals |
| Production / `:8787` / wolf-system | NOT BUILT | Forbidden this lane |

## Honesty rules

- **BUILT** = code exists on Beta branch and is reachable on `:8788` path.
- **TESTED** = automated tests green on Mac Beta for that capability.
- **NOT BUILT** = absent or only specified in mission.
- Never upgrade a row to BUILT/TESTED from a plan document alone.
