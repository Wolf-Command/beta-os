# CONTENT ENGINE UX — Owner commissioning evidence — 2026-09-24

**Status:** `HUMAN_FEEDBACK_RECEIVED` → `ENGINEERING_IN_FLIGHT`  
**staff_ready:** **false** (must stay false)  
**Owner:** Matthew Goss · **Staff subject:** Haikal · **Surface:** Beta `/content-2.0` · :8788  
**Recorded:** 2026-09-24 09:18 WITA  
**Run:** `BF-content-engine-staff-ux-20260924`  
**Prod:** untouched (:8787 PID sacred)

## Commissioning class
P0 human commissioning under Credit Conservation. Heavy pack **allowed** as exception (human feedback fix / staff UX redesign). Not breadth. Not operator-depth auto-chain.

## Screenshot attachments
**None in this chat turn.** Owner issued the redesign in text. Executor did **not** invent screenshot files.

Prior related text / checklist paths on Mac (linked, not re-invented as screenshots):

- `docs/deliveries/HAIKAL-BETA-CONTENT-FEEDBACK-2026-09-17.md` — Haikal keep/upload unchanged; Wave1 plan titles, headers, library search, select all/deselect, brand tint
- `docs/deliveries/HAIKAL-UX-WAVE1-BETA-2026-09-19.md` — Wave1 prove notes
- `docs/deliveries/GROK-REVIEW-P0-SMART-UPLOAD-DETAIL-d147739-2026-09-22.md` — Smart Upload detail regression; Haikal RETEST still required **after** this UX redesign
- `docs/deliveries/WOLF-HAIKAL-NAS-LIBRARY-RETEST-CHECKLIST-2026-09-22.md` — NAS library human loop
- No `*screenshot*` / Smart-Upload PNG/JPG feedback files found under beta-os (search 2026-09-24)

## Matt Owner design test (text — non-negotiable)
Staff flow: **PLAN → UPLOAD → FIND → PREVIEW → SELECT → DOWNLOAD**  
Primary Haikal nav: **CONTENT PLAN | LIBRARY | UPLOAD | WOLF INTELLIGENCE** (+ brand/context selector)  
Remove engineering language from staff UI (Operator depth, proven=/ready=/staff_ready=, human fake, NAS destroy, CR/AU states, capability maturity, connective, implementation/test commentary).  
Library: search-first large search; filters only real metadata; More filters for advanced; thumbnail grid; select all/deselect/count/download (+ZIP); download progress; upload lifecycle Uploading→Processing→Saving to Library→Complete; empty human; preview clean; Content Plan = content team plan not Wolf dashboard; Wolf Intelligence = assist without AKR/Decision Memory exposure.  
Permissions server-side. Hidden ≠ security. Mobile+desktop. Beta only.

## Haikal prior feedback TEXT (attached by reference)
From `HAIKAL-BETA-CONTENT-FEEDBACK-2026-09-17.md`:

- Keep Upload page + Smart Upload: no change (Wave1) — **superseded for this P0 only where Owner now requires upload lifecycle progress honesty and staff chrome cleanup; do not rip Smart Upload core.**
- Plan title human format; short human headers; post/story status on list; Library Select all / Deselect all; brand colour tint; Library search revamp (big search + brand filter; Detailed filters accordion).
- Later: not ready for unsupervised team use until features actually work.

## Status machine
| From | To | When |
|------|-----|------|
| (open) | HUMAN_FEEDBACK_RECEIVED | Owner P0 ~09:15 WITA 24 Sep 2026 |
| HUMAN_FEEDBACK_RECEIVED | ENGINEERING_IN_FLIGHT | RULE+GATE+SPEC+factory arm `BF-content-engine-staff-ux-20260924` |
| ENGINEERING_IN_FLIGHT | ENGINEERING_PASS (candidate) | Peaches verify FAIL=0 — **still staff_ready=false** |
| * | HAİKAL_RETEST_REQUIRED | After engineering pass |
| * | STAFF_READY | **Forbidden** until separate Haikal PASS + Owner accept |

## Nine Owner acceptance questions (Haikal answers without Wolf architecture)
1. Where is this brand’s content plan?
2. How do I upload new media?
3. How do I find an asset I already have?
4. How do I preview it?
5. How do I select one or many?
6. How do I download / ZIP what I selected?
7. How do I see upload progress through to Library?
8. How do I switch brand/context?
9. Where do I ask Wolf for help on content work?

## Locks
- No fake STAFF READY
- No new agents
- No prod mutation
- Smart Upload detail retest **follows** this redesign

## Factory close 2026-09-24 09:43 WITA
- BF-content-engine-staff-ux-20260924 **DONE ENGINEERING_PASS** PASS=48 FAIL=0 (wave1 PASS=21).
- Peaches independent verify PASS. staff_ready=**false**. CAP **SPECIFIED**.
- **Haikal RETEST REQUIRED** next. Smart Upload retest follows.
- Credit Conservation: no auto-arm breadth.

## Owner human override — 2026-09-24 12:59 WITA
Haikal REAL commissioning recorded in `state/commissioning/CONTENT-ENGINE-HAIKAL-2026-09-24.md`.

**HUMAN COMMISSIONING = FAILED / RETEST REQUIRED · staff_ready=false**

Prior `BF-content-engine-staff-ux-20260924` ENGINEERING_PASS is overridden for staff_ready. Repair pack `BF-content-engine-haikal-fail-repair-20260924`. Do not mark Haikal CE cards PASS.
