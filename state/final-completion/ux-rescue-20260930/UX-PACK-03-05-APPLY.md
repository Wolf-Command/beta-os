# UX-PACK-03 + UX-PACK-04 + UX-PACK-05 APPLY

**Status:** PACK_03_05_APPLIED · 2026-09-30T22:08:28+08:00 (WITA)  
**Bound:** Beta :8788 only · Prod :8787 READ-ONLY untouched  
**Finance SoD:** unchanged · staff_ready=false

## Applied
- **UX-PACK-03** — Uma Blu one desk URL with tabs (Today/Bills/Issues/Petty/Evidence/Exceptions/Recipes/Real/Close); PR under Bills; Real route 
- **UX-PACK-04** — AMG hub tabs: Day Ops / Journey / Packages / OCC / Kuta Rates (Finance stays EMPTY on ops desk). GGV hub tabs: Pipeline / Strategy / Social (Finance live link unchanged)
- **UX-PACK-05** — Owner Trading RO paper desk cards (Holdings / Journal / TTC paper) via existing  (+ history)

## URLs
- Uma desk: https://beta.wolfcommand.net/bzg/uma-blu
- AMG hub: https://beta.wolfcommand.net/amg-ops-pack
- GGV hub: https://beta.wolfcommand.net/ggv-ops-pack
- Trading: https://beta.wolfcommand.net/owner/trading
- Local: http://127.0.0.1:8788/{bzg/uma-blu,amg-ops-pack,ggv-ops-pack,owner/trading}

## Files changed
-  (8) ·  ·  · 
-  ·  · 

Backup: 

## Finance SoD
- AMG grammar finance remains EMPTY (no href) on ops hub
- GGV finance remains  live — auth matrices not edited
- No FC seat grants · no money paths opened

## Residuals (Pack 05 partial honesty)
- V1 research tiles (filings/earnings/sector/…) not ported
- RO only — no holdings write / no broker
- Screenshots still BLOCKED_AUTH without Owner CF session

## Next packs
UX-PACK-06 (Fitness RO) · UX-PACK-07 (Personal Command + Radar) · UX-PACK-08 (My Work + screenshots)

## Matt paragraph
Uma Blu is now one desk (/bzg/uma-blu) with chrome tabs for Bills/Issues/Petty/Evidence/Exceptions/Recipes/Real/Close. AMG hub tabs now reach Day Ops, Journey, Packages, OCC, and Kuta Rates without opening hotel Finance (SoD still EMPTY on that desk). GGV hub tabs now reach Pipeline, Strategy, and Social; Finance link unchanged and still gated. Owner Trading (/owner/trading) is a PARTIAL RO paper desk with Holdings, Journal, and TTC paper cards from /api/owner/trading-ro — no broker, staff_ready stays false. Prod :8787 untouched. Next: Fitness RO (06), Personal Command + Radar stub (07), My Work depth + Owner screenshots (08).
