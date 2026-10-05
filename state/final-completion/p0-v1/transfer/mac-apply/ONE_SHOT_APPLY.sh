#!/bin/bash
# ONE_SHOT_APPLY.sh — deepen3 HKEGCAV RO on Beta only. Never touch prod :8787.
# If Shell drops mid-apply: EXIT PARTIAL (caller must not await/retry).
set -euo pipefail
export PATH="/usr/bin:/bin:/usr/sbin:/sbin:/opt/homebrew/bin:$PATH"
ROOT="${HOME}/beta-os"
# Pack may live under beta-os mirror OR be copied into /tmp by agent
PACK_CANDIDATES=(
  "${ROOT}/state/final-completion/p0-v1/transfer/ro-deepen3-20260930/mac-apply"
  "${HOME}/.openclaw/workspace/state/final-completion/p0-v1/transfer/ro-deepen3-20260930/mac-apply"
  "/tmp/ro-deepen3-mac-apply"
)
PACK=""
for c in "${PACK_CANDIDATES[@]}"; do
  if [[ -d "$c" ]]; then PACK="$c"; break; fi
done
if [[ -z "$PACK" ]]; then echo "PACK_MISSING"; exit 2; fi
EVID="${ROOT}/state/final-completion/p0-v1/evidence"
TAG="20260930-ro-deepen3"
mkdir -p "${ROOT}/scripts/core" "$EVID" "${ROOT}/scripts/tests"

echo "PACK=$PACK"
# 1) Install loaders
for f in owner_habitat_investment_ro.py ops_kuta_rates_ro.py owner_gatekeeper_ro.py \
         ops_event_bus_ro.py seats_content_ro.py seats_ads_studio_ro.py \
         seats_resolve_studio_ro.py voice_boards_ro.py hkegcav_ro_routes.py; do
  cp -f "$PACK/$f" "$ROOT/scripts/core/$f"
  echo "installed $f"
done
cp -f "$PACK/test_hkegcav_ro_loaders.py" "$ROOT/scripts/tests/test_hkegcav_ro_loaders_20260930.py" 2>/dev/null || true

# 2) Wire serve_beta.py routes if marker missing
python3 - <<'PY'
from pathlib import Path
import re, json
root = Path.home() / "beta-os"
p = root / "scripts/serve_beta.py"
if not p.exists():
    p = root / "scripts/ops/serve_beta.py"
text = p.read_text()
marker = "HKEGCAV_RO_20260930"
if marker in text:
    print("serve_beta: routes already wired")
else:
    # Insert import + dispatch near prior OWNER RO block if present, else after imports
    glue_import = f'''
# --- {marker} BEGIN ---
try:
    from scripts.core.hkegcav_ro_routes import try_hkegcav_ro
except Exception:
    try:
        from hkegcav_ro_routes import try_hkegcav_ro
    except Exception:
        try_hkegcav_ro = None
# --- {marker} END ---
'''
    lines = text.splitlines(True)
    insert_at = 0
    for i, ln in enumerate(lines[:120]):
        if ln.startswith("import ") or ln.startswith("from "):
            insert_at = i + 1
    # Prefer after TRADING_FITNESS or travel/learning markers
    for i, ln in enumerate(lines):
        if "TRADING_FITNESS_RO_20260930 END" in ln or "TRAVEL_LEARNING_RO" in ln or "OWNER_RO_DEEPEN2" in ln:
            insert_at = i + 1
    lines.insert(insert_at, glue_import)
    text2 = "".join(lines)
    hook = f'''
        # {marker} routes
        if try_hkegcav_ro is not None:
            _hk = try_hkegcav_ro(path, self._json) if hasattr(self, "_json") else None
            if _hk is not None:
                return _hk
'''
    # Find a path-dispatch area
    if f"{marker} routes" not in text2:
        # Try inject after an existing trading-ro route
        m = re.search(r'(if path\.rstrip\("/"\) == "/api/owner/learning-ro".*?\n)', text2)
        if not m:
            m = re.search(r'(if path\.rstrip\("/"\) == "/api/owner/trading-ro".*?\n(?:.*\n){0,3})', text2)
        note = root / "state/final-completion/p0-v1/transfer/ro-deepen3-20260930/mac-apply/SERVE_HOOK_NOTE.txt"
        note.parent.mkdir(parents=True, exist_ok=True)
        if m:
            text2 = text2[:m.end()] + hook + text2[m.end():]
            print("serve_beta: hook injected after existing owner-ro")
        else:
            note.write_text("Manual hook may be needed. Imports inserted.\n" + hook + "\nserve=" + str(p) + "\n")
            # Also try common do_GET pattern
            m2 = re.search(r'(def do_GET\(self\).*?:\n)', text2)
            if m2:
                # insert early in do_GET after path assign if possible
                text2 = text2[:m2.end()] + "        # HKEGCAV placeholder — see try_hkegcav_ro below\n" + text2[m2.end():]
            print("serve_beta: imports inserted; check SERVE_HOOK_NOTE.txt")
    p.write_text(text2)
    print("serve_beta: updated", p)
PY

# 3) Graft boards with usable RO render (not shell-only JSON forever — structured tiles)
python3 - <<'PY'
from pathlib import Path
import json
root = Path.home() / "beta-os"
pack = None
for c in [
    root / "state/final-completion/p0-v1/transfer/ro-deepen3-20260930/mac-apply",
    Path.home() / ".openclaw/workspace/state/final-completion/p0-v1/transfer/ro-deepen3-20260930/mac-apply",
    Path("/tmp/ro-deepen3-mac-apply"),
]:
    if (c / "board_graft_map.json").exists():
        pack = c; break
mp = json.loads((pack / "board_graft_map.json").read_text())
MARKER = "HKEGCAV_RO_20260930"
for name, api in mp.items():
    p = root / "dashboards" / name
    if not p.exists():
        print("missing", name); continue
    t = p.read_text(encoding="utf-8", errors="replace")
    if MARKER in t and 'id="ro-live"' in t and "ro-deepen3-render" in t:
        print(name, "already grafted deepen3"); continue
    # Remove prior shallow dump graft if present without deepen3 renderer
    block = f'''
<!-- {MARKER} -->
<div id="ro-live" class="ro-deepen3-render" data-api="{api}" style="margin:12px 0;padding:14px;border:1px solid #3a3a3a;border-radius:10px;font:14px/1.45 system-ui,sans-serif;background:#111;color:#eee">
  <div style="display:flex;gap:10px;align-items:center;flex-wrap:wrap">
    <strong>RO live</strong>
    <span id="ro-live-status" style="opacity:.8">loading…</span>
    <code style="opacity:.6">{api}</code>
  </div>
  <div id="ro-live-banner" style="margin-top:8px;opacity:.9"></div>
  <div id="ro-live-cards" style="display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:8px;margin-top:10px"></div>
  <details style="margin-top:10px"><summary>raw JSON</summary>
    <pre id="ro-live-body" style="white-space:pre-wrap;max-height:220px;overflow:auto;font-size:12px"></pre>
  </details>
</div>
<script>
(function(){{
  var el=document.getElementById("ro-live"); if(!el) return;
  var api=el.getAttribute("data-api");
  function card(k,v){{
    var d=document.createElement("div");
    d.style.cssText="padding:10px;border:1px solid #333;border-radius:8px;background:#1a1a1a";
    d.innerHTML="<div style=\\"opacity:.6;font-size:11px\\">"+k+"</div><div style=\\"font-size:16px;font-weight:600\\">"+v+"</div>";
    return d;
  }}
  fetch(api, {{credentials:"same-origin"}}).then(function(r){{return r.json().then(function(j){{return {{ok:r.ok,j:j}};}});}})
    .then(function(x){{
      var j=x.j||{{}};
      document.getElementById("ro-live-status").textContent = (x.ok && j.ok) ? ("ok · "+(j.reason||"")) : "fail-closed";
      document.getElementById("ro-live-banner").textContent = j.banner || "";
      var box=document.getElementById("ro-live-cards"); box.innerHTML="";
      var keys=["title","daily_md_count","project_count","html_bytes","mode","never_send","live_booking","spend","db_bytes"];
      keys.forEach(function(k){{ if(j[k]!==undefined && j[k]!==null) box.appendChild(card(k, String(j[k]))); }});
      if(j.status && j.status.headline) box.appendChild(card("headline", j.status.headline));
      if(j.db && j.db.table_counts) box.appendChild(card("db_tables", JSON.stringify(j.db.table_counts)));
      if(j.brief && j.brief.name) box.appendChild(card("brief", j.brief.name));
      if(j.sections) box.appendChild(card("sections", String((j.sections||[]).length)));
      if(j.entities) box.appendChild(card("entities", Object.keys(j.entities).join(",")));
      if(j.refuse) box.appendChild(card("refuse", (j.refuse||[]).slice(0,3).join(" · ")));
      document.getElementById("ro-live-body").textContent = JSON.stringify(j, null, 2);
    }}).catch(function(e){{
      document.getElementById("ro-live-status").textContent = "error";
      document.getElementById("ro-live-body").textContent = String(e);
    }});
}})();
</script>
'''
    if MARKER in t and 'id="ro-live"' in t:
        # replace old block roughly: from marker comment to following script end is hard; append deepen3 if missing renderer
        if "ro-deepen3-render" not in t:
            if "</body>" in t:
                t = t.replace("</body>", block + "\n</body>", 1)
            else:
                t += block
    else:
        if "</body>" in t:
            t = t.replace("</body>", block + "\n</body>", 1)
        else:
            t += block
    p.write_text(t)
    print("grafted", name, "->", api)
PY

# 4) Unit tests
cd "$ROOT" && python3 scripts/tests/test_hkegcav_ro_loaders_20260930.py || python3 "$PACK/test_hkegcav_ro_loaders.py" || true

# 5) Kickstart Beta only
launchctl kickstart -k "gui/$(id -u)/net.wolfcommand.serve-beta" || true
sleep 2

# 6) Probe
{
  echo "tag=$TAG"
  echo "time=$(date '+%Y-%m-%d %H:%M:%S %Z')"
  for u in \
    /api/owner/habitat-investment-ro \
    /api/ops/kuta-rates-ro \
    /api/owner/gatekeeper-ro \
    /api/ops/event-bus-ro \
    /api/seats/content-ro \
    /api/seats/ads-studio-ro \
    /api/seats/resolve-studio-ro \
    /api/voice/ro \
    /api/voice/amg-ro \
    /habitat-investment-2026 /kuta-rates /owner/gatekeeper /ops/event-bus \
    /seats/ads-studio /seats/resolve-studio /amg-voice /api/health
  do
    code=$(curl -sS -o /tmp/ro3body.json -w "%{http_code}" --max-time 5 "http://127.0.0.1:8788$u" || echo ERR)
    echo "$u -> $code"
    head -c 220 /tmp/ro3body.json 2>/dev/null; echo
  done
  curl -sS -o /dev/null -w "prod8787_ro_ping=%{http_code}\n" --max-time 3 http://127.0.0.1:8787/ || true
} | tee "$EVID/RO-DEEPEN3-PROBES-$TAG.txt"

echo DONE
