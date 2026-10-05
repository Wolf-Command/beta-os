# TRANSFER-GATEKEEPER-EVENTBUS-PEPTIDE-HOLDINGS-PIPELINE-SPEC — P0 RESET pack

Generated: 2026-09-30T11:30:00+08:00 (WITA)  
Owner oversight: **Matthew** · Executor: Peaches  
Constraint: **PARTIAL honesty** · `staff_ready=false` · never claim REBUILT+PROVEN · no prod :8787 · no Exit Report  
Owner-only: Peptide Schedule · HOLDINGS-PERSONAL  
Forbidden: fake live sync · invent holdings · invent competitor rates · Gatekeeper auto-send · Event Bus rewrite · unpark rate-calendar LaunchAgents without Owner

## Purpose

Clear remaining MISSING non-HR from TRANSFER-BACKLOG (Gatekeeper · Event Bus · Peptide · Holdings · Competitor Rates Pipeline · Rate Calendar DB · Calendly Atrium Sync) as **PARTIAL** Beta surfaces. Prefer existing Owner Fitness/Trading for Peptide/Holdings. Pipeline trio = honesty stubs with V1 SoT + blockers only.

## 1) Gatekeeper

| Item | Value |
|------|-------|
| V1 SoT | `WolfCommand/01-Wolf-Command/Gatekeeper/` (daily triage MD) · `scripts/aios_gatekeeper.py` · `com.wolfcommand.aios-gatekeeper` (06:15 daily) |
| Canonical Beta | `/owner/gatekeeper` |
| HTML | `dashboards/owner-gatekeeper-1.html` |
| IA | HOME "Gatekeeper (Owner)" key=`owner_gatekeeper` |
| Authz | Owner only |
| Forbidden | Auto-send · create Gmail drafts without Owner opt-in · touch prod :8787 |
| migration_state | **PARTIAL** |
| Honesty | NEVER sends. Draft-only / Telegram review table. Multi-inbox (11) still follow-on. |

## 2) Event Bus

| Item | Value |
|------|-------|
| V1 SoT | `~/.openclaw/state/event_bus.db` · `scripts/event_bus_consumer.py` · `com.wolfcommand.event-bus` (KeepAlive) |
| Canonical Beta | `/ops/event-bus` |
| HTML | `dashboards/ops-event-bus-1.html` |
| IA | SYSTEM "Event Bus (ops)" key=`ops_event_bus` |
| Authz | Owner / SYSTEM |
| Forbidden | Rebuild consumer on Beta · fake live event stream UI · touch prod |
| migration_state | **PARTIAL** |
| Honesty | LaunchAgent health stamp only — DB remains on V1 path. |

## 3) Peptide Schedule

| Item | Value |
|------|-------|
| V1 SoT | `~/peptide_schedule_update.gs` · `dashboards/data/spartacus-peptides.json` · `workout_peptides.py` |
| Canonical Beta | `/owner/fitness` (deepen existing; alias `/owner/peptide` → fitness) |
| Authz | **Owner only** (personal health) |
| Forbidden | Staff Fitness product · invent injection log · claim Sheets vs JSON winner without Owner |
| migration_state | **PARTIAL** |
| Honesty | Both Sheets script + local JSON present (JSON mtime 2026-08-22). SoT confirmation = remaining Owner work. |

## 4) HOLDINGS-PERSONAL Registry

| Item | Value |
|------|-------|
| V1 SoT | `System-Registry/HOLDINGS-PERSONAL.md` (BTC stub · Peaches morning glance · Sterling owns group books) |
| Canonical Beta | `/owner/trading` (deepen existing; alias `/owner/holdings` → trading) |
| Authz | **Owner only** |
| Forbidden | Invent holdings lines · trades from this file · live broker |
| migration_state | **PARTIAL** |

## 5–7) Pipeline trio (honesty stubs — no fake live sync)

### Competitor Rates Pipeline
| V1 SoT | `~/.openclaw/data/competitor-rates.db` · `com.wolfcommand.competitor-rates` (+ digest) · `competitor_scraper.py` · feeds Kuta Rates board |
| Beta | `/ops/competitor-rates-pipeline` |
| Blockers | Atrium scrape SSL timeout observed 2026-09-30 03:09 · `competitor_rates`/`rate_signals` tables empty · board UI not re-hosted · no invent ADR |

### Rate Calendar DB
| V1 SoT | `~/.openclaw/data/rate-calendar.db` · LaunchAgents **parked** `*.parked-20260820-tg-mute` |
| Beta | `/ops/rate-calendar` |
| Blockers | Agents parked (tg-mute) · no Beta write path · no unpark without Owner |

### Calendly Atrium Sync
| V1 SoT | `com.wolfcommand.calendly-atrium-sync` · `calendly-atrium-sync.py` · `credentials/calendly.json` |
| Beta | `/ops/calendly-atrium-sync` |
| Blockers | V1 poll still on Mac (0 new bookings recent) · Beta has **no** live sync wire · no fake booking feed |

## Transfer steps

1. Ship PARTIAL honesty boards + deepen Fitness/Trading for Peptide/Holdings.
2. Alias legacy / discoverability URLs → canonicals.
3. IA + ROUTE_PARENT/CRUMBS + AUDIENCE + serve_beta path rewrite.
4. Backlog items 4,5,15–19 → `migration_state=PARTIAL`.
5. Local HTTP prove on Beta :8788; kickstart LaunchAgent. **Do not touch prod :8787.**
6. Human prove later — claim stays NOT REBUILT+PROVEN.

## Non-goals

- HR · Exit Report · staff_ready · REBUILT+PROVEN
- Unparking rate-calendar · rebuilding scraper on Beta · Gatekeeper send
- Inventing holdings or competitor figures
