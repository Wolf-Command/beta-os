#!/usr/bin/env bash
# MAC-APPLY — gated LaunchAgent commission (Link)
# NEVER run as recovery while pipe RED from box.
# NEVER escalate Matt open-app / Cmd-Q / pkill.
set -euo pipefail

ROOT="${MAC_REACH_ROOT:-/Users/wolfterminal/beta-os}"
SCRIPTS="${ROOT}/scripts/mac-reachability"
STATE="${ROOT}/state/mac-reachability"
LOGS="${STATE}/logs"
AGENTS="${HOME}/Library/LaunchAgents"
MID="${MAC_MACHINE_ID:-36d8fa4b-2d58-4983-b227-e5bfa5495e78}"
LABEL_HB="com.wolf.mac-reachability.heartbeat"
LABEL_SV="com.wolf.mac-reachability.supervisor"

die() { echo "MAC_APPLY_ABORT: $*" >&2; exit 1; }

# Hard gate — caller must prove GREEN out-of-band then set confirm
[[ "${MAC_APPLY_CONFIRM:-}" == "GREEN" ]] || die "refusing — set MAC_APPLY_CONFIRM=GREEN only after ListMachines connected=true + Shell PROVE_OK"
[[ "$(uname -s)" == "Darwin" ]] || die "refusing — not Darwin (do not run on box Linux as install)"

echo "mac-apply: preflight mid=${MID} root=${ROOT}"
mkdir -p "$SCRIPTS" "$LOGS" "${ROOT}/docs" "$AGENTS"

# Expect scripts already copied into $SCRIPTS
for s in heartbeat.sh supervisor.sh classify.sh recover.sh verify.sh; do
  [[ -x "${SCRIPTS}/${s}" ]] || die "missing executable ${SCRIPTS}/${s}"
done

install_plist() {
  local label="$1" src="$2"
  local dst="${AGENTS}/${label}.plist"
  [[ -f "$src" ]] || die "missing template/src $src"
  # If src still has REPLACE / TEMPLATE markers for required ProgramArguments — refuse
  if grep -q 'REPLACE_ME' "$src" 2>/dev/null; then
    die "plist still REPLACE_ME: $src"
  fi
  cp "$src" "$dst"
  echo "installed $dst"
}

# Prefer already-rendered plists beside scripts; else TEMPLATEs with .TEMPLATE stripped by operator
HB_SRC="${SCRIPTS}/${LABEL_HB}.plist"
SV_SRC="${SCRIPTS}/${LABEL_SV}.plist"
[[ -f "$HB_SRC" ]] || HB_SRC="${SCRIPTS}/${LABEL_HB}.plist.TEMPLATE"
[[ -f "$SV_SRC" ]] || SV_SRC="${SCRIPTS}/${LABEL_SV}.plist.TEMPLATE"

install_plist "$LABEL_HB" "$HB_SRC"
install_plist "$LABEL_SV" "$SV_SRC"

UID_N="$(id -u)"
launchctl bootout "gui/${UID_N}/${LABEL_HB}" 2>/dev/null || true
launchctl bootout "gui/${UID_N}/${LABEL_SV}" 2>/dev/null || true
launchctl bootstrap "gui/${UID_N}" "${AGENTS}/${LABEL_HB}.plist"
launchctl bootstrap "gui/${UID_N}" "${AGENTS}/${LABEL_SV}.plist"
launchctl kickstart -k "gui/${UID_N}/${LABEL_HB}"
launchctl kickstart -k "gui/${UID_N}/${LABEL_SV}"

echo "mac-apply: bootstrap done — VERIFY required (Shell PROVE_OK + heartbeat fresh). process alive ≠ GREEN."
echo "mac-apply: next = PROVE-MATRIX Run A then Run B; matt_contacted=false"
exit 0
