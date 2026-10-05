# TRANSFER-TRADING-SPEC — Beta Owner Trading (P0)

Generated: 2026-09-30T10:54:34+08:00 (WITA)  
Owner: **Matthew only** · Executor: Peaches  
Constraint: **NO live broker** · paper quant OK · `staff_ready=false` · never claim REBUILT+PROVEN · no prod :8787 · no Exit Report

## Purpose

Restore Owner Trading as a first-class Beta Owner surface so it is **not** Wave-8 soft-redirect retired into Empire. Preserve V1 provenance. Migration stays **PARTIAL** until human prove.

## V1 inventory (source of truth)

| Asset | Path | Notes |
|-------|------|-------|
| Board | `/Users/wolfterminal/.openclaw/workspace/wolf-system/dashboards/trading.html` | live=true, access=wolf; "Paper only. Nothing trades." |
| Desk | `/Users/wolfterminal/.openclaw/workspace/wolf-system/trading-desk/` | README, QUANT_PROGRAM.md, PAPER_QUANT_PRACTICE_BRIEF.md, journal.jsonl (3 lines), files/ screenshot |
| JS | `/Users/wolfterminal/.openclaw/workspace/wolf-system/dashboards/assets/trading-desk.js` | V1 cockpit |
| API | V1 `/api/trading` | holdings + journal; POST auto-journal historically 409 |
| Quant | Flint TTC | PAPER ONLY — QUANT_PROGRAM.md; trading_alerts NOT LIVE |
| Manifest | `dashboards/data/manifest.json` | name=trading live=true |
| Beta Wave-8 | `wolf_shell.SPECIALIST_*` + sidenav `HIDDEN_SPECIALIST_PRIMARY` | soft-redirect → /wolf (must reverse for Owner Trading) |

## Beta target (Owner-only)

| Item | Value |
|------|-------|
| Canonical route | `/owner/trading` |
| HTML | `~/beta-os/dashboards/owner-trading-1.html` |
| Legacy aliases | `/trading`, `/trading.html`, `/dashboards/trading.html` → `/owner/trading` (not Empire) |
| IA | HOME section, Owner-visible; key=`owner_trading` (not specialist slug leak) |
| Audience | Owner / Matthew only via whoami — staff must not see as primary |
| migration_state | **PARTIAL** |
| staff_ready | **false** |
| live broker | **FORBIDDEN** — banner + code refuse |
| paper quant | OK to surface as read-only program brief / journal summary |

## Transfer steps

1. **Un-retire chrome**: remove `trading` from Wave-8 `SPECIALIST_PRIMARY_SLUGS`, `SPECIALIST_PRIMARY_KEYS`, `SPECIALIST_SOFT_REDIRECT_PATHS`, and sidenav `HIDDEN_SPECIALIST_PRIMARY`.
2. **Canonical Owner board**: ship `owner-trading-1.html` with honesty strip (PARTIAL · paper only · no live broker · provenance paths).
3. **Route map**: alias legacy trading URLs → `/owner/trading`; register PARENT crumb under Empire.
4. **IA**: add HOME item "Trading (Owner)" → `/owner/trading` with key `owner_trading`.
5. **Data**: prefer read-only mirrors / explicit "V1 SoT still live" stamps. Do **not** invent holdings. Journal/holdings UNKNOWN is honest.
6. **Quant**: link/copy PAPER_QUANT + QUANT_PROGRAM as Owner docs under beta state; no execution hooks.
7. **Prove gate (human)**: Matthew opens `/owner/trading` authenticated; confirms paper-only; confirms no soft-redirect to Empire. Until then migration_state stays PARTIAL.

## Non-goals

- Live exchange/broker keys, order routing, auto-trade alerts LIVE
- Staff Trading desk
- Claiming REBUILT+PROVEN or staff_ready

## Honesty / provenance

- V1 board + trading-desk remain authoritative until Beta prove.
- Wave-8 "hidden ≠ deleted" preserved as history; Owner surface is the re-entry.
- Flint reserved architecture for live trading stays refused.
