#!/bin/bash
set -u
OUT="/Users/wolfterminal/beta-os/state/mac-reachability/RECOVERY-KEY-TEST.json"
ssh_try() {
  ssh -i /var/wolfrecover/client_ed25519 -p 2222 \
    -o IdentitiesOnly=yes -o BatchMode=yes -o StrictHostKeyChecking=accept-new \
    -o UserKnownHostsFile=/var/wolfrecover/known_hosts \
    wolfrecover@100.113.26.51 "$1"
}
ssh_try status > /tmp/rk-status.txt 2>&1; echo $? > /tmp/rk-status.rc
ssh_try "echo PWNED; /bin/bash -c id" > /tmp/rk-denied.txt 2>&1; echo $? > /tmp/rk-denied.rc
ssh_try recover-watchdog > /tmp/rk-recover.txt 2>&1; echo $? > /tmp/rk-recover.rc
tail -n 8 /var/wolfrecover/logs/audit.log > /tmp/rk-audit.txt 2>&1 || true
lsof -nP -iTCP:2222 -sTCP:LISTEN > /tmp/rk-listen.txt 2>&1 || true
ps -p 15975 -o pid= | tr -d " " > /tmp/rk-prod.txt
python3 - << 'PY2'
import json
from pathlib import Path
def t(p):
    return Path(p).read_text(errors="replace")
data = {
  "status_rc": t("/tmp/rk-status.rc").strip(),
  "status": t("/tmp/rk-status.txt"),
  "denied_rc": t("/tmp/rk-denied.rc").strip(),
  "denied": t("/tmp/rk-denied.txt"),
  "recover_rc": t("/tmp/rk-recover.rc").strip(),
  "recover": t("/tmp/rk-recover.txt"),
  "audit": t("/tmp/rk-audit.txt"),
  "listen": t("/tmp/rk-listen.txt"),
  "prod_pid": t("/tmp/rk-prod.txt").strip(),
}
Path("/Users/wolfterminal/beta-os/state/mac-reachability/RECOVERY-KEY-TEST.json").write_text(json.dumps(data, indent=2)+"\n")
print("TEST_FILE_WRITTEN")
PY2
