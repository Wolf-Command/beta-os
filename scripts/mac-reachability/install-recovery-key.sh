#!/bin/bash
set -euo pipefail
if [[ "$(id -u)" -ne 0 ]]; then
  echo NOT_ROOT
  exit 1
fi
IP="100.113.26.51"
PORT="2222"
BASE="/var/wolfrecover"
USER_NAME="wolfrecover"
UID_NUM="550"
GID_NUM="550"

if ! ifconfig utun4 | awk '/inet /{print $2}' | grep -qx "$IP"; then
  echo "TAILSCALE_IP_CHANGED"
  ifconfig utun4 | awk '/inet /{print}'
  exit 2
fi

if ! dscl . -read "/Groups/${USER_NAME}" >/dev/null 2>&1; then
  dscl . -create "/Groups/${USER_NAME}"
  dscl . -create "/Groups/${USER_NAME}" PrimaryGroupID "$GID_NUM"
  dscl . -create "/Groups/${USER_NAME}" Password "*"
fi
if ! dscl . -read "/Users/${USER_NAME}" >/dev/null 2>&1; then
  dscl . -create "/Users/${USER_NAME}"
  dscl . -create "/Users/${USER_NAME}" UserShell /bin/bash
  dscl . -create "/Users/${USER_NAME}" RealName "Wolf Recovery"
  dscl . -create "/Users/${USER_NAME}" UniqueID "$UID_NUM"
  dscl . -create "/Users/${USER_NAME}" PrimaryGroupID "$GID_NUM"
  dscl . -create "/Users/${USER_NAME}" NFSHomeDirectory "$BASE"
  dscl . -create "/Users/${USER_NAME}" Password "*"
fi

mkdir -p "$BASE/.ssh" "$BASE/logs"
chmod 755 "$BASE"
chmod 700 "$BASE/.ssh"

cat > "$BASE/recover-bounded.sh" << 'SCRIPT'
#!/bin/bash
set -u
AUDIT="/var/wolfrecover/logs/audit.log"
ts="$(TZ=Asia/Makassar date '+%Y-%m-%dT%H:%M:%S%z')"
cmd="${SSH_ORIGINAL_COMMAND:-status}"
# one line, no newlines
safe="$(printf '%s' "$cmd" | tr '\n' ' ' | cut -c1-180)"
audit() {
  printf '%s cmd=%s result=%s\n' "$ts" "$safe" "$1" >> "$AUDIT"
}
case "$cmd" in
  status)
    app="$(python3 - << 'PY'
import subprocess
exact="/Applications/Grok Bot.app/Contents/MacOS/Grok Bot"
helper="/Applications/Grok Bot.app/Contents/Frameworks/Grok Bot Helper.app/Contents/MacOS/Grok Bot Helper"
out=subprocess.check_output(["ps","-ax","-o","pid=,comm="], text=True)
app=helper_n=""
hn=0
for line in out.splitlines():
    line=line.strip()
    if not line: continue
    pid,_,comm=line.partition(" ")
    if comm==exact and not app: app=pid
    elif comm==helper: hn+=1
print(app or "NONE")
print(hn)
PY
)"
    prod="$(curl -s -o /dev/null -w '%{http_code}' --max-time 5 http://127.0.0.1:8787/api/health || echo ERR)"
    beta="$(curl -s -o /dev/null -w '%{http_code}' --max-time 5 http://127.0.0.1:8788/api/health || echo ERR)"
    prod_pid="$(ps -p 15975 -o pid= 2>/dev/null | tr -d ' ' || true)"
    audit "status"
    echo "STATUS host=$(hostname) uptime=$(uptime | tr -d '\n')"
    echo "PROD_HEALTH ${prod} PROD_PID ${prod_pid:-missing}"
    echo "BETA_HEALTH ${beta}"
    echo "GROK ${app}"
    ;;
  recover-watchdog)
    uid_gui="501"
    launchctl kickstart "gui/${uid_gui}/com.wolf.mac-reachability.supervisor" || true
    launchctl kickstart "gui/${uid_gui}/com.wolf.mac-reachability.heartbeat" || true
    launchctl kickstart "gui/${uid_gui}/com.wolfcommand.grok-bot-keepalive" || true
    audit "recover-watchdog"
    echo "RECOVER_WATCHDOG_DONE"
    ;;
  *)
    audit "DENIED"
    echo "DENIED"
    exit 1
    ;;
esac
SCRIPT
chmod 755 "$BASE/recover-bounded.sh"
chown -R "${USER_NAME}:${USER_NAME}" "$BASE"

if [[ ! -f "$BASE/ssh_host_ed25519_key" ]]; then
  ssh-keygen -t ed25519 -f "$BASE/ssh_host_ed25519_key" -N "" -q
fi
if [[ ! -f "$BASE/client_ed25519" ]]; then
  ssh-keygen -t ed25519 -f "$BASE/client_ed25519" -N "" -q -C "wolf-recovery-key"
fi
chmod 600 "$BASE/ssh_host_ed25519_key" "$BASE/client_ed25519"
chown root:wheel "$BASE/ssh_host_ed25519_key" "$BASE/client_ed25519"

PUB="$(cat "$BASE/client_ed25519.pub")"
printf 'restrict,command="/var/wolfrecover/recover-bounded.sh" %s\n' "$PUB" > "$BASE/.ssh/authorized_keys"
chmod 600 "$BASE/.ssh/authorized_keys"
chown "${USER_NAME}:${USER_NAME}" "$BASE/.ssh/authorized_keys"

cat > "$BASE/sshd_config" << CFG
Port ${PORT}
ListenAddress ${IP}
HostKey ${BASE}/ssh_host_ed25519_key
PasswordAuthentication no
KbdInteractiveAuthentication no
ChallengeResponseAuthentication no
PermitRootLogin no
PubkeyAuthentication yes
AllowUsers ${USER_NAME}
AuthorizedKeysFile ${BASE}/.ssh/authorized_keys
ForceCommand ${BASE}/recover-bounded.sh
PermitTTY no
AllowTcpForwarding no
X11Forwarding no
AllowAgentForwarding no
GatewayPorts no
PidFile ${BASE}/sshd.pid
ClientAliveInterval 30
MaxAuthTries 2
CFG
chmod 644 "$BASE/sshd_config"

cat > /Library/LaunchDaemons/com.wolf.recovery-sshd.plist << 'PLIST'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>com.wolf.recovery-sshd</string>
  <key>ProgramArguments</key>
  <array>
    <string>/usr/sbin/sshd</string>
    <string>-D</string>
    <string>-f</string>
    <string>/var/wolfrecover/sshd_config</string>
  </array>
  <key>RunAtLoad</key>
  <true/>
  <key>KeepAlive</key>
  <true/>
  <key>StandardErrorPath</key>
  <string>/var/wolfrecover/logs/sshd.err</string>
</dict>
</plist>
PLIST
chmod 644 /Library/LaunchDaemons/com.wolf.recovery-sshd.plist
launchctl bootout system/com.wolf.recovery-sshd 2>/dev/null || true
launchctl bootstrap system /Library/LaunchDaemons/com.wolf.recovery-sshd.plist
sleep 1
echo INSTALL_OK
lsof -nP -iTCP:${PORT} -sTCP:LISTEN 2>/dev/null || true
