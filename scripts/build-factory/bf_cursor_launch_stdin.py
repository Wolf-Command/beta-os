#!/usr/bin/env python3
"""Factory launcher (stdin prompt). Args: log, prompt file, pidfile, result json (rel or abs).
Runs cursor-agent with the prompt on stdin, records the child pid, then appends
RESULT_JSON and exactly one final EXIT:<0|1> line. Never echoes prompt or argv.
"""
import json, os, subprocess, sys
from pathlib import Path
ROOT = Path("/Users/wolfterminal/beta-os")
log, prompt, pidfile, result = (Path(a) for a in sys.argv[1:5])
result = result if result.is_absolute() else ROOT / result
env = dict(os.environ)
env["PATH"] = os.path.expanduser("~/.local/bin") + ":/opt/homebrew/bin:/usr/bin:/bin:" + env.get("PATH", "")
env["CURSOR_AGENT_NO_INTERACTIVE"] = "1"
log.parent.mkdir(parents=True, exist_ok=True)
with open(log, "ab") as lf, open(prompt, "rb") as pf:
    p = subprocess.Popen(
        ["/Users/wolfterminal/.local/bin/cursor-agent", "-p", "--force", "--model", "composer-2.5",
         "--workspace", str(ROOT)],
        cwd=str(ROOT), stdin=pf, stdout=lf, stderr=subprocess.STDOUT, env=env)
    Path(pidfile).write_text(str(p.pid) + "\n")
    lf.write(f"CURSOR_AGENT_PID={p.pid}\n".encode()); lf.flush()
    rc = p.wait()
ec = 1
try:
    d = json.loads(result.read_text())
    ok = rc == 0 and int(d.get("tests_fail", 1) or 0) == 0 and int(d.get("tests_pass", 0) or 0) > 0 \
        and str(d.get("status", "")).upper().startswith("IMPLEMENTATION_DONE")
    ec = 0 if ok else 1
except Exception:
    ec = 1
with open(log, "a") as lf:
    lf.write(f"\nCURSOR_RC={rc}\nRESULT_JSON: {result.relative_to(ROOT) if str(result).startswith(str(ROOT)) else result}\nEXIT:{ec}\n")
sys.exit(ec)
