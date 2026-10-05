from __future__ import annotations
import json, shutil, re, subprocess, time, os, sys
from pathlib import Path
from datetime import datetime, timezone, timedelta

WITA = timezone(timedelta(hours=8))
HOME = Path.home()
ROOT = HOME / "beta-os"
PACK = ROOT / "state/final-completion/p0-v1/transfer/ro-deepen-20260930/mac-apply"
CORE = ROOT / "scripts/core"
SERVE = ROOT / "scripts/serve_beta.py"
EVID = ROOT / "state/final-completion/p0-v1/evidence"
DASH = ROOT / "dashboards"
EVID.mkdir(parents=True, exist_ok=True)
TAG = "20260930-ro-live"
now = datetime.now(WITA).strftime("%Y-%m-%dT%H:%M:%S%z")
log = []

def note(s):
    print(s, flush=True)
    log.append(s)

for name in ("owner_trading_ro.py", "owner_fitness_ro.py"):
    src, dst = PACK / name, CORE / name
    shutil.copy2(src, dst)
    note(f"copied {name} -> {dst}")
tests_dir = ROOT / "scripts/tests"
tests_dir.mkdir(parents=True, exist_ok=True)
shutil.copy2(PACK / "test_owner_ro_loaders.py", tests_dir / "test_owner_ro_loaders_20260930.py")

text = SERVE.read_text(encoding="utf-8")
bak = SERVE.with_suffix(".py.bak-ro-" + TAG)
if not bak.exists():
    shutil.copy2(SERVE, bak)
    note(f"backup {bak}")

marker_imp = "TRADING_FITNESS_RO_20260930_IMPORT"
marker_rte = "TRADING_FITNESS_RO_20260930_ROUTES"
imp = (
    f"\n# --- {marker_imp} BEGIN ---\n"
    "from core import owner_trading_ro as _owner_trading_ro\n"
    "from core import owner_fitness_ro as _owner_fitness_ro\n"
    f"# --- {marker_imp} END ---\n"
)
rte = f'''
        # --- {marker_rte} BEGIN ---
        # Owner Trading/Fitness READ-ONLY V1 surfaces. Beta only. No broker/Spartacus writes.
        if path == "/api/owner/trading-ro" or path.rstrip("/") == "/api/owner/trading-ro":
            try:
                self._send_json(_owner_trading_ro.load_trading_ro())
            except Exception as _e:
                self._send_json({{"ok": False, "error": "trading_ro_fail", "detail": str(_e), "staff_ready": False}}, status=500)
            return
        if path == "/api/owner/fitness-ro" or path.rstrip("/") == "/api/owner/fitness-ro":
            try:
                self._send_json(_owner_fitness_ro.load_fitness_ro())
            except Exception as _e:
                self._send_json({{"ok": False, "error": "fitness_ro_fail", "detail": str(_e), "staff_ready": False}}, status=500)
            return
        # --- {marker_rte} END ---
'''

changed = False
if marker_imp not in text:
    m = re.search(r"(from core import strat_radar_prove as _strat_radar\n)", text)
    if m:
        text = text[: m.end()] + imp + text[m.end() :]
    else:
        m2 = re.search(r"(from core import [^\n]+\n)(?!\s*from core)", text)
        if not m2:
            raise SystemExit("cannot find import insert point")
        text = text[: m2.end()] + imp + text[m2.end() :]
    changed = True
    note("imports inserted")
else:
    note("imports already present")

if marker_rte not in text:
    get_idx = text.find("    def do_GET(self) -> None:")
    if get_idx < 0:
        raise SystemExit("no do_GET")
    post_idx = text.find("    def do_POST(self) -> None:", get_idx)
    chunk = text[get_idx:post_idx]
    needle = "        # Owner Command Centre. Owner only. Read model over Wolf Core. No writes."
    pos = chunk.find(needle)
    if pos < 0:
        raise SystemExit("owner command needle missing in do_GET")
    chunk2 = chunk[:pos] + rte + "\n" + chunk[pos:]
    text = text[:get_idx] + chunk2 + text[post_idx:]
    changed = True
    note("routes inserted in do_GET")
else:
    note("routes already present")

if changed:
    SERVE.write_text(text, encoding="utf-8")
    note(f"wrote {SERVE}")

graft_block = '''
<!-- TRADING_FITNESS_RO_20260930 -->
<div id="ro-live" data-api="__API__" style="margin:12px 0;padding:12px;border:1px solid #444;border-radius:8px;font:14px/1.4 system-ui">
  <strong>RO live</strong> <span id="ro-live-status">loading…</span>
  <pre id="ro-live-body" style="white-space:pre-wrap;max-height:240px;overflow:auto"></pre>
</div>
<script>
(function(){
  var el=document.getElementById("ro-live"); if(!el) return;
  var api=el.getAttribute("data-api");
  fetch(api, {credentials:"same-origin"}).then(function(r){return r.json().then(function(j){return {ok:r.ok,j:j};});})
    .then(function(x){
      document.getElementById("ro-live-status").textContent = x.ok ? "ok" : "fail-closed";
      document.getElementById("ro-live-body").textContent = JSON.stringify(x.j, null, 2);
    }).catch(function(e){
      document.getElementById("ro-live-status").textContent = "error";
      document.getElementById("ro-live-body").textContent = String(e);
    });
})();
</script>
'''
for name, api in (("owner-trading-1.html", "/api/owner/trading-ro"), ("owner-fitness-1.html", "/api/owner/fitness-ro")):
    p = DASH / name
    t = p.read_text(encoding="utf-8", errors="replace")
    if "TRADING_FITNESS_RO_20260930" in t or 'id="ro-live"' in t:
        note(f"{name} already grafted")
        continue
    block = graft_block.replace("__API__", api)
    if "</body>" in t:
        t = t.replace("</body>", block + "\n</body>", 1)
    else:
        t += "\n" + block
    p.write_text(t, encoding="utf-8")
    note(f"grafted {name}")

os.chdir(ROOT)
env = os.environ.copy()
env["PYTHONPATH"] = str(ROOT / "scripts") + os.pathsep + env.get("PYTHONPATH", "")
r = subprocess.run(["python3", str(tests_dir / "test_owner_ro_loaders_20260930.py")], capture_output=True, text=True, env=env, timeout=60)
note(f"loader_tests rc={r.returncode}")
note((r.stdout or "")[-800:])
note((r.stderr or "")[-400:])
if r.returncode != 0:
    raise SystemExit("loader tests failed")

uid = os.getuid()
label = f"gui/{uid}/net.wolfcommand.serve-beta"
kr = subprocess.run(["launchctl", "kickstart", "-k", label], capture_output=True, text=True)
note(f"kickstart rc={kr.returncode} {(kr.stderr or kr.stdout or '')[:200]}")
time.sleep(2.5)

probes = {}
for u in ("/api/owner/trading-ro", "/api/owner/fitness-ro", "/owner/trading", "/owner/fitness", "/api/health"):
    try:
        pr = subprocess.run(
            ["curl", "-sS", "-o", "/tmp/robody.json", "-w", "%{http_code}", "--max-time", "8", f"http://127.0.0.1:8788{u}"],
            capture_output=True, text=True, timeout=12,
        )
        code = (pr.stdout or "").strip()
        body = Path("/tmp/robody.json").read_text(encoding="utf-8", errors="replace")[:600]
        probes[u] = {"http": code, "body_head": body}
        note(f"probe {u} -> {code}")
    except Exception as e:
        probes[u] = {"http": "ERR", "error": str(e)}
        note(f"probe {u} ERR {e}")

prod = subprocess.run(["lsof", "-nP", "-iTCP:8787", "-sTCP:LISTEN"], capture_output=True, text=True, timeout=5)
note("prod8787_listen:\n" + (prod.stdout or "")[:300])

trading_ok = probes.get("/api/owner/trading-ro", {}).get("http") == "200"
fitness_ok = probes.get("/api/owner/fitness-ro", {}).get("http") == "200"
live = trading_ok and fitness_ok
status = "RO_LIVE" if live else "RO_APPLY_PARTIAL"

evidence = {
    "tag": TAG,
    "at": now,
    "status": status,
    "live": live,
    "staff_ready": False,
    "claim": "RO_API_MOUNTED" if live else "NOT_REBUILT_PLUS_PROVEN",
    "prod_8787": "untouched_listen_only",
    "log": log,
    "probes": probes,
}
(EVID / f"RO-APPLY-ONESHOT-{TAG}.json").write_text(json.dumps(evidence, indent=2), encoding="utf-8")
(EVID / f"RO-APPLY-ONESHOT-{TAG}.txt").write_text("\n".join(log), encoding="utf-8")

gap = ROOT / "state/final-completion/p0-v1/CONNECTOR-GAP-20260930.json"
if gap.exists():
    try:
        g = json.loads(gap.read_text(encoding="utf-8"))
        g["ro_trading_fitness"] = {"status": status, "at": now, "apis": ["/api/owner/trading-ro", "/api/owner/fitness-ro"], "live": live}
        gap.write_text(json.dumps(g, indent=2), encoding="utf-8")
        note(f"updated {gap}")
    except Exception as e:
        note(f"gap update skip: {e}")

patch_status = ROOT / "state/final-completion/p0-v1/transfer/ro-deepen-20260930/STATUS.json"
patch_status.parent.mkdir(parents=True, exist_ok=True)
patch_status.write_text(json.dumps({"status": status, "at": now, "live": live, "staff_ready": False}, indent=2), encoding="utf-8")

print("==== FINAL ====", status, "live=", live, flush=True)
sys.exit(0 if live else 2)
