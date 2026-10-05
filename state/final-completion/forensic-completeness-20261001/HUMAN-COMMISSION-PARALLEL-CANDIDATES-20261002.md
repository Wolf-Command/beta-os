# Human commissioning — parallel candidates (2 Oct 2026)

All packs below are **eng-proved** with `staff_ready=false` / `human_proven=false`. Goal: coherent **single-person** workflows in real staff hands while Cursor builds Atrium ops (Security in flight → Maint → Tours → Events).

**Matt is not the universal tester.** Owner may approve/decide where RBAC already requires `PERS-MATT` (e.g. Uma purchase approve) but click-paths and night loops should be staff-owned.

| Priority | Person | Eng pack(s) | Coherent workflow to commission | Gate conditions before handoff | Blocked if |
|---|---|---|---|---|---|
| 1 | **Haikal** | Content / Smart Upload (prior PEACHES verify) | Upload retest → library asset recognised | Already `PEACHES_VERIFY_PASS_AWAITING_HAIKAL` / human_retest ISSUED — **do not re-arm Cursor**; confirm Telegram/retest path only | Diverting him into Security/Maint UI |
| 2 | **Devi** (`PERS-DEVI`) | PACK-02 + WAVE2-01 | Uma receive → petty → night close; optional declared-cash evidence attach | Pack 02 eng chain exists (PR/receipt/petty/close ids); she holds `venue.receive` / `venue.close.submit`; **physical till count** required for declared-cash — do not invent amount; Matt only as **approver** on segregating step, not as primary operator | `org_authority_limits=0` for material amounts; Alchemist `cash_count` still 0 until she counts |
| 3 | **Zayen** | PACK-05 (+ PACK-10 seat checks) | Atrium finance SoD: submit close-review / approve as AMG-allowed seat; prove GGV deny | API entity isolation repaired (Zayen AMG/BZG yes, GGV no); CF/browser session for Zayen still open as UX gate | Treating Matt click as Zayen proof; Xero write (ABSENT — out of scope) |
| 4 | **Amanda** (`PERS-AMANDA`) | PACK-06 | GGV nota capture → issue one real client line | Pack 06 eng-proved on catalog copy; live `ggv_notas=0`; Issue blocked until **real** slip; Amanda GGV finance yes / AMG board read false | Inventing nota amount/supplier; phone commission still open (Matt+Amanda pair — schedule after first live capture) |
| 5 | **Misa** | PACK-04 | Habitat tick → draft/queue row (publish OFF) | Pack 04 eng-proved; Metricool WRITE off; queue `MISA-CBA83917AE23` pattern; draft-only commission OK | Enabling publish; Haikal upload FAIL without defect pack |

## Explicitly not ready for staff commission yet
- WAVE2 honesty desks (01–07): eng gap pages — **not** jobs. Declared-cash needs Devi till first.
- PACK-03 sales desk: read-only 14 views; no POST — commission would be “look only,” low value vs Devi/Amanda loops.
- PACK-07 guest stay / WAVE2-02 HK: UNAVAILABLE room status — wait Maint/HK workflow software.
- PACK-08 menu variance / WAVE2-04: contribution UNAVAILABLE — do not score invented margins.
- PACK-09 pre-open outlets: config-only; null sales by design.
- Atrium Security/Maint builds: eng-prove first; then name an AMG ops person (not Matt) for commission.

## First action this morning
Keep **Haikal upload retest** as the live parallel human track. Do not pull Matt into testing Security/Maint Cursor output.

## Feedback rule
- Human **FAIL** → open factory defect pack (named pack id).
- Human **PASS** → mark `HUMAN_PROVEN` for that slice only.
- Never flip global `staff_ready` until the bar for that desk is met.
- Do not count honesty UNAVAILABLE/UNJOINED/BROKEN UI as commissioned software.

## Evidence anchors
- Pack results: `~/beta-os/state/final-completion/forensic-completeness-20261001/PACK-{02,04,05,06,10}-*-RESULT.md`
- WAVE2: same dir `WAVE2-0N-*-RESULT.md`
- RBAC seats: PACK-10 / PACK-05 result tables (Devi/Zayen/Amanda)
