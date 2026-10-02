# CURSOR PACK — BZG-CLOSE-OWNER-CONTROL-ESB-RECON-1 (P0)

**Owner drain** · tip parent `d4f8f1e` · **NO push** · prod `:8787` READ-ONLY · Peaches credit-light

## A) Canonical OWNER CONTROL / BREAK GLASS (Wolf-wide start + Daily Close now)
- Matt Owner authority from **Owner Assignment** (ROLE-MATT / PERS-MATT) — NOT hardcoded email.
- Product UI Owner actions (no chat/Peaches/engineering required): take over, reassign, reopen, cancel workflow, unlock abandoned, correct assignment, override operational lock, return for correction — **audited**.
- Every Owner intervention: previous state, new state, action, actor Matt, timestamp, reason, entity/business, before/after evidence. No silent mutation; no audit deletion.
- Reversible ops controls ≠ money movement / irreversible bank execution (keep separated).
- Audit major workflows for “Can Matt take control from UI?” — start with **BZG Daily Close**; stamp a Wolf-wide Owner-control gap register for Finance/Content/My Work/approvals/integrations (honest PARTIAL list OK if not all implemented tonight).

## B) ESB dual-source reconciliation (tonight Uma commissioning FAIL)
Live Beta: bills **61**, cash **Rp 2,855,000**. Printed closing receipt 02 Oct 2026: bills **58**, cash **Rp 2,735,000**, pax 103, net/service/tax/gross as Owner listed; payments by bank EDC+QRIS + non-bank lines totaling Rp 18,395,000.

**Do NOT** change Beta to match receipt. Trace exact semantic difference (date boundary, TZ, status, late/reopen/void/cancel, non-sales lines, settlement cut-off, aggregation, warehouse pull time, API table). Stamp forensic RESULT.

UI must show **both**:
- LIVE ESB OPERATIONAL DATA
- ESB END OF DAY CLOSING RECEIPT (photo → vision draft → confirm/edit; preserve image)
- Difference board (bills/cash/payments) explained or flagged — never overwrite sources.

Payment mapping: EDC and QRIS **separate by bank** (BNI/Mandiri etc.) + other categories.

Tonight close (Matt taken over) is the commissioning case after deploy. `staff_ready=false` until dual-source recon works; Daily Close NOT commissioned.

Reusable BZG engine; outlet bank config location-specific.

## Exit
RESULT + forensic stamp under `state/bzg-daily-close/`. Tests. Restart `:8788`. EXIT:0 tip. Do not claim Matt-ready — Peaches verifies then one ping.
