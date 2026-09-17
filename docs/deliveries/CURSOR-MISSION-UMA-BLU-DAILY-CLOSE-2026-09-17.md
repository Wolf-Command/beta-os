# CURSOR MISSION — Uma Blu Daily Close + Exception Handover

Implement exactly: `docs/deliveries/GROK-PLAN-UMA-BLU-DAILY-CLOSE-2026-09-17.md`

## Hard rules
- Workspace: `/Users/wolfterminal/beta-os` branch `build/wolf-command-rebuild`
- Beta only. No Production. No ESB writes. No Habitat mutations (content_planner untouched).
- No invented variance thresholds. Live threshold count must stay 0.
- No hard-coded `if Devi`. Role/assignment/scope only.
- Client cannot override totals/variance/state.
- Peaches does not write app code — you do.
- Commit when green with message referencing this mission.

## Deliverables
1. Migration + `venue_daily_closes` (+ any needed indexes)
2. Seed PERS-DEVI + AUTH email `deviputu236@gmail.com` + ROLE-BZG-HFB position/assignment + SCOPE-BZG-UMA (from HR-authorised email — do not invent another)
3. `scripts/core/venue_close.py` + `esb_close_snapshot.py`
4. Beta API + `dashboards/uma-blu-close.html` (mobile-first, human language)
5. `scripts/tests/test_uma_blu_daily_close.py` covering Matt mandatory list
6. `docs/canon/UMA-BLU-DAILY-CLOSE.md`
7. Run tests; leave working tree clean after commit

## Success
All new tests PASS · Core regressions PASS · honesty flags correct · Habitat slots unchanged
