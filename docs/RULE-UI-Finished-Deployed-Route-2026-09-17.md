# RULE — UI FINISHED requires deployed-route verification — 2026-09-17

**Status:** LOCKED (factory MUST)  
**Trigger:** Any Beta UI route / `scripts/serve_beta.py` change that claims FINISHED.

## Law

1. **Repository unit tests and ephemeral `ThreadingHTTPServer` (port 0) are not enough** to mark a UI route FINISHED.
2. **UI FINISHED** requires verification against the **real Beta serving stack** on `http://127.0.0.1:8788` (LaunchAgent `net.wolfcommand.serve-beta`).
3. After any change to `scripts/serve_beta.py`:
   - Restart Beta via LaunchAgent only:  
     `launchctl kickstart -k gui/$(id -u)/net.wolfcommand.serve-beta`  
     (or `python3 scripts/beta_restart.py`).  
     Never orphan `nohup`. Never touch Production `:8787`.
   - Run `python3 scripts/prove_deployed_ui_routes.py` and require **PASS**.
4. Clean URL aliases (e.g. `/progress` → `/progress.html`) must be proven on the live process, not only on a fresh Handler in tests.
5. Auth fail-closed behavior (e.g. `/api/progress` → `missing_auth` / 401/403, **not** 404) is part of deployed-route acceptance. Do not flip `BETA_AUTH_MODE` to make proves green.

## Why

2026-09-17: `/progress` was committed (`cef569a`) and 92/92 ephemeral tests passed while live Beta still returned 404 — process had been up since ~09:47 WITA without reload. Static `.html` worked; clean path needed reload + prove against origin.

## Related

- `scripts/prove_deployed_ui_routes.py`
- `scripts/beta_restart.py`
- `scripts/tests/test_deployed_ui_routes.py`
- `docs/RULE-Build-Factory-Self-Driving-2026-09-17.md` (MUST gate)
