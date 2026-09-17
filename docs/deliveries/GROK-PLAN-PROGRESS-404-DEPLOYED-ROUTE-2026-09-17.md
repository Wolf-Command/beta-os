# GROK PLAN — Progress 404 / Deployed-Route Acceptance — 2026-09-17

**Factory run:** `BF-progress-404-deployed-route-20260917`  
**Repo:** `/Users/wolfterminal/beta-os` · branch `build/wolf-command-rebuild`  
**Scope:** Beta `:8788` only. Production `:8787` / `~/.openclaw/workspace/wolf-system` untouched.

## Root cause (confirmed)

Route `/progress` + APIs landed in `cef569a` on `scripts/serve_beta.py`, but the live Beta process had been running since ~09:47 WITA without reload. Ephemeral `ThreadingHTTPServer` unit tests (port 0) always got a fresh Handler → 92/92 green while live `:8788` still 404'd clean `/progress`. Static `/progress.html` worked from disk; clean path needed process reload. Peaches already restarted Beta via LaunchAgent; `/progress` now 200.

## Remaining gaps

1. Clean aliases missing for `/uma-blu-close` and `/habitat-operator` (`.html` works; clean paths 404).
2. No **deployed-route** prove against real `127.0.0.1:8788` — factory can miss stale process again.
3. RULE / Build-Factory gate must require deployed-route verification after `serve_beta.py` changes.

## Plan (ordered)

1. Write this plan + Cursor mission.
2. Patch `serve_beta.py`: add clean aliases for Uma + Habitat (same pattern as `/progress`).
3. Add `scripts/prove_deployed_ui_routes.py` (hits real `:8788`, fail loud).
4. Add `scripts/beta_restart.py` — LaunchAgent kickstart only; refuse `:8787`.
5. New RULE `docs/RULE-UI-Finished-Deployed-Route-2026-09-17.md` + backlog note + patch Build-Factory RULE.
6. Add `scripts/tests/test_deployed_ui_routes.py` (auto-prove when `:8788` serve_beta detectable).
7. Restart Beta via LaunchAgent → run prove → unit tests → commit → review → factory DONE.

## Auth constraints (locked)

- Live `auth_mode=cloudflare_access` fail-closed. Unauthenticated `/api/progress` → `missing_auth` JSON (not 404). Do **not** change `BETA_AUTH_MODE`.
- Owner-only progress auth stays. Matt JWT not forgeable here — browser retest = human gate.

## Restart law

```bash
launchctl kickstart -k gui/$(id -u)/net.wolfcommand.serve-beta
```

KeepAlive true. Never orphan `nohup`. Never touch `:8787`.

## Done when

- Prove script PASS on real `:8788`
- `/progress`, `/uma-blu-close`, `/habitat-operator` → 200
- `/api/progress` unauthenticated → not 404 (expect missing_auth / 401/403)
- Commit on branch; Production untouched; factory `--final-state DONE`
