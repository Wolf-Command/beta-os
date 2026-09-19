# CURSOR MISSION — Progress Owner SYSTEM% prove — 2026-09-19

**Class:** FIX / prove. Not a new system.  
**Decision:** owner correction `model_c_recon_after_devi_p0_stable` (2026-09-19) — read-only; no score gaming. Bound `beta-progress-dashboard-readonly-fix`.  
**Lane:** Beta `:8788` only. Production `:8787` not touched.

Owner SYSTEM is **25.5%**. That is the live ledger sum **19.65 / 77**, half-up to one decimal. It is not the older frozen **25.3** (19.45 / 77).

No hard-coded 25.3 was in the Owner HTML or the read model. Nothing was removed. The percentage is computed on each read. No maturity was raised. PROVEN stayed 12. READY stayed 3. Ledger bytes unchanged. Credits table unchanged.

## WHERE

| Surface | What it shows | Source |
| --- | --- | --- |
| `compute_system_from_ledger` | `system_pct` 25.5, `sum_credits_exact` 19.65, status OK, n 77 | `scripts/core/progress_read_model.py` reading `state/model-c-baseline-assessments.json` |
| `build_read_model().system` | same 25.5, integrity ok | same function, every read |
| `build_read_model().views.Empire.system` | same 25.5 | Empire is the Owner headline view |
| Owner `GET /api/progress` | `person_id` PERS-MATT, `system.system_pct` 25.5 | `scripts/serve_beta.py` `_progress_empire` after the Owner gate |
| Owner HTML | `SYSTEM — ${esc(systemPct)}%` | `dashboards/progress.html` sets `systemPct` from `system.system_pct` only when status is OK |

A stale projection blanks the percent and shows SCORING PROJECTION STALE. Score history is listed under SYSTEM detail. It is not the headline. The history tip is still the pre-INTEL snapshot (19.45). The headline does not use it.

## Prove

- `python3 scripts/tests/test_progress_system_pct_owner.py` → `PASS=45 FAIL=0`
- Authenticated Owner on an ephemeral port (same Beta handler, not Production, live auth not flipped): Matt 200 and 25.5; staff 403; anonymous 403
- `python3 scripts/tests/test_dashboard_truth.py` → `PASS=62 FAIL=0` (locks 19.65 → 25.5)
- Live `:8788` `/progress` is 200 and binds `system.system_pct`. Anonymous `/api/progress` is 403. `development_assertion` was not turned on for the live process
- `:8787` still listening
- WIP four digests unchanged

Signed-in browser click-through was not run. Cloudflare Access blocks an anonymous session, and live auth stays fail-closed.
