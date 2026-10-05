# Uma Blu close — shift ended before Wolf finished (4 Oct 2026)

**Date:** 2026-10-04  
**Close:** `VDC-64f5f529-5485-4ff1-a0cc-11941a64e6f5`  
**Outlet:** BZG-UMA (Uma Blu)  
**Business date:** 2026-10-04  

## What happened

Iza (PERS-IZA) opened and started the 4 October Uma Blu daily close during her shift. ESB snapshot and petty cash OUT links were captured, but workflow defects (photo upload auth on local HTTP without Cloudflare JWT, incomplete close path before shift end) stopped her from finishing before her shift ended.

## Classification

**Human commissioning fail — not a staff pass.**

Even if the Owner later submits this close, the original closer did not complete a commissioned close during her shift. Wolf did not let the real close finish in time for the closer on duty.

## Preserved

- Same close id, business date, outlet
- Iza's entries, ESB snapshot, petty links, timestamps
- `declared_cash_amount` remains NULL until a physical cash count is entered

## Owner takeover

Matt (PERS-MATT) took over via governed `venue.close.reassign` permission — not a hardcoded email, not a Peaches step. Reason recorded: *Iza shift ended / Owner takeover after workflow failure*.

## Result artifact

`state/reliability/UMA-CLOSE-4OCT-TAKEOVER-RESULT-2026-10-04.json`
