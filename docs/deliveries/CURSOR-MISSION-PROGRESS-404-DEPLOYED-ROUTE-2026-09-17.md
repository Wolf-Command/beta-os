# CURSOR MISSION — Progress 404 Deployed-Route — 2026-09-17

**Run:** `BF-progress-404-deployed-route-20260917`  
**Workspace:** `/Users/wolfterminal/beta-os` · `build/wolf-command-rebuild`  
**Beta only.** NEVER touch Production `:8787` or `~/.openclaw/workspace/wolf-system`.

## Context

Matt hit `https://beta.wolfcommand.net/progress` → 404. Root cause: `serve_beta.py` had `/progress` in git (`cef569a`) but live process not reloaded. Tests used ephemeral servers → false green. Peaches restarted Beta; `/progress` now 200. Still need clean aliases for Uma/Habitat + deployed-route prove gate so this cannot recur.

## Implement

### a) `scripts/serve_beta.py` (~progress alias block)

Add near existing `/progress` clean alias:

```python
if path in ("/uma-blu-close", "/uma-blu-close/"):
    self.path = "/uma-blu-close.html"
if path in ("/habitat-operator", "/habitat-operator/"):
    self.path = "/habitat-operator.html"
```

(Use the same rewrite style already used for `/progress` → `/progress.html`.)

### b) `scripts/prove_deployed_ui_routes.py` (NEW)

Hit **real** `http://127.0.0.1:8788` (NOT ephemeral):

| Check | Expect |
|-------|--------|
| GET `/progress` | 200 + body has Progress dashboard markers |
| GET `/progress.html` | 200 |
| GET `/api/progress` (no auth) | **not** 404 (401/403/`missing_auth` OK) |
| GET `/uma-blu-close` | 200 |
| GET `/habitat-operator` | 200 |

Fail loud if `:8788` not listening or listener is not `serve_beta`. Exit non-zero on any fail. Print `PASS`/`FAIL` lines.

### c) `docs/RULE-UI-Finished-Deployed-Route-2026-09-17.md` (NEW)

UI FINISHED requires deployed-route verification against real Beta stack. Repo unit/ephemeral HTTP ≠ enough. After `serve_beta.py` changes: restart Beta + prove PASS before FINISHED.

### d) `docs/backlog/DEPLOYED-ROUTE-UI-ACCEPTANCE-2026-09-17.md`

Short backlog note.

### e) Patch `docs/RULE-Build-Factory-Self-Driving-2026-09-17.md`

Short MUST gate → new RULE + prove script.

### f) `scripts/tests/test_deployed_ui_routes.py`

Keep ephemeral tests elsewhere. Add optional/real prove: if `WOLF_PROVE_DEPLOYED=1` **or** `:8788` serve_beta detectable → run prove logic (prefer auto when detectable).

### g) `scripts/beta_restart.py`

Safe restart of Beta only via:

`launchctl kickstart -k gui/$(id -u)/net.wolfcommand.serve-beta`

Refuse if about to touch `:8787`. No orphan nohup.

## After code change

1. `python3 scripts/beta_restart.py` (or LaunchAgent kickstart)
2. `python3 scripts/prove_deployed_ui_routes.py`
3. Unit tests (`python3 -m pytest scripts/tests/…` or project norm)
4. Commit: `fix(beta): deployed-route prove + clean UI aliases after Progress 404`
5. Preserve dirty-tree WIP (Phase2.6, Habitat discovery, sha256 backups) — add/commit **in-scope only**
6. Write `docs/deliveries/GROK-REVIEW-PROGRESS-404-DEPLOYED-ROUTE-<hash>-2026-09-17.md`
7. `bf_write_run.py` stages; `--final-state DONE` only after prove PASS

## Forbidden

- Production / `:8787` / wolf-system mutations
- Habitat planner/workflow data mutations
- Metricool/ESB writes
- Weakening auth / changing live `BETA_AUTH_MODE`
- Blind git clean
- Orphan nohup Beta processes

## Report line for Peaches

ROOT CAUSE · FIX · COMMIT · prove summary · Habitat/Uma/Progress results · tests count · review · dirty reason · Beta restarted · Production untouched YES
