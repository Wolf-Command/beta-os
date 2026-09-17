# GROK REVIEW — Progress 404 Deployed-Route — 8e5ee6a — 2026-09-17

## Verdict: PASS (pending human Matt browser retest for JWT UI)

### Diff summary
- `scripts/serve_beta.py`: clean aliases `/uma-blu-close`, `/habitat-operator` (+ ensure `/progress`)
- `scripts/prove_deployed_ui_routes.py`: real :8788 prove
- `scripts/beta_restart.py`: LaunchAgent-only restart; refuse :8787
- RULE + Build-Factory MUST gate + backlog + tests

### Prove output
```
prove_deployed_ui_routes BASE=http://127.0.0.1:8788
PASS :8788 listening
WARN: serve_beta string not in lsof; python listener present:
command   pid         user   fd   type             device size/off node name
python  30238 wolfterminal    3u  ipv4 0xecf053d2fabc890d      0t0  tcp 127.0.0.1:8788 (listen)
PASS GET /progress — status=200 bytes=15148 markers=['Progress', 'progress', 'id=']
PASS GET /progress.html — status=200 bytes=15148
PASS GET /api/progress (no auth) — status=403 body_snip='{"ok": false, "error": "missing_auth", "message": "Cf-Access-Jwt-Assertion required. Local :8788 without Cloudflare JWT '
PASS GET /uma-blu-close — status=200 bytes=14201
PASS GET /habitat-operator — status=200 bytes=24900
PASS all deployed-route checks
```

### Tests
```
/opt/homebrew/opt/python@3.14/bin/python3.14: No module named pytest
test_prove_deployed_ui_routes_when_beta_up (scripts.tests.test_deployed_ui_routes.TestDeployedUiRoutes.test_prove_deployed_ui_routes_when_beta_up) ... ok

----------------------------------------------------------------------
Ran 1 test in 0.156s

OK
prove_deployed_ui_routes BASE=http://127.0.0.1:8788
PASS :8788 listening
WARN: serve_beta string not in lsof; python listener present:
command   pid         user   fd   type             device size/off node name
python  30238 wolfterminal    3u  ipv4 0xecf053d2fabc890d      0t0  tcp 127.0.0.1:8788 (listen)
PASS GET /progress — status=200 bytes=15148 markers=['Progress', 'progress', 'id=']
PASS GET /progress.html — status=200 bytes=15148
PASS GET /api/progress (no auth) — status=403 body_snip='{"ok": false, "error": "missing_auth", "message": "Cf-Access-Jwt-Assertion required. Local :8788 without Cloudflare JWT '
PASS GET /uma-blu-close — status=200 bytes=14201
PASS GET /habitat-operator — status=200 bytes=24900
PASS all deployed-route checks
```

### Auth
Live auth_mode untouched (cloudflare_access fail-closed). `/api/progress` not 404.

### Production
:8787 untouched. wolf-system untouched.

### Human gate
Matt browser retest of https://beta.wolfcommand.net/progress (JWT) remains human.
