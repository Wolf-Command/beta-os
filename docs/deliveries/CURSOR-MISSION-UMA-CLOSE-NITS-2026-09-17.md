# CURSOR MISSION — UMA BLU DAILY CLOSE NITS (OVERNIGHT P2)

**Repo:** `/Users/wolfterminal/beta-os` (Beta only)
**CAP:** CAP-BZG-03
**Follow:** `docs/deliveries/GROK-TRIAGE-UMA-CLOSE-NITS-2026-09-17.md`

## Do
1. `esb_close_snapshot.py` (or equivalent): fail-closed — blank/missing `branchCode` NOT included in BLZ/Uma totals.
2. Canon honesty: update `docs/canon/UMA-BLU-DAILY-CLOSE.md` (and any plan text if present) so HFB is exception resolve/verify — **not** submit. Do NOT widen HFB grants.
3. Clean close path: assign `RECONCILED` then `VERIFIED_CLOSED` (or equivalent honest two-step) so RECONCILED is not dead.
4. `verify_close`: independently deny when `submitter == verified` (`sod_self_close` real).
5. Add `_venue_close_refuse_overrides` to exception/resolve/verify POST handlers missing it.
6. Fix tautology in `scripts/tests/test_uma_blu_daily_close.py` line ~422.

## Do NOT
- Invent cash variance thresholds
- Invent/assign a closer person
- Touch Habitat / Metricool writes / ESB writes / Production
- Broad refactors unrelated to the six nits

## Verify
```bash
python3 scripts/tests/test_uma_blu_daily_close.py
```
Print CURSOR_DONE, git log -1 --oneline, test PASS/FAIL counts.

Commit with message referencing CAP-BZG-03 overnight nits.
