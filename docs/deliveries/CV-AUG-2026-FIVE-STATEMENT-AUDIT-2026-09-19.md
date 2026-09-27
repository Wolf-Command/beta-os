# CV Aug 2026 — five-statement audit

**As of:** 2026-09-19T09:22:26+08:00 WITA
**PDFs (Matt 19 Sep):** filed as `KAS/PPL/CKM/FRJ/PLI-*-2026-08-CIMB-E-Statement.pdf` under `atrium/statements/` + `~/.openclaw/state/bank/_cimb-cv-archive/`.
**Parse:** `atrium/archive/parsed-aug-2026-from-matt.json` — 89 lines, all balance chains OK.
**Ledger + dash:** `atrium_sales.sqlite` updated; `dashboards/atrium-sales.html` rebuilt.

## Per CV

| CV | Account | Opening | Closing (last line) | #txns |
|----|---------|--------:|--------------------:|------:|
| Karya Anak Sasak | 800203745100 | 2,288,260,441.00 | 19,843,056.48 | 11 |
| Pasir Putih | 800203720100 | 54,989,428.00 | 11,586,014.78 | 17 |
| Cipta Karya Mandalika | 800203739400 | 3,242,842.23 | 3,222,842.23 | 1 |
| Fortuna Rinjani | 800203718200 | 620,985,519.21 | 71,119,682.67 | 54 |
| Pesona Lombok | 800203774400 | 140,577,962.23 | 111,694,007.76 | 6 |

### Roll-up (parse)
- Total credits: Rp 2,773,814
- Total debits: Rp 2,893,364,403

## Notable
- **Karya Anak Sasak** opening ~Rp 2.29bn → heavy Aug outflow (~Rp 2.27bn debits).
- **Fortuna Rinjani** carries Aug Sajidd Steel kitchen/bar/ice-maker paydowns.
- **Cipta Karya** quiet Aug (1 fee line only).

## Sajidd
Principal total across history in ledger: **Rp 550,353,075** — full table in `CV-SAJIDD-STEEL-PAYMENT-BREAKDOWN-2026-09-19.md`.

## Gaps
- Google Sheet CV master / Drive re-sync not run this pass (operator dash = atrium-sales.html).
- `load_statements.py` missing.json bug remains — FIX later if needed.
