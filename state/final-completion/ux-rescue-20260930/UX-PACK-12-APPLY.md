# UX-PACK-12 APPLY — Radar deepen + Owner Home polish
**Status:** PACK_12_APPLIED_PARTIAL · 2026-09-30T22:46:43+08:00 (WITA)
**Bound:** Beta :8788 only · Prod :8787 READ-ONLY untouched
**finance_sod_unchanged:** true · **staff_ready:** false · **desktop_gate_ready:** false

## A) Owner Radar
- New RO API `/api/owner/radar-ro` (local Beta, same family as pulse-ro)
- `/owner/radar` deepened: What matters tonight · This week (12WY/Mars/wire) · Honesty · board links
- Counts: {"tiles": 15, "LIVE": 1, "PARTIAL": 3, "EMPTY": 4, "BLOCKED": 7}
- Honesty: EMPTY/BLOCKED stay loud · no invented Mars meter / 12WY % / engagement

## B) Owner Home polish
- Needs You CTA → `/owner/needs-you-1` (+ staff-ops secondary)
- Exceptions / Needs You glance strip from radar-ro (click → action)
- Pulse strip + FINISH WOLF + My Work + Personal preserved/coherent
- Desktop denser (1360 / 4-col pulse / 3-col personal / line-clamp) — not stretched-mobile
- No fake pulse LIVE invent

## Files
- `scripts/core/owner_radar_ro.py` (new)
- `scripts/serve_beta.py` (mount radar-ro)
- `dashboards/owner-radar-1.html`
- `dashboards/owner-empire-pack.html`

## Backup
`/Users/wolfterminal/beta-os/backups/ux-pack-12-20260930-224358`

## Residuals
- 12WY score EMPTY · Mars meter EMPTY · wire engagement NOT live
- Pulse: occ BLOCKED · Uma EMPTY · leads DEMO · backup STALE/AMBER
- Screenshots BLOCKED_AUTH until Owner CF (PACK-10)
- Not V1 full radar feature dump

## Next
- UX-PACK-10 authenticated screenshot pass (BLOCKED until Owner CF — do not fake)

## Matt
UX-PACK-12 landed on Beta: Owner Radar (/owner/radar) is no longer an empty stub — it is a PARTIAL RO desk with tonight cards (pulse occ/kuta/Uma/backup + blocked exceptions + Needs You connective), this-week boards (12WY Week 4 score EMPTY not 0%, Mars meter EMPTY, Metricool wire PARTIAL brands=6 engagement NOT live), and honesty stamps linking into real desks. Owner Home got denser desktop layout, plain-language Needs You → /owner/needs-you-1, and an Exceptions/Needs You glance strip (one hop to act) while Pulse + FINISH WOLF + Personal stay coherent. Prod :8787 untouched; finance SoD unchanged; staff_ready false; desktop_gate_ready still false. Next remains UX-PACK-10 authenticated screenshots when you open Owner CF Access — do not fake shots.
