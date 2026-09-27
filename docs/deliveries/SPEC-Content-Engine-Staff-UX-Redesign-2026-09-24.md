# SPEC — Content Engine Staff UX Redesign — 2026-09-24

**Run:** `BF-content-engine-staff-ux-20260924`  
**Branch:** `build/wolf-command-rebuild` · soft head `f3ab8f7` (do not destroy uncommitted work)  
**Workspace:** `/Users/wolfterminal/beta-os` · Beta :8788 only  
**Prod:** :8787 sacred — **do not mutate**  
**RULE:** `docs/RULE-Content-Engine-Staff-UX-2026-09-24.md`  
**AUDIT:** `docs/deliveries/AUDIT-Content-Engine-Staff-Jargon-Leak-2026-09-24.md`  
**CR:** `state/completion-register/content-engine-staff-ux-20260924.json` · CAP **SPECIFIED** · **staff_ready=false**  
**Class:** Smallest coherent staff UX redesign. Human commissioning exception under Credit Conservation.  
**Recorded:** 2026-09-24 09:19 WITA

## Goal
Make Haikal’s Content Engine desk answerable as a content workflow — not an engineering console.

Staff flow: **PLAN → UPLOAD → FIND → PREVIEW → SELECT → DOWNLOAD**

## In scope (do these)

### 1. Staff primary nav — 4 tabs
On `/content-2.0` (and brand aliases into it):

- **CONTENT PLAN** | **LIBRARY** | **UPLOAD** | **WOLF INTELLIGENCE**
- Keep brand/context selector adjacent and obvious
- Demote global / Empire / Owner / Progress links to **visually secondary** chrome (smaller, quieter, not competing with the four tabs)
- Mobile + desktop

### 2. Strip engineering strings from staff surfaces (prefer shared fixes)
From staff-visible Content chrome (and shell audience `SPECIALIST_CONTENT` where shared):

Remove / stop rendering:

- Operator depth panels + copy on Library
- `proven=` / `ready=` / `staff_ready=` slogans
- “human fake” / “No Haikal” / “NAS destroy”
- CR- / AU- / SPECIFIED / ENGINEERING / connective as UI chrome
- Needs-You engineering strips as primary Library content
- **AKR** and **Decision Memory** grammar empties on the Content staff surface

Prefer: audience/page-type gates in `wolf_shell.py` + `content-2.0.html` shared sections over one-off string deletes that break Owner surfaces.

Owner/Progress/API may keep honesty flags. Staff UI must not.

### 3. Library — search-first + thumbnail grid + select/download + progress
- Large search is the hero
- Filters only for **real existing metadata**; advanced under **More filters** (rename from “Detailed filters” if needed — do **not** invent new metadata filters)
- Results = **thumbnail grid** (media hero)
- Select all / Deselect / live selection **count** / Download (+ ZIP)
- **Download progress** UI (visible while ZIP/blob prepares)
- Empty state: short human next step (e.g. upload path) — no eng flags

### 4. Upload — lifecycle progress honesty
Show real stages:

**Uploading → Processing → Saving to Library → Complete**

Map existing pipeline statuses into these four human labels. Never invent NAS-received or Complete.

### 5. Preview
Clean preview: media + essential human fields. No eng dump (CR, maturity, staff_ready, ops-depth).

### 6. Content Plan declutter
Content-team plan: fortnight / posts / stories / status. Not Wolf dashboard, not Owner Progress, not ops-depth.

### 7. Wolf Intelligence assist shell
Assist for content tasks. **No AKR / Decision Memory exposure** on this staff surface.

### 8. Tests + review artifact
- Add/adjust focused Beta tests proving: four tabs present; banned jargon absent from staff Content HTML for SPECIALIST_CONTENT path; library search hero; upload stage labels; no staff_ready invent
- Write `docs/deliveries/GROK-REVIEW-Content-Engine-Staff-UX-2026-09-24.md`
- FAIL=0 on the pack’s tests
- Restart Beta :8788 only if needed via existing beta restart helpers — **never** touch prod :8787

## Acceptance — nine Owner questions
Haikal (or Peaches simulating staff) can answer **without Wolf architecture explanation**:

1. Where is this brand’s content plan?
2. How do I upload new media?
3. How do I find an asset?
4. How do I preview it?
5. How do I select one or many?
6. How do I download / ZIP the selection?
7. How do I see upload progress through to Library?
8. How do I switch brand/context?
9. Where do I ask Wolf for help on content work?

## Out of scope
- Production / :8787
- New dashboards / new agents
- Operator-depth packs / connective packs
- Inventing metadata filters
- Marking PROVEN / READY / **STAFF READY**
- Merging PR #1
- Fake Haikal human PASS
- Destroying NAS / uncommitted soft-head work
- Smart Upload core rewrite (detail retest **follows** this redesign; only add lifecycle progress honesty + staff chrome cleanup)

## Honesty
`proven=false` · `ready=false` · `staff_ready=false` in **state/CR** — not as staff chrome slogans.

## Done means
Engineering candidate complete + review written + tests FAIL=0 + Beta serves cleaned staff desk.  
**Next humans:** Peaches verify → **Haikal RETEST REQUIRED**. staff_ready stays false until then.
