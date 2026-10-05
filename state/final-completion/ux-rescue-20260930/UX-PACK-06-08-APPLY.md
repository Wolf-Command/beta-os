# UX-PACK-06 + UX-PACK-07 + UX-PACK-08 APPLY

**Status:** PACK_06_08_APPLIED · 2026-09-30T22:19:43+08:00 (WITA)  
**Bound:** Beta :8788 only · Prod :8787 READ-ONLY untouched  
**Finance SoD:** unchanged · staff_ready=false

## Applied
- **UX-PACK-06** — Fitness RO desk parity (Today / Program / Training / Peptides) mirroring Trading; `/api/owner/fitness-ro` deepened with `today_day` + `today_plan`
- **UX-PACK-07** — PERSONAL IA group (Trading / Fitness / Radar); `/owner/radar` stub; Travel / Learning / Habitat Investment HIDE from primary IA (routes kept)
- **UX-PACK-08** — My Work plain queues (TODAY / DO THIS NEXT / NEEDS ATTENTION / WAITING / COMPLETED) → action screen; Owner Home Personal strip + fitness glance + pulse action links

## URLs
- Fitness: https://beta.wolfcommand.net/owner/fitness
- Radar: https://beta.wolfcommand.net/owner/radar
- Trading: https://beta.wolfcommand.net/owner/trading
- My Work: https://beta.wolfcommand.net/my-work
- Owner Home: https://beta.wolfcommand.net/owner-empire-pack
- Local: http://127.0.0.1:8788/{owner/fitness,owner/radar,owner/trading,my-work,owner-empire-pack}

## Files changed
- `owner-fitness-1.html` · `owner-radar-1.html` (new) · `owner-trading-1.html` (crumb) · `my-work.html` · `owner-empire-pack.html`
- `sidenav.js` · `wolf_shell.py` · `owner_fitness_ro.py` · `serve_beta.py`

Backup: `/Users/wolfterminal/beta-os/backups/ux-pack-06-08-20260930-221309`

## Desktop gate
**desktop_gate_ready = false**

Why: Owner Home pulse still weak vs V1 dense live tiles; screenshots still BLOCKED_AUTH (CF Access); Radar PARTIAL stub only; staff_ready false.

## Residuals
- Travel / Learning / Habitat Investment HIDE_UNTIL_USEFUL (URL kept)
- Telegram Spartacus unchanged
- Full V1 radar / Owner Home pulse parity incomplete
- Screenshots need Owner CF session

## Next work
Owner Home real SoT pulse tiles · authenticated screenshot pass · optional Travel/Learning RO desks · Radar deepen only if prioritized

## Matt paragraph
Fitness (/owner/fitness) is now a PARTIAL RO desk like Trading — Today, Program/plan, Training, and Peptides cards from /api/owner/fitness-ro (live Spartacus sqlite, Fitness ≠ HR, no writes). Personal Command is grouped under PERSONAL in the nav: Trading, Fitness, and a new Owner Radar stub (/owner/radar). Travel, Learning, and Habitat Investment stay reachable by URL but are hidden from primary IA until useful. My Work is simplified to TODAY / DO THIS NEXT / NEEDS ATTENTION / WAITING / COMPLETED with Open→do this links to the action screen; Owner Home gained a Personal Command strip plus a Fitness day glance and pulse cards that link to actions when hrefs exist. Prod :8787 untouched; finance SoD unchanged; staff_ready stays false. Desktop gate is NOT ready yet — Owner Home is still weak vs the V1 live pulse, and screenshots remain CF-blocked without your Owner session.
