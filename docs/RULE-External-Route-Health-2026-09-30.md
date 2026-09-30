# RULE — External Route Health — 2026-09-30

**Status:** LOCKED (P0 after CF Host Error 502 on Beta finance)  
**Scope:** Beta only. Never prod `:8787`. Never weaken auth.  
**Flags:** `staff_ready=false` · `human_commissioned=false`

## Incident law

Atrium Finance sidecar `:8790` down unsupervised → Beta `atrium_full_mount` returns
`sidecar_unavailable` 502 → Cloudflare **Host Error**. Local shell health alone
is **not** full recovery. External HTTPS route class must match service truth.

## Probe command (Operator desk / reliability watches)

```bash
export PATH="/usr/bin:/bin:/opt/homebrew/bin:$PATH"
cd /Users/wolfterminal/beta-os
python3 scripts/ops/external_route_health_tick.py --json
```

Plain one-liner for watches:

```bash
python3 /Users/wolfterminal/beta-os/scripts/ops/external_route_health_tick.py
```

Exit codes: `0` = not RED · `2` = RED CRITICAL.

## Critical routes

- `https://beta.wolfcommand.net/amg/finance`
- `https://beta.wolfcommand.net/bzg/finance`
- `https://beta.wolfcommand.net/ggv/finance`

## Classification

| Observation | Class |
| --- | --- |
| Host Error / origin 502 / `sidecar_unavailable` / connection refused | **RED CRITICAL** |
| CF Access 302/challenge without Host Error | **ORIGIN_REACHABLE** (amber; unauth probe; not RED) |
| 200 HTML after valid auth | **GREEN** |

Also probes local Host Error deps: `:8788` listen, `:8790 /api/health`,
`cloudflared` tunnel process, LaunchAgent `net.wolfcommand.atrium-finance-sidecar`.

## Safe autorecovery

If `:8790` is down **and** LaunchAgent plist exists:

```bash
launchctl kickstart -k gui/$(id -u)/net.wolfcommand.atrium-finance-sidecar
```

Log: `state/build-factory/logs/external-route-health-autorecover.jsonl`  
Never kill unrelated processes. Never touch prod.

## Owner / War Room

Material RED surfaces into Owner operational exceptions (`kind=external_route`)
with dedupe: alert event on transition to RED; sustained RED stays open without
spam. Cleared when class leaves RED.

State:

- `state/ops/external-route-health-latest.json`
- `state/ops/external-route-health-alert.json`
- Evidence: `state/final-completion/p0-502/EXTERNAL-ROUTE-HEALTH-*.json`

## Reliability board

`RELIABILITY-1` includes `external_routes` surface from latest tick
(and can live-probe). Local lsof alone previously left a **service-truth gap**
for external Host Error — this RULE closes it.

## Related

- `scripts/core/external_route_health.py`
- `scripts/ops/external_route_health_tick.py`
- `scripts/core/reliability1.py`
- `scripts/core/owner_operational_exceptions.py`
- `scripts/serve_atrium_finance.sh`
- LaunchAgent `net.wolfcommand.atrium-finance-sidecar`
