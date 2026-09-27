> **HISTORICAL 2026-09-17** — Scoring audit that recommended Model C. Catalog now CANONICAL. 28% still legacy estimate pending Model C scoring migration. Do not treat this audit as live scoring authority.

# MISSION PROGRESS SCORING AUDIT — 17 Sep 2026

**Class:** READ-ONLY. No dashboard / Master Build / overlay / registry / weight / code / DB mutations.
**Trigger:** Matt human retest #3 — Owner Cockpit UX PASS; freeze visual; 28% not commissioned as trustworthy mission measure.
**WHERE:** Chat (this report) · Path `docs/deliveries/MISSION-PROGRESS-SCORING-AUDIT-2026-09-17.md`

---

## Verdict

| Field | Value |
| --- | --- |
| Audit | **COMPLETE** |
| Can 28% be called mission complete? | **NO** |
| Granularity invariance (current) | **FAIL** |
| Application / DB / Dashboard / Prod / Habitat / Uma disturbed | **NO / NONE** |

---

## What the current 28% actually measures

A **weighted average of lifecycle maturity** across seven scoring domains (Core, GGV, BZG, AMG, Intelligence, Integrations, Sale Readiness), where each domain score is the **unweighted mean** of that domain’s tracked rows’ lifecycle scores (with a commissioning cap of 0.65 when built-ish but not human-commissioned). Domain weights are fixed estimates (not derived from row count). Label is already `PARTIAL ESTIMATE`.

It measures **build-tracker maturity of the currently ingested 92 rows**, not “Wolf Command mission is 28% done.”

It does **not** measure operating adoption, founder independence, financial control quality, or saleability of the three businesses.

---

## The 92 — classification summary

| Level | Approx count | What |
| --- | --- | --- |
| CAPABILITY / MODULE | ~31 | Master_Build modules remapped into Core/GGV/BZG/AMG/Intelligence/Sale + overlay Core engines + GGV/BZG vertical overlays + Integrations contracts |
| CONTROL / REQUIREMENT (diligence cell) | 60 | Sale_Readiness.csv: **20 Areas × 3 Entities (GGV/AMG/BZG)** |
| DOMAIN | 0 as scored units | Domains are buckets, not rows |
| MILESTONE / TASK | not in denominator | Commissioning.csv (10 releases) exists but is **not** scored into the 92 |

**Sources:** master_build_csv + overlay + integrations_csv + sale_readiness_csv. Master_Build itself has only **16** coarse modules; Finance/People/Operations/Executive/System rows are folded into **Core** for scoring.

### Why Sale Readiness = 61

Not 61 independent mission capabilities. It is:

- **60** buyer-diligence **controls** (same 20 areas repeated for GGV, AMG, BZG) — all `SPECIFIED`
- **+1** Master_Build capability `Data Room / Buyer Mode` (MB-014)

Sale Readiness was specified at **checklist / control granularity**. That domain is over-decomposed relative to operating domains.

### Why AMG = 1

Master_Build lists a single coarse module: **Yanolja Operating Slice** (MB-008, SPECIFIED). The entire Master Spec §13 AMG Hotel Operating System is **compressed into one row**. Same pattern: BZG has 2 (Uma Operating Slice + Uma Daily Close overlay); GGV has 3 (Content Machine + Habitat UI + Habitat Publish Gate).

---

## Master Spec coverage vs scoring denominator

| Master Spec area | Scoring coverage |
| --- | --- |
| Wolf Core (org/identity/permissions/work items/approvals…) | **B/C mixed** — some overlay engines TESTED; many Master_Build Core still SPECIFIED/SCHEMA_BUILT; Finance/HR/Procurement/SOP/Command/DR folded into Core as single rows |
| GGV / Content Machine | **B** — Content Machine + Habitat slices present; agency CRM/client profitability thin |
| AMG Hotel OS | **B compressed** — one Yanolja slice |
| BZG F&B Control | **B compressed** — Uma slice + Daily Close; full §12 control system not expanded |
| HR / People §9 | **B compressed** into Core MB-011 |
| Finance / Accounting §10 | **B compressed** into Core MB-009 |
| Procurement §11 | **B compressed** into Core MB-010 |
| Customer / CRM / Packages §14 | **D absent** as own scored domain |
| Maintenance / Security / Compliance §15 | **D largely absent** (only appears as Sale Readiness *controls*) |
| Documents / Legal §16 | **D absent** |
| Strategy / 12WY / Command §17 | **B compressed** — Matt Command MB-013 |
| Information / DR §25 | **B compressed** — Backup & DR MB-016 |
| Wolf Intelligence §7 | **C thin** — 2 rows |
| Integrations / Infrastructure | **C** — 5 integration contracts, all SPECIFIED |
| Sale Readiness §24 | **C over-decomposed** — 61 |

---

## Granularity invariance — simulations (read-only math)

Current Model A: `overall = Σ (domain_mean(rows) × fixed_weight)`.

| Attack | Result |
| --- | --- |
| Split one TESTED capability into 10 equal TESTED rows (same domain) | Overall **unchanged** (0.2836) |
| Split one TESTED into 1 TESTED + 9 SPECIFIED “requirements” | Overall **28% → ~20%** (Δ −7.9 pp); GGV mean 0.55 → 0.175 |
| Merge Sale 61 → 1 SPECIFIED | Overall **unchanged** (domain already flat SPECIFIED; weight fixed) |
| Merge Core 18 mixed → 1 bucket lifecycle | Overall **moves** (variance collapse; e.g. → SCHEMA_BUILT lifts ~+6 pp) |
| Add 100 future SPECIFIED to Sale | Overall **unchanged** |
| Add 100 future SPECIFIED to Core | Overall **28% → ~22%** (dilution) |
| Omit immature AMG and re-norm weights | Overall **rises ~+4 pp** |
| Mark all Sale LIVE+commissioned | Overall **+5 pp** (Sale weight only 5% — limited blast) |
| Mark all Core LIVE without human commissioning | Overall **+8 pp** but capped at 0.65 — still gameable without adoption |

**Verdict:** Current model **FAILS** the Granularity Invariance Test in the realistic case (capability split into requirement rows). Equal-maturity clone-splits are accidentally invariant; documentation/decomposition refactors are not.

Fixed domain weights **partially** shield overall % from Sale’s 61-row flood, but the **92-row story** and within-domain means remain row-count sensitive. Tracker completeness ≠ mission completeness.

---

## Models

### MODEL A — Current row-mean inside fixed domain weights
- **Strengths:** Simple; domain weights blunt Sale flood; commissioning cap; already labelled PARTIAL ESTIMATE.
- **Failures:** Within-domain mean is row-granularity-sensitive; Master Spec uneven grain; can dilute by adding unfinished rows; omit-domain renorm games %; software LIVE without adoption still scores high (capped, not zero); single % pretends mission completeness.

### MODEL B — Domain-weighted maturity (deliberate domain weights; capabilities only inside domain)
- **Strengths:** Domain mission weight stable; splitting requirements should not change domain weight.
- **Failures:** Still needs a stable capability catalog; if “capabilities” are just today’s rows, collapses to A; weight politics; still one number.

### MODEL C — Hierarchical MISSION → DOMAIN → CAPABILITY → REQUIREMENT
- **Strengths:** Best match to desired properties; requirements set capability maturity only; denominator = approved capabilities; explainable; extensible when new scope is *approved* at capability level.
- **Failures:** Requires upfront catalog + mapping work; governance to prevent fake “capabilities”; evidence rules still needed.

### MODEL D — Milestone / outcome
- **Strengths:** Business-relevant stages (foundation → workflow → commissioned → live → founder-independent → buyer-ready); hard to game with tiny endpoints.
- **Failures:** Coarse; weak for day-to-day build steering; subjective stage gates; naive equal-outcome mean ~24% here is illustrative only, not commissioned.

### MODEL E — Multi-dimension mission maturity (recommended companion)
Separate dials, not one fake mega-%:
1. **SYSTEM** (software capability maturity — Model C)
2. **OPERATING ADOPTION** (humans using it)
3. **DATA / MEASUREMENT**
4. **FOUNDER INDEPENDENCE**
5. **FINANCIAL CONTROL**
6. **SALE READINESS**

Optional rollup “Overall Mission Maturity” only after dimensions exist — or show a radar / min-gate, never a silent average of incomparable things.

---

## Grok recommended model

**MODEL C (hierarchical capability denominator) for SYSTEM progress, plus MODEL E dimensions on the Owner Cockpit over time.**

Do **not** keep selling 28% as mission complete. Keep displaying current tracker % only if clearly labelled **build-tracker estimate** until C is approved — or hide overall % until catalog exists.

**Simulated overall under recommended model:** **UNKNOWN** (capability catalog not yet locked; refusing to invent a tuned number).

---

## Red team — which models can be gamed

| Attack | A | B | C | D | E |
| --- | --- | --- | --- | --- | --- |
| Split 1→10 requirements | FAIL | FAIL if requirements in denom | PASS if reqs excluded | PASS | PASS per dial |
| Merge 10→1 | Mixed | Mixed | PASS at capability layer | PASS | PASS |
| Add 100 future reqs one domain | FAIL (dilute) / Sale no-op | FAIL if in denom | PASS | PASS | PASS |
| Omit immature domain | FAIL (renorm up) | FAIL if weights editable without approval | HARDER if catalog locked | FAIL if stages skipped | Visible on dial |
| Complete many tiny tasks | FAIL | FAIL | HARDER | HARDER | HARDER |
| Software w/o adoption | FAIL (high) | FAIL | FAIL if SYSTEM-only | Better if stage needs humans | PASS (split dials) |
| Commission w/o production | Partial | Partial | Needs LIVE evidence | Needs LIVE stage | PASS |
| Prod w/o measurement | FAIL | FAIL | FAIL if SYSTEM-only | Weak | PASS (DATA dial) |
| Tiny mature vs huge immature | Weight helps | Weight helps | Weight + catalog | Outcomes help | PASS |

---

## Can Master Spec support trustworthy scoring?

**PARTIAL.** Intent and domains are there. Missing: approved **stable capability catalog** at consistent grain, owned domain weights registry, evidence binding for status, and explicit separation of diligence controls vs capabilities.

### What must change before trustworthy scoring

1. Lock a **capability catalog** (Model C grain) mapped from Master Spec — not Sale checklist cells as peers of hotel OS.
2. Move Sale_Readiness 60 cells to **controls under** Sale capabilities (or Sale dimension), not mission denominator peers.
3. Expand compressed domains (AMG/BZG/HR/Finance/CRM/… ) to real capabilities **or** accept explicit “compressed = one capability until decomposed” with no fake precision.
4. Put **domain weights** in an approved registry (not code constants labelled ESTIMATED).
5. Evidence rules for lifecycle/commissioning/live.
6. Decide Owner Cockpit shows **multiple dimensions** (Model E); single % only as optional SYSTEM rollup with honest label.

---

## Recommended next action (ONE)

**Approve a Model C capability catalog draft (domain → capability list + which current CSV rows map in/out) before any scoring formula or displayed-% change.**

