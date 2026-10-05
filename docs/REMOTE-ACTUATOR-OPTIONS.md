# Remote actuator options — box → Studio while local-exec DOWN

**Owner:** Link (Mac Reachability)  
**Updated:** 2026-09-23 ~09:49 WITA  
**Pipe:** still `connected=false` — **not GREEN**.  
**Standing:** ATTEMPT#3 FAIL_CEILING. No thrash. No Matt-as-restart.

Actuator audit (`ACTUATOR-AUDIT.md`) found **no** usable OOB path today. This doc ranks **Owner-approvable** next actuators so commission is not forever blocked on chance GUI reconnect.

---

## Tier 0 — already designed (needs one GREEN)

| Item | Status |
|------|--------|
| LaunchAgent heartbeat + supervisor KeepAlive | TEMPLATEs + `MAC-APPLY.md` + gated `scripts/mac-apply.sh` |
| Box-side retry protocol | `BOX-SIDE-RETRY-PROTOCOL.md` (ceiling 3) |
| One-time commission ≠ routine Matt | `BOOTSTRAP-PARADOX.md` |

**Unblocks A-class** after first successful MAC-APPLY + PROVE-MATRIX ×2.

---

## Tier 1 — preferred OOB (Owner must provision once)

| Option | What | Why preferred | Link does NOT |
|--------|------|---------------|---------------|
| **A. SSH key Studio←box** | `box` ed25519 + Studio `~/.ssh/authorized_keys` (user `wolfterminal`), optional `Match` limit | Survives Grok Bot GUI death; can `launchctl kickstart` / copy plists | Mint keys without Owner; broaden seats |
| **B. Managed Tailscale + SSH** | Studio + box on same TS ACL; SSH over TS IP | Works off LAN; Ethernet-primary still stands | Touch Tailscale without Owner; invent IPs |
| **C. Existing jump / bastion** | Documented host with Studio reach | Reuse infra | Invent bastion |

Any Tier-1 live path gets recorded in `ACTUATOR-AUDIT.md` Results table → status **PRESENT** with prove command.

---

## Tier 2 — weaker / conditional

| Option | Note |
|--------|------|
| Second Mac / always-on agent host | Only if Owner adds machine; not invent |
| Vendor headless local-exec API | Unknown; leave local-exec plist `REPLACE_ME` until proved |
| MDM/script push | Only if Owner MDM already covers Studio |

---

## Explicit non-options (defect if used as recovery)

- Ask Matt open Grok Bot / Cmd-Q / pkill / reconnect card
- Update Grok Bot / Reset Peaches computer
- Reboot / power-cycle advice as routine
- Fake GREEN from ListMachines process list alone

---

## Decision ask (Owner via Peaches — not Matt restart)

When Peaches wants to break `BLOCKED_NEEDS_ACTUATOR` without waiting for accidental GREEN:

1. Approve **Tier 1A or 1B** once, **or**
2. Accept wait for opportunistic GREEN → Link runs `MAC-APPLY` immediately (no Matt ritual)

Link will not ping Matt for open-app. Link will ping Peaches on verified Shell `PROVE_OK` or true B-class only.

---

## Link watch while blocked

- Heartbeat: at most **one** ListMachines+Shell probe per Peaches recheck / OWN tick (no multi-retry past ceiling)
- Design-continue: MAC-APPLY pack, this options doc, GREEN-wake detector script on box
- Factory pipe-dependent: stay parked
