# DEEPEN-FORENSIC-TF-20260930 — Trading / Fitness (+ Travel / Learning)

Generated: `2026-09-30T12:20:54+0800` (WITA) · Peaches · Mac Studio `36d8fa4b-…`  
Bound: **beta :8788** · prod :8787 **READ-ONLY** · staff_ready=false · no Exit Report · no live broker · no Spartacus writes · Fitness≠HR

## Trading (V1)

| Item | Detail |
|------|--------|
| Board | `dashboards/trading.html` + `assets/trading-desk.js` (395 lines) |
| Board API | `GET /api/trading` → `trading_desk.get_board()` |
| JS fetches | /api/trading/holdings, /api/trading/journal, /api/trading/journal/remove |
| Display | Holdings list · Trade journal rows (+ screenshot via `/api/trading/journal/file`) · TTC paper method · research NOT CHECKED tiles |
| Mutations (V1 only — **forbidden on Beta**) | POST holdings · POST journal · journal/remove · auto-journal |
| SoT | `trading-desk/journal.jsonl` · `QUANT_PROGRAM.md` · `PAPER_QUANT_PRACTICE_BRIEF.md` · `HOLDINGS-PERSONAL.md` |

**Beta before deepen:** `/api/owner/trading-ro` 200 V1_RO_OK but board `#ro-live` was JSON dump only → **PARTIAL ≠ LIVE_USABLE**.

## Fitness (V1)

| Item | Detail |
|------|--------|
| Board | `dashboards/spartacus.html` |
| APIs | `/api/spartacus`, `/api/spartacus/board` (+ POST board historically) |
| DB | `~/.openclaw/personal/health/spartacus.sqlite` mode=ro |
| Peptides | `dashboards/data/spartacus-peptides.json` (schedule meta) |
| Safe RO | counts · training_log date/lift · lift_sessions date/lift_key · peptide_log date/compound/status |
| Forbidden | PII dumps · Fitness=HR · DB writes |

**Beta before:** `/api/owner/fitness-ro` aggregates+recent workouts; board still JSON dump.

## Travel (V1)

| Item | Detail |
|------|--------|
| Board | `travel.html` — tiles: Europe, Vegas, Holiday ideas, In Lombok — Accor IDR nights, official, 20 Aug 2026, Fly-aways with party totals — Google Flights 20 Aug 2026, currency IDR, Talk to Peaches |
| Fetches | /api/peaches-desk, /whoami |
| Law | **Nobody books from here.** No booking API. Party: 2 adults + kids 5 & 7. |
| Beta before | stamp-only `owner-travel-1.html` · no RO API |

## Learning (V1)

| Item | Detail |
|------|--------|
| Board | `learning.html` + `learning-desk.js` |
| API | `GET /api/learning` → tracks + items |
| JS | /api/learning, /api/learning/file, /api/learning/research, /api/learning/start |
| State | `state/learning-desk/` tracks · inbox · ttc-learn-base |
| Law | TTC **paper only** · nothing trades · ≠ `/intel/learning` |
| Beta before | stamp-only · no RO API |

## Deepen targets (this pack)

1. Trading RO: journal history cap · holdings honesty · QUANT/PAPER excerpts · usable board UI
2. Fitness RO: peptide schedule + recent lifts UI
3. Travel + Learning: same RO pattern as trading-ro
4. Mechanical prove only → mark **API_USABLE** / **BOARD_DATA_WIRED** — never LIVE_USABLE without human prove
