#!/bin/bash
# ONE_SHOT_APPLY.sh — Trading+Fitness RO mount on Beta only. Never touch prod :8787.
set -euo pipefail
export PATH="/usr/bin:/bin:/usr/sbin:/sbin:/opt/homebrew/bin:$PATH"
ROOT="${HOME}/beta-os"
PACK="${ROOT}/state/final-completion/p0-v1/transfer/ro-deepen-20260930/mac-apply"
EVID="${ROOT}/state/final-completion/p0-v1/evidence"
TAG="20260930-ro-live"
mkdir -p "${ROOT}/scripts/core" "$EVID"

# 1) Install loaders
cp -f "$PACK/owner_trading_ro.py" "$ROOT/scripts/core/owner_trading_ro.py"
cp -f "$PACK/owner_fitness_ro.py" "$ROOT/scripts/core/owner_fitness_ro.py"
cp -f "$PACK/test_owner_ro_loaders.py" "$ROOT/scripts/tests/test_owner_ro_loaders_20260930.py"

# 2) Wire serve_beta.py if routes missing
python3 - <<'PY'
from pathlib import Path
import re
p = Path.home() / "beta-os/scripts/ops/serve_beta.py"
if not p.exists():
    p = Path.home() / "beta-os/scripts/serve_beta.py"
text = p.read_text()
marker = "TRADING_FITNESS_RO_20260930"
if marker in text:
    print("serve_beta: routes already wired")
else:
    glue = '''
# --- TRADING_FITNESS_RO_20260930 BEGIN ---
try:
    from scripts.core.owner_trading_ro import load_trading_ro
    from scripts.core.owner_fitness_ro import load_fitness_ro
except Exception:
    try:
        from owner_trading_ro import load_trading_ro
        from owner_fitness_ro import load_fitness_ro
    except Exception as _e:
        load_trading_ro = load_fitness_ro = None
        _ro_import_err = str(_e)
# --- TRADING_FITNESS_RO_20260930 END ---
'''
    # Prefer inserting after imports block
    lines = text.splitlines(True)
    insert_at = 0
    for i, ln in enumerate(lines[:80]):
        if ln.startswith("import ") or ln.startswith("from "):
            insert_at = i + 1
    lines.insert(insert_at, glue)
    text2 = "".join(lines)
    # Hook path dispatch — look for common patterns
    hook = '''
        # TRADING_FITNESS_RO_20260930 routes
        if path.rstrip("/") == "/api/owner/trading-ro" and load_trading_ro:
            return self._json(load_trading_ro())
        if path.rstrip("/") == "/api/owner/fitness-ro" and load_fitness_ro:
            return self._json(load_fitness_ro())
'''
    # If no _json helper, leave a TODO file
    if "TRADING_FITNESS_RO_20260930 routes" not in text2:
        # try inject near other /api/owner handlers
        m = re.search(r'(/api/owner/[^\"]+)', text2)
        note = Path.home() / "beta-os/state/final-completion/p0-v1/transfer/ro-deepen-20260930/mac-apply/SERVE_HOOK_NEEDED.txt"
        note.write_text("Manual hook may be needed. Imports inserted. Hook snippet:\n" + hook + "\nserve=" + str(p) + "\n")
        # Still write a small companion router module
        router = Path.home() / "beta-os/scripts/core/owner_ro_routes.py"
        router.write_text('''
def try_owner_ro(path, json_response):
    """Return response or None. Beta only."""
    try:
        from scripts.core.owner_trading_ro import load_trading_ro
        from scripts.core.owner_fitness_ro import load_fitness_ro
    except Exception:
        from owner_trading_ro import load_trading_ro
        from owner_fitness_ro import load_fitness_ro
    p = path.rstrip("/")
    if p == "/api/owner/trading-ro":
        return json_response(load_trading_ro())
    if p == "/api/owner/fitness-ro":
        return json_response(load_fitness_ro())
    return None
''')
    p.write_text(text2)
    print("serve_beta: imports inserted at", p)
PY

# 3) Graft board snippets if #ro-live missing
python3 - <<'PY'
from pathlib import Path
snip = (Path.home() / "beta-os/state/final-completion/p0-v1/transfer/ro-deepen-20260930/mac-apply/board-render-snippets.js").read_text()
for name, api in [("owner-trading-1.html", "/api/owner/trading-ro"), ("owner-fitness-1.html", "/api/owner/fitness-ro")]:
    p = Path.home() / "beta-os/dashboards" / name
    if not p.exists():
        print("missing", p); continue
    t = p.read_text()
    if "TRADING_FITNESS_RO_20260930" in t or "id=\"ro-live\"" in t:
        print(name, "already grafted"); continue
    block = f'''
<!-- TRADING_FITNESS_RO_20260930 -->
<div id="ro-live" data-api="{api}" style="margin:12px 0;padding:12px;border:1px solid #444;border-radius:8px;font:14px/1.4 system-ui">
  <strong>RO live</strong> <span id="ro-live-status">loading…</span>
  <pre id="ro-live-body" style="white-space:pre-wrap;max-height:240px;overflow:auto"></pre>
</div>
<script>
(function(){{
  var el=document.getElementById("ro-live"); if(!el) return;
  var api=el.getAttribute("data-api");
  fetch(api, {{credentials:"same-origin"}}).then(function(r){{return r.json().then(function(j){{return {{ok:r.ok,j:j}};}});}})
    .then(function(x){{
      document.getElementById("ro-live-status").textContent = x.ok ? "ok" : "fail-closed";
      document.getElementById("ro-live-body").textContent = JSON.stringify(x.j, null, 2);
    }}).catch(function(e){{
      document.getElementById("ro-live-status").textContent = "error";
      document.getElementById("ro-live-body").textContent = String(e);
    }});
}})();
</script>
'''
    if "</body>" in t:
        t = t.replace("</body>", block + "\n</body>", 1)
    else:
        t += block
    p.write_text(t)
    print("grafted", name)
PY

# 4) Unit tests for loaders
cd "$ROOT" && python3 scripts/tests/test_owner_ro_loaders_20260930.py || python3 "$PACK/test_owner_ro_loaders.py" || true

# 5) Kickstart Beta only
launchctl kickstart -k "gui/$(id -u)/net.wolfcommand.serve-beta" || true
sleep 2

# 6) Probe
{
  echo "tag=$TAG"
  echo "time=$(date '+%Y-%m-%d %H:%M:%S %Z')"
  for u in /api/owner/trading-ro /api/owner/fitness-ro /owner/trading /owner/fitness; do
    code=$(curl -sS -o /tmp/robody.json -w "%{http_code}" --max-time 5 "http://127.0.0.1:8788$u" || echo ERR)
    echo "$u -> $code"
    head -c 400 /tmp/robody.json 2>/dev/null; echo
  done
  # never touch 8787 mutate — read-only ping ok
  curl -sS -o /dev/null -w "prod8787=%{http_code} pid_check_only\n" --max-time 3 http://127.0.0.1:8787/ || true
} | tee "$EVID/RO-APPLY-ONESHOT-$TAG.txt"

echo DONE
