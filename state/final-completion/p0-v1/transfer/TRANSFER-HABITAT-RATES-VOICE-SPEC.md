# TRANSFER-HABITAT-RATES-VOICE-SPEC — Habitat Investment · Kuta Rates · Voice Boards (P0)

Generated: 2026-09-30T11:22:00+08:00 (WITA)  
Owner oversight: **Matthew** · Executor: Peaches  
Constraint: **PARTIAL honesty** · `staff_ready=false` · never claim REBUILT+PROVEN · no prod :8787 · no Exit Report  
Forbidden this pack: voice **send** / reply automation · competitor-rates **pipeline** rebuild · Gatekeeper · Event Bus · Peptide · Holdings · Calendly  

## Purpose

Restore next MISSING non-HR pack into Beta as Owner/AMG-reachable **PARTIAL** boards. Prefer existing V1 habitat-investment / kuta-rates / `*-voice` paths (aliases → canonical). Do **not** invent duplicate sprawl routes. Migration stays **PARTIAL** until human prove.

## 1) Habitat Investment 2026

| Item | Value |
|------|-------|
| V1 SoT | `~/.openclaw/workspace/wolf-system/dashboards/habitat-investment-2026.html` (+ bak prospectus variants on disk) |
| Canonical Beta | `/habitat-investment-2026` |
| HTML | `~/beta-os/dashboards/habitat-investment-1.html` |
| Historical aliases | `/habitat-investment`, `/habitat-investment/`, `/habitat-investment.html`, `/habitat-investment-2026.html`, `/habitat-investment-2026/`, `/dashboards/habitat-investment-2026.html`, `/habitat-investment-1.html`, `/dashboards/habitat-investment-1.html` → `/habitat-investment-2026` |
| IA | HOME "Habitat Investment (Owner)" key=`habitat_investment` |
| Authz | Owner oversight · GGV client-facing report provenance |
| Forbidden | Invent financials · claim live prospectus publish · touch prod :8787 |
| migration_state | **PARTIAL** |
| Note | V1 nav once dropped Investment **menu child** only — board file retained. Prefer existing `habitat-investment*` paths. |

## 2) Kuta Rates Competitor Board

| Item | Value |
|------|-------|
| V1 SoT | `dashboards/kuta-rates.html` · `data/kuta-rates.status.json` · `data/kuta-rates-brief-*.md` · `state/competitor-rates/` · competitor-rates.db (pipeline separate / skipped) |
| Canonical Beta | `/kuta-rates` |
| HTML | `~/beta-os/dashboards/kuta-rates-1.html` |
| Wave-8 change | **Re-enter** — remove from `SPECIALIST_SOFT_REDIRECT_*` / sidenav `HIDDEN_SPECIALIST_PRIMARY` (was Empire soft-land) |
| Historical aliases | `/kuta-rates/`, `/kuta-rates.html`, `/dashboards/kuta-rates.html`, `/kuta-rates-1.html`, `/dashboards/kuta-rates-1.html` → `/kuta-rates` |
| IA | BUSINESSES "Kuta Rates (AMG)" key=`kuta_rates` |
| Authz | Owner + SPECIALIST_AMG audience pages |
| Forbidden | Live booking · invent competitor rates · rebuild LaunchAgent pipeline this pack |
| migration_state | **PARTIAL** |
| Honesty | "Nobody books from here." Morning scan SoT remains V1 status/briefs until optional read-only mirror. |

## 3) AMG / BZG / GGV Voice Boards

| Item | Value |
|------|-------|
| V1 SoT | `amg-voice.html` · `bzg-voice.html` · `ggv-voice.html` + `amg_voice.py` / `bzg_voice.py` / `ggv_voice.py` · `state/*-voice-responses.jsonl` |
| Canonical Beta | `/amg-voice` · `/bzg-voice` · `/ggv-voice` |
| HTML | `amg-voice-1.html` · `bzg-voice-1.html` · `ggv-voice-1.html` |
| Historical aliases | `/{entity}-voice.html`, `/dashboards/{entity}-voice.html`, `/{entity}-voice-1.html`, trailing `/` → canonical |
| IA | BUSINESSES Voice (seat) items keys=`amg_voice` / `bzg_voice` / `ggv_voice` |
| Authz | Owner + matching SPECIALIST_AMG / OPERATOR(BZG) / SPECIALIST_GGV audience pages |
| Forbidden | **Do not send voice messages** · no reply automation · no Beta POST `/api/*/voice` wiring this pack |
| migration_state | **PARTIAL** |

## Transfer steps

1. Ship PARTIAL honesty boards (NOT REBUILT+PROVEN banners · V1 SoT paths · no pipeline / no voice send).
2. Alias legacy URLs → canonicals (not Empire soft-redirect for kuta-rates).
3. IA + sidenav + ROUTE_PARENT/CRUMBS + AUDIENCE_PAGES + serve_beta path rewrite.
4. Backlog items 12–14 → `migration_state=PARTIAL` with beta routes.
5. Local HTTP prove on Beta :8788; kickstart LaunchAgent if needed. **Do not touch prod :8787.**
6. Human prove later — until then claim stays NOT REBUILT+PROVEN.

## Non-goals

- Competitor Rates Pipeline / Rate Calendar DB / Calendly
- Gatekeeper · Event Bus · Peptide · Holdings · HR
- Rebuilding full V1 prospectus / rates grid / voice form POST on Beta
- Exit Report · staff_ready · REBUILT+PROVEN

## Honesty / provenance

- V1 HTML + status/briefs/jsonl remain authoritative until Beta human prove + optional read-only mirror.
- Kuta rates: competitor pipeline LaunchAgents **not** transferred this pack (backlog item remains NOT_STARTED).
- Voice: questionnaire capture stays on V1; Beta seats are honesty-only (no send).
