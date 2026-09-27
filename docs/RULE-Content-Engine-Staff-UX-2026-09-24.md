# RULE — Content Engine Staff UX (2026-09-24)

**Owner lock:** Matthew Goss · **Commissioned:** 2026-09-24 09:18 WITA (~09:15 WITA Owner P0) · **Governor:** Peaches · **Executor:** Grok on Wolf Command  
**Surface:** Beta Content Engine only (`/content-2.0` · :8788) · **Production :8787 sacred — do not mutate**

## Intent
Staff Content Engine must feel like a content desk, not an engineering console. Haikal’s primary job is:

**PLAN → UPLOAD → FIND → PREVIEW → SELECT → DOWNLOAD**

## Primary Haikal nav (non-negotiable)
Four staff tabs + brand/context selector:

1. **CONTENT PLAN**
2. **LIBRARY**
3. **UPLOAD**
4. **WOLF INTELLIGENCE**

Global / Empire / Owner nav may remain available but must be visually **secondary**. Do not bury the four staff tabs.

## Strip engineering language from staff UI
Staff-facing copy and chrome must **not** expose:

- Operator depth / `operator_depth`
- `proven=` / `ready=` / `staff_ready=`
- “human fake” / “No Haikal” commissioning honesty slogans
- “NAS destroy”
- CR- / AU- identifiers
- capability maturity claims
- “connective”
- ENGINEERING / SPECIFIED / Needs-You engineering states as primary chrome
- implementation / test commentary
- AKR / Decision Memory exposure on the staff Content surface

Honesty flags and maturity stay in **server state / Owner / Progress / factory** — not in Haikal’s desk chrome.

## Library
- **Search-first:** large search is the hero control
- Filters only for **real metadata**; advanced under **More filters**
- Results = **thumbnail grid** (media is hero)
- Select all / Deselect / selection count / Download (+ ZIP)
- Download **progress** UI
- Empty state = human language (what to do next)
- Preview = clean (media + essential fields; no eng dump)

## Upload
Real lifecycle progress honesty:

**Uploading → Processing → Saving to Library → Complete**

No fake NAS-received. No fake Complete.

## Content Plan
Content-team plan surface — **not** a Wolf dashboard, not Owner Progress, not ops-depth.

## Wolf Intelligence
Assist shell for content work. **Do not** expose AKR or Decision Memory on this staff surface.

## Security
Permissions stay **server-side**. Hidden ≠ security.

## Platforms
Mobile + desktop. Beta only.

## Factory / maturity locks
- This RULE authorises **one** UX redesign pack under Credit Conservation (human commissioning exception).
- Do **not** invent PROVEN / READY / STAFF READY.
- `staff_ready` must stay **false** until Haikal human retest PASS is recorded separately.
- Smart Upload detail retest **follows** this redesign (no longer top factory arm).
- No new agents. No speculative breadth. No prod mutation. No PR #1 merge from this pack.

## Related
- Gate: `state/build-factory/GATE-content-engine-staff-ux-20260924.json`
- SPEC: `docs/deliveries/SPEC-Content-Engine-Staff-UX-Redesign-2026-09-24.md`
- Audit: `docs/deliveries/AUDIT-Content-Engine-Staff-Jargon-Leak-2026-09-24.md`
- Commissioning: `state/commissioning/CONTENT-ENGINE-UX-2026-09-24.md`
- CR: `state/completion-register/content-engine-staff-ux-20260924.json`
