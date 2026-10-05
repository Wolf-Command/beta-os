#!/bin/bash
set -euo pipefail
cp /Users/wolfterminal/beta-os/scripts/mac-reachability/recover-bounded.sh /var/wolfrecover/recover-bounded.sh
chown wolfrecover:wolfrecover /var/wolfrecover/recover-bounded.sh
chmod 755 /var/wolfrecover/recover-bounded.sh
ssh -i /Users/wolfterminal/.ssh/nas_wolfcommand \
  -o IdentitiesOnly=yes -o BatchMode=yes \
  -o UserKnownHostsFile=/Users/wolfterminal/.ssh/known_hosts \
  -o StrictHostKeyChecking=yes \
  "Mr Wolf@100.86.93.120" \
  'umask 077; mkdir -p "$HOME/.ssh/wolf-recovery"; cat > "$HOME/.ssh/wolf-recovery/id_ed25519"; chmod 700 "$HOME/.ssh/wolf-recovery"; chmod 600 "$HOME/.ssh/wolf-recovery/id_ed25519"; ls -l "$HOME/.ssh/wolf-recovery/id_ed25519"' \
  < /var/wolfrecover/client_ed25519
echo COPY_OK
