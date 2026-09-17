# RULE — Deployed-Route Verify — 2026-09-17

**Status:** LOCKED (factory MUST for UI FINISHED)  
**Trigger:** Any Beta UI route / `scripts/serve_beta.py` change claimed FINISHED to Matt/staff.

## Law

**REPOSITORY TEST ≠ DEPLOYED ROUTE TEST**

1. Repository unit tests and ephemeral `ThreadingHTTPServer` (port 0) are **not enough** to mark a UI route FINISHED.
2. Before any UI route is reported FINISHED, the factory must verify the **actual Beta HTTP endpoint** through the real serving stack (`serve_beta.py` on `:8788`), not only Flask/unit/ephemeral test clients.
3. After any change to `scripts/serve_beta.py`:
   - Restart Beta via LaunchAgent only (`python3 scripts/beta_restart.py` or  
     `launchctl kickstart -k gui/$(id -u)/net.wolfcommand.serve-beta`).  
     Never orphan `nohup`. Never touch Production `:8787`.
   - Run `python3 scripts/prove_deployed_routes.py` (and/or `prove_deployed_ui_routes.py`) and require **PASS**.
4. Wire this RULE into factory **PEACHES_VERIFY** for UI slices going forward.

## Minimum Progress-class checks

1. Clean path GET is **not 404** (e.g. `/progress`, `/habitat-operator`, `/uma-blu-close`).
2. Response body is the expected dashboard HTML (marker string in title/body).
3. Unauthenticated / wrong-seat behaviour documented where the page already enforces it — do **not** invent new auth in a route-alias slice. Live `BETA_AUTH_MODE` stays fail-closed.

## Why

2026-09-17: `/progress` was committed (`cef569a`) and ephemeral tests passed while live Beta still returned 404 — process had been up without reload. Static `.html` worked; clean path needed reload + prove against origin.

## Related

- `scripts/prove_deployed_routes.py`
- `scripts/prove_deployed_ui_routes.py`
- `scripts/beta_restart.py`
- `scripts/tests/test_deployed_route_aliases.py`
- `docs/RULE-UI-Finished-Deployed-Route-2026-09-17.md`
- `docs/RULE-Build-Factory-Self-Driving-2026-09-17.md` (PEACHES_VERIFY MUST gate)
