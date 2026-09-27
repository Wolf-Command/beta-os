# Habitat Brand Intelligence Discovery — 17 Sep 2026

**Lane:** Beta `/Users/wolfterminal/beta-os` read-only  
**Commissioning:** Haikal/Amanda human loop **not disturbed** (content_planner Habitat slots unchanged this mission)  
**Code / DB mutations / Metricool write / Production:** none  

## Why

Content Machine should eventually run from canonical Client/Brand Intelligence. **Reuse before build.** This pass maps what already exists.

## Classification legend

| Class | Meaning |
|---|---|
| CANONICAL | Explicit authoritative structured Wolf source |
| AVAILABLE BUT UNSTRUCTURED | Exists in files/text/config; not authoritative structured |
| DERIVED | Calculated/inferred from other evidence |
| HUMAN-HELD | Someone knows; Wolf does not hold it |
| UNKNOWN | No trustworthy answer |

Do **not** upgrade AVAILABLE → CANONICAL because a sentence exists.

---

## IDENTITY

| Item | Class | Current source |
|---|---|---|
| GGV entity | CANONICAL | `org_entities` ENT-GGV |
| Habitat as Client Brand under GGV | CANONICAL | `org_brands.brand_id=habitat` CLIENT_BRAND LIVE; `brands.id=habitat` ACTIVE + `org_brand_id` |
| Legal client vs developer (Keen Eye) | AVAILABLE → APPROVED memory (not legal registry) | `memory_items` FACT #1–2 from Obsidian `Habitat-Brand.md` (`approved_by=phase1-habitat-import`) |
| Metricool profile | CANONICAL link | `brand_external_ids` habitat → metricool `6260634` |
| Habitat physical location in org | ABSENT | `org_locations` only LOC-ATRIUM-LOMBOK; no Habitat brand_location |
| Websites/domains | UNKNOWN / HUMAN-HELD | Not found as structured Beta field |
| Social handles | DERIVED | Metricool `performance_records` permalinks / captions |
| Default content assignee | AVAILABLE | `brands.default_assignee` = haikalqilbari123@gmail.com |
| GGV account ownership nuance | HUMAN-HELD | Client-seat vs agency relationship details |

## BRAND

| Item | Class | Notes |
|---|---|---|
| Colours | CANONICAL-ish | `brands.theme_json` + APPROVED FACT #7 (aligned #79755B / #EAE6D7 / #A6A28B) |
| Font | CONFLICT | APPROVED FACT #6 **Manrope** vs `theme_json` **Inter** — not safe as single truth |
| Tone / banned clichés | PARTIAL CANONICAL | APPROVED RULE #12–14 (architectural journal; no luxury/stunning; no handheld wobble) |
| Brand essence / quiet luxury | AVAILABLE BUT UNSTRUCTURED | OBSERVATION #15 **PROPOSED** only |
| Visual direction | PARTIAL | RULE #13 APPROVED; grid ratio OBSERVATION #17 PROPOSED |
| Logo/assets pack on NAS | AVAILABLE | FACT #9 path; NAS folder present (fonts/logos/palettes/style-guide) — not ingested as rights objects |
| Haikal craft style JSON | AVAILABLE BUT UNSTRUCTURED | wolf-system `state/style-profiles/haikal.json` (editor craft, not Habitat brand bible) |

## CUSTOMER

| Item | Class |
|---|---|
| Audiences / segments / journey / objections / FAQs | HUMAN-HELD or buried in Metricool captions (DATA, not approved FAQ store) |
| Reasons to choose Habitat | DERIVED from post copy in `performance_records` — treat as CLAIM until confirmed |

## COMMERCIAL

| Item | Class |
|---|---|
| Products (Forest / Garden / Vibe villa counts & sold-out) | PARTIAL CANONICAL | APPROVED FACTs #3–5, #11 |
| Pricing / packages | ABSENT / HUMAN-HELD |
| CTAs / DM paths | DERIVED from Metricool captions |
| Conversion goals | AVAILABLE in fortnight `strategy_json` objectives (plan-level, not brand registry) |
| Scarcity / ROI unlocks | HUMAN-HELD (Matthew) |

## CONTENT

| Item | Class |
|---|---|
| Cadence (Fri 09:00 WITA developer update; fortnight targets) | PARTIAL CANONICAL | FACT #8 + `brands.cadence_json` |
| Content pillars | AVAILABLE BUT UNSTRUCTURED | OBSERVATION #16 **PROPOSED** only |
| Grid ratio 35/25/20/20 | AVAILABLE BUT UNSTRUCTURED | OBSERVATION #17 PROPOSED |
| Platforms / formats | AVAILABLE | planner + Metricool networks |
| Approval rules (publish) | CANONICAL | `GPO-HABITAT-CONTENT-PUBLISH` + `EVR-HABITAT-CONTENT-PUBLISH` + `docs/canon/HABITAT-PUBLISH-GATE.md` |
| Fortnight plans | AVAILABLE | `content_plans` Habitat Working_Draft / Human_Approved + strategy_json themes |
| Know/Like/Trust mapping | ABSENT as structured field |

## FACTUAL CLAIMS

| Statement | Class |
|---|---|
| Forest 10 sold out; Garden 18 sold out / mid-build; Vibe 31 early build | APPROVED memory FACT — still **claim-vs-inventory** until ops/legal reconfirm |
| Foreigners buy via PT PMA / HGB; nominee discouraged; opex ~10% rent | In Metricool captions → **CLAIM** (marketing), not verified legal fact store |
| “Low risk” framing | Marketing language → **CLAIM** |
| Manrope primary typeface | APPROVED FACT but **conflicts** with theme_json Inter |

Separate always: **VERIFIED FACT** vs **CLAIM** vs **UNKNOWN**. Marketing copy must not silently become truth.

## PERFORMANCE / LEARNING

| Item | Class |
|---|---|
| Metricool historical posts + metrics | AVAILABLE (DATA) | `performance_records` **1103** rows; habitat profile 6260634; Beta Metricool **write disabled** |
| High/low performer lessons | ABSENT as approved lessons | No `memory_items` LESSON/APPROVED from performance |
| Planning refs to metricool | DERIVED | `planning_context_refs` includes `metricool_performance` |

Metricool = **DATA**, not an agent. Do not auto-promote engagement into brand law.

## RIGHTS / ASSETS

| Item | Class |
|---|---|
| Library file rows | PARTIAL | `assets` ~9 habitat paths; location/shoot_date/uploader exist |
| Usage rights / expiry / model release / creator contract | ABSENT columns | File existence ≠ rights |
| Brand-Assets NAS vs library_v2 | AVAILABLE path + HUMAN-HELD ownership rules |

## OPERATOR FEEDBACK (Haikal — not brand truth)

Source: `docs/deliveries/HAIKAL-BETA-CONTENT-FEEDBACK-2026-09-17.md`  
Class: **USER / OPERATOR FEEDBACK** (preserved separately)

| Feedback | State |
|---|---|
| Fortnight human titles | FEEDBACK → PROPOSED CHANGE (Wave 1 mission exists; **not** VERIFIED IMPROVEMENT) |
| Human page headers | FEEDBACK → PROPOSED |
| Status on list | FEEDBACK → PROPOSED |
| Library Select all / Deselect all | FEEDBACK → PROPOSED |
| Brand colour tint; keep shared font | FEEDBACK → PROPOSED |
| Library search + detailed-filter accordion | FEEDBACK → PROPOSED |
| Upload / Smart Upload works — no change | FEEDBACK (keep) |
| Not ready for unsupervised team | FEEDBACK (trust bar) |
| Review team pages after his desk solid | FEEDBACK (sequence) |

States: FEEDBACK → PROPOSED CHANGE → IMPLEMENTED → RETESTED → VERIFIED IMPROVEMENT.  
Wave 1 was **superseded/paused** for human commissioning — do not mark IMPLEMENTED.

## INSTITUTIONAL / BUS FACTOR (if Haikal + Amanda + Matt gone 90 days)

1. What “sounds like Habitat” beyond 3 APPROVED RULE lines  
2. Live inventory / sold / prices vs prospectus  
3. Scarcity & ROI narrative unlocks (Matthew)  
4. Which claims are legally safe this week  
5. Footage/rights for specific owners/guests  
6. Amanda commercial approve norms beyond Core policy IDs  
7. Haikal craft taste vs brand law boundary  
8. Client (Keen Eye) relationship / commission nuances  
9. What Metricool winners mean for next fortnight (no lesson store)  
10. Font/visual kit truth (Manrope vs Inter conflict)

---

## Current sources of truth (map)

| Concern | Current |
|---|---|
| Org / entity / brand id | `org_*` + `brands` |
| Brand facts/rules | `memory_items` (+ approval_state) |
| Publish approval | Core governance policy + evidence req + HABITAT-PUBLISH-GATE canon |
| Cadence / theme chrome | `brands.cadence_json` / `theme_json` |
| External social | `brand_external_ids` + `performance_records` |
| Plans | `content_plans` / cards / strategy_json |
| Operator UX wishes | Haikal feedback delivery doc |
| Craft editor rules | wolf-system style-profiles (non-Beta) |

## Recommended future canonical model (smallest)

**No new Brand Memory / Client Intelligence / Learning / vector DB / agent.**

Reuse:

1. **`org_brands` + `brands`** — identity, theme, cadence, Metricool link  
2. **`memory_items`** — FACT / RULE / OBSERVATION with approval_state (promote pillars/voice only after human confirm)  
3. **`evidence_items` / Core evidence** — bind claims to proof  
4. **`performance_records`** — Metricool DATA only; lessons become PROPOSED memory after human review  
5. **`content_plans`** — period strategy; do not duplicate brand law into every plan  
6. **`assets` + Naming Law** — files; add rights later only if needed  
7. **Core publish-gate policy** — approval rules already live for Habitat  

Resolve conflicts (Manrope vs Inter) by **one human confirm**, then single APPROVED FACT + theme_json update — not a new system.

## Grok architecture challenge

1. **Duplicating?** Yes risk if we build “Brand Bible” beside `memory_items` + `brands`.  
2. **Canonical?** Org brand row + APPROVED memory + publish policy.  
3. **Source-linked?** Metricool posts, NAS kits, prospectus — link/hash, don’t copy wholesale.  
4. **Derived?** Performance rankings, CTA frequency — compute on read.  
5. **Human confirm?** Pillars, voice pack, legal claims, inventory, font conflict, scarcity rules.  
6. **Profit lever?** Approved claims + pillars + lesson loop from Metricool → fewer wrong posts, faster fortnight build.  
7. **Masturbation — do NOT build:** Brand Memory UI, Client Intelligence CRM, Learning Library product, AI voice agent, vector DB, auto-scrape, second Metricool store, new agent.

## MUST CAPTURE FROM HUMANS (later — not this mission)

- Confirm/reconcile **Manrope vs Inter**  
- Promote or rewrite **pillars** (PROPOSED → APPROVED or reject)  
- Reconfirm **inventory / sold-out / legal PT PMA claims**  
- Matthew **scarcity/ROI unlock** rules  
- Minimal **rights** policy for Habitat footage (who can appear)

## Do we need new Core primitive? **NO**  
## Do we need new agent? **NO**

---

## Artifact hygiene

- Read-only SELECTs on `catalog/content_library.sqlite`  
- No writes to content_planner / approvals / Metricool  
- Haikal commissioning slots observed unchanged at discovery close (ids 1,3–6; no work_item/core_approval on those rows at check time)
