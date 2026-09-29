# SOP-LESSON-LIVE-1 RESULT — SOP lesson board live honesty (human review required)

**As of:** 2026-09-30 ~03:53 WITA · **Branch:** `build/wolf-command-rebuild` (beta-os @ `b035e66` + pack WIP)  
**Ports:** Prod `:8787` pid **15975** READ-ONLY untouched · Beta test harness ephemeral  
**Flags:** `staff_ready=false` · `human_commissioned=false` · **No push** · **Did not start FIN-TAX-SHELL-1 / HEADCHEF / Exit Report**

## Decision / canon

Serves **FINAL_WOLF_COMPLETION_MISSION Phase 2 pack SOP-LESSON-LIVE-1** (armed after AMG-OCC-TRUTH-1 PASS_VERIFIED) plus **2026-09-19 PICK SOP Factory v1** and **2026-09-20 PICK CAP-INTEL-05**.  
Surfaces SOP factory lesson candidates **without auto-approve** and **without inventing a live catalog**. DEMO rows stay **DEMO / NOT LIVE STAFF ADOPTION**.  
Preserves **SOP-FACTORY-1** + **INTEL-LEARN-1**. Human APPROVE/DENY reuses `POST /api/sop/review-decision`.  
**Not PROVEN/READY.** CAP-INTEL-05 stays **SPECIFIED**.

## What landed

### 1) SOP lesson live-honesty board
- Page `/ops/sop-lesson-live` (`dashboards/sop-lesson-live.html`; aliases `/core/sop-lesson-live`, `/sop-lesson-live`)
- Live catalog `catalog/sop_factory.sqlite` **ABSENT** · `live_lesson_count=0` · nothing invented
- Factory DEMO candidates listed and labeled **DEMO / NOT LIVE STAFF ADOPTION**
- Human review queue **PENDING_REVIEW** · auto-approve off
- APPROVE/DENY posts to SOP factory `POST /api/sop/review-decision` (not this board)

### 2) Auth page + API
- API `GET /api/ops/sop-lesson-live` (alias `GET /api/sop/lesson-live`)
- Unsigned → **403** · Amanda → Access denied · Matt → DEMO queue + LIVE ABSENT
- POST auto-approve / invent-lesson → **403** (`auto_approve_refused` / `invent_lesson_refused`)
- Does not swallow `/api/sop/lesson-candidate`, `/api/sop/review-queue`, or `/api/intel/learning`

### 3) Honesty pins
| Pin | Value |
| --- | --- |
| Human review gate | **true** |
| Auto-approve / auto-approve lessons | **false** |
| Invented / fake lessons | **false** |
| Live catalog SOP | **ABSENT** · live_lesson_count **0** |
| DEMO is live adoption | **false** |
| SOP-FACTORY-1 / INTEL-LEARN-1 | **PRESERVED** |
| `staff_ready` / `human_commissioned` | **false** |
| CAP-INTEL-05 | **SPECIFIED** · ceiling **BUILT** |
| Next pack | **FIN-TAX-SHELL-1** (parent/Peaches only — Cursor did not auto-chain) |

## Tests

| Suite | Result |
| --- | --- |
| `scripts/tests/test_sop_lesson_live1_20260930.py` | **PASS=150 FAIL=0** |

Shots under `docs/wolf/ops/shots/`: `soplessonlive1-desk-desktop.png`, `soplessonlive1-desk-phone.png`, `soplessonlive1-live-absent.png`, `soplessonlive1-human-review.png`, `soplessonlive1-amanda-deny.png`, `soplessonlive1-unsigned-deny.png`.

## Files

- Core: `scripts/core/sop_lesson_live1.py`
- Serve: `scripts/serve_beta.py` (`_sop_lesson_live1_dispatch` / `_sop_lesson_live1_write_refused`)
- UI: `dashboards/sop-lesson-live.html`
- Shell crumbs/canonical: `scripts/core/wolf_shell.py`
- Tests: `scripts/tests/test_sop_lesson_live1_20260930.py`
- Stamp: `state/final-completion/packs/SOP-LESSON-LIVE-1-ARM.json`

## Out of scope (not started from this EXIT)

- **FIN-TAX-SHELL-1** (next — Peaches/parent arms after verify; Cursor must not auto-chain)
- Auto-approve lessons, fake lessons, inventing live catalog rows
- HEADCHEF / Exit Report / prod mutate / push / flipping commissioning flags
- Claiming CAP-INTEL-05 PROVEN/READY / live staff adoption

## EXIT

**EXIT:0**

`staff_ready=false` · `human_commissioned=false` · prod pid 15975 untouched · no push · did not auto-chain next pack.
