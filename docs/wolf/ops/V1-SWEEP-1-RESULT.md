# V1-SWEEP-1 RESULT — Non-HR V1 retirement / status sweep

**As of:** 2026-09-29 ~22:41 WITA · **Branch:** `build/wolf-command-rebuild` (beta-os @ `f35d61a` working tree) + atrium-finance `wolf/beta-mount-20260928` @ `1ecfc3c`  
**Ports:** Prod `:8787` pid **15975** READ-ONLY untouched · Beta `:8788` recycled for route load · Sidecar `:8790`  
**Flags:** `staff_ready=false` · `human_commissioned=false` · **No push** · **Did not start Rebuild Exit Report / HEADCHEF**

## Owner addendum (locked)

After Finance Core + BZG multi-outlet + non-HR V1 retirement finishes: **do NOT chain another major feature pack**. Next = **Rebuild Completion & Exit Report** only. Bug fixes + human commissioning OK.  
**This Cursor EXIT does not auto-start the Exit Report pack** — Peaches writes that report from evidence after verify.

## Decision / canon

Serves Matt-ordered Owner sprint **V1-SWEEP-1** (2026-09-29); inventory `state/finance-core-sprint/INVENTORY-20260929.json` §C + RULE-One-Finance-Product exit discipline (non-HR V1 retirement before Rebuild Exit Report).  
**Matt-ordered sprint overrides breadth veto / credit conservation for this pack.**

## What landed

### 1) Honest V1 status register
- `state/finance-core-sprint/V1-STATUS-REGISTER-20260929.json` — all **23** inventory ids classified with evidence path + Beta disposition.
- Beta surface: `/ops/v1-status` + `/api/ops/v1-status` (read-only).
- HR stays **HR-DEFERRED** / V1 — no HR retire/redirect.

| Class | Count |
| --- | ---: |
| SUPERSEDED | 3 |
| HISTORICAL ONLY | 5 |
| MOUNTED READ-ONLY | 6 |
| REBUILT IN WOLF | 4 |
| HR-DEFERRED | 1 |
| BLOCKED | 2 |
| DISCOVER-NEEDED | 2 |

### 2) Safe Beta redirects (no V1 file deletes)
| From (Beta only) | To | Note |
| --- | --- | --- |
| `/atrium-finance`, `/atrium-finance.html`, `/dashboards/atrium-finance.html` | `/amg/finance` | SUPERSEDED board |
| `/bzg-finance`, `/bzg-finance.html`, `/dashboards/bzg-finance.html` | `/bzg/finance` | historical V1 board → Beta books shell |

- wolf-system V1 HTML/DBs **not deleted**.
- **MOUNTED READ-ONLY** remaining (no cutover): ESB, alchemist, V1 GGV money sqlite, V1 uma recipes, V1 GGV board, bank ingest.
- Xero + n8n-xero-bzg marked SUPERSEDED (do not revive).

### 3) Preserve Finance Core + BZG packs
Re-ran: CORE-BOOKS-1 / CORE-ENT-1 / BZG-OUTLET-1 — all pass (see Tests). SoD + books shells + outlet registry intact.

## Tests (honest)

| Suite | Result |
| --- | --- |
| `test_v1_sweep1_20260929.py` | **PASS=65 FAIL=0** (with RESULT present: re-check below) |
| `test_core_books1_20260929.py` | **pass=64 fail=0** |
| `test_core_ent1_20260929.py` | **pass=49 fail=0** |
| `test_bzg_outlet1_20260929.py` | **PASS=82 FAIL=0** |

## Shots

Under `docs/wolf/ops/shots/` (6/6):
- `v1sweep1-register-{desktop,phone}.png` — status register
- `v1sweep1-atrium-redirect-{desktop,phone}.png` — Beta `/amg/finance` destination
- `v1sweep1-bzg-redirect-{desktop,phone}.png` — Beta `/bzg/finance` destination

## Migration / files

- Register: `state/finance-core-sprint/V1-STATUS-REGISTER-20260929.json`
- Core: `scripts/core/v1_status_register.py`
- Redirects: `scripts/core/wolf_shell.py` (`V1_SUPERSEDED_BOARD_REDIRECTS`) + early do_GET in `scripts/serve_beta.py`
- UI: `dashboards/v1-status.html`
- Desk: `scripts/core/bzg_finance_desk.py` (aliases → 302; canonical `/bzg/finance` only)
- Tests: `scripts/tests/test_v1_sweep1_20260929.py`
- Shots: `scripts/audit/v1sweep1_shots.py`
- Stamp: `state/finance-core-sprint/V1-SWEEP-1-ARM.json`

## Remaining work (for Peaches Exit Report — not started here)

- Full verify pass after this EXIT
- **WOLF COMMAND Rebuild Completion & Exit Report** (Peaches writes from evidence)
- MOUNTED READ-ONLY SoR cutovers (ESB / alchemist / V1 GGV money / recipes) — Matt decision only
- DISCOVER-NEEDED: owner returns SoR, NAS finance crawl
- BLOCKED: money board, PMS accounting exports
- HR stays V1 until a separate HR decision
- Beta GGV invoice/nota + Uma ops shells still incomplete (honest)

## Out of scope (not started from this EXIT)

- Rebuild Exit Report feature pack (Peaches next)
- HEADCHEF / random breadth
- HR retirement
- Destructive ESB/alchemist/money DB cutover
- Prod / push / inventing people / flipping `staff_ready` / `human_commissioned` / money movement
