# MAC-APPLY — Trading+Fitness RO deepen (box-prepared; Mac was RED)

When Link signals GREEN (`machineId 36d8fa4b…` connected + Shell PROVE_OK):

1. Copy `owner_trading_ro.py`, `owner_fitness_ro.py` into `~/beta-os/` (serve lib path).
2. Wire routes `/api/owner/trading-ro` and `/api/owner/fitness-ro` on **beta sidecar only** (not :8787).
3. Graft `board-render-snippets.js` into `dashboards/owner-trading-1.html` + `owner-fitness-1.html` (or inline script calling the loaders into a `#ro-live` node). Replace pure placeholder text with RO render / "no SoT yet".
4. Run `python3 test_owner_ro_loaders.py` on Mac; optionally hit APIs against real V1 paths.
5. Beta kickstart (sidecar only). Update `CONNECTOR-GAP-20260930.json` trading/fitness status → `RO_LOADER_BOX_READY` then `RO_LIVE` once verified.
6. Evidence: holdings_count / journal_rows / table_counts from real files — fail closed if missing.
7. **Forbidden:** live broker, Spartacus DB writes, invent holdings, prod :8787, Exit Report, staff_ready=true, REBUILT+PROVEN.

Prepared: 2026-09-30 ~11:41 WITA on box while Mac pipe RED / SPAWN_REFUSED.
