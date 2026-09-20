# GROK REVIEW — CAP-AMG-07 Service Improvement / Review-to-Improve Loop skeleton v1 — 2026-09-20

**Status:** PENDING commit hash. Fill after completion commit.

## Touched
  - `scripts/core/amg_service_improve.py` (new)
  - `scripts/tests/test_amg_service_improve.py` (new)
  - `dashboards/amg-service-improve.html` (new)
  - `scripts/serve_beta.py` (routes + Owner handlers)
  - `docs/deliveries/CURSOR-MISSION-AMG-SERVICE-IMPROVE-V1-2026-09-20.md` (new)
  - `state/build-claims/2026-09-20.json` claim row `bf-amg-service-improve-v1-20260920`

## Class
NEW CAPABILITY skeleton (`beta-amg-ops-safe`). Names review / finding / action / owner / due / notes slots; every slot empty. Empty framework ≠ live review-to-improve loop ≠ proof of service improvement machinery. No invent PROVEN / READY. No money move / payment / bank write. No guest blast / public post. No Yanolja live call/write. No Cloudflare/Access mutate.

Live `CAP-AMG-07` ledger stays **SPECIFIED** (not rewritten). Ceiling honesty label **BUILT** only. Ledger 77 rows.

## Prove (pre-commit)
- `python3 scripts/tests/test_amg_service_improve.py` → **PASS=286 FAIL=0**
- Ledger CAP-AMG-07 **SPECIFIED**; assessments len **77**
- CR-29c6ac36a9ca03f1 **OPEN**
- Live `:8788` anon `GET /api/amg/service-improve` → **403**; page `/amg-service-improve` → **403**
- `:8787` pid unchanged (`20807`); `:8788` restarted (`31282`)

## Refuse matrix (sample)
| Invent PROVEN / READY / raise CAP-AMG-07 | PASS — ledger CAP-AMG-07 SPECIFIED unchanged; ceiling BUILT label only |
| False-resolve CR-29c6ac36a9ca03f1 | PASS — CR stays OPEN |
| Guest blast / public post | PASS — refused |
| Money / Yanolja / Cloudflare / Access | PASS — refused |
| WIP four / Production :8787 | PASS — unchanged |

Do not false-resolve `CR-29c6ac36a9ca03f1`. Delivery evidence is the completion commit + this review. CAP-AMG-07 remains SPECIFIED.
