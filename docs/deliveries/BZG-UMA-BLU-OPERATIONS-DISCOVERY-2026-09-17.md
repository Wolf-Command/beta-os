# BZG — Uma Blu Daily Venue Operations Discovery

**Date:** 2026-09-17  
**Class:** DISCOVERY ONLY — no application code, no DB mutations, no ESB writes, no Production mutations  
**Rule applied:** Authorised Knowledge Resolution (RULE-Authorised-Knowledge-Resolution-2026-09-17)  
**Habitat commissioning:** undisturbed (read-only check only)

---

## 1. Scope searched

| Source | Result |
|---|---|
| Beta org registry (`content_library.sqlite`) | FOUND — ENT-BZG, BZG-UMA, DEPT-BZG-FB, ROLE-BZG-HFB |
| Beta Data_Sources / Integrations / SOP_Register | FOUND — ESB named as F&B SoT (SPECIFIED) |
| Obsidian vault `03-BZG/` | FOUND — overview, ESB auth, cash-recon design, Alchemist tasks, sales capture |
| Google Drive | FOUND — ESB capability reports, Ordering SOP, F&B Ops project instructions, Alchemist Control |
| Notion BZG hub | FOUND — Tasks, PRs, Waste Log, Petty Cash, Daily Sales, Stock Counts, Recipes, etc. |
| NAS Brand-Assets/BZG/Uma-Blu-Cafe | FOUND — brand assets (not daily ops SOPs) |
| wolf-system `esb.sqlite` warehouse | FOUND — sales/GL/material_usage live through 2026-09-16 |
| wolf-system scripts (esb_*, bzg-*) | FOUND — ingest/report/PR/waste/petty paths exist |
| Peaches staff memory | PARTIAL — Clara/Dede content; Devi not in peaches-memory slug files |
| Full kitchen/bar/floor Notion SOP pages | INACCESSIBLE as named pages in this sweep (ops instructions say they live in Notion; hub lists DBs; specific SOP docs not retrieved by title search) |
| ClickUp BZG Ops list 901818393154 | KNOWN — referenced in ops instructions; not live-queried this pass |
| ESB settlement / cancel-menu / goods-receipt reports | CONFIRMED UNAVAILABLE via API (Felix 2026-07-19) |

---

## 2. Canonical structure

| Object | Status | Evidence |
|---|---|---|
| Legal entity BZG | **PASS** | `ENT-BZG` LIVE — Blu Zone Group |
| Uma Blu venue/brand | **PASS** | `BZG-UMA` LIVE, brand_type=VENUE, display Uma Blu Brunch Cafe |
| Location binding | **PARTIAL** | Bound to shared `LOC-ATRIUM-LOMBOK` (AMG property) — correct commercially; no separate Uma Blu site row |
| Department F&B | **PASS** | `DEPT-BZG-FB` |
| Role Head of F&B | **PARTIAL** | `ROLE-BZG-HFB` exists; **no** BZG position/assignment/person for Devi (or outlet leads) in Beta org tables — only GGV content assignments seeded |
| People / assignments | **PARTIAL** | Devi + ~26 staff documented in vault/Agent-BZG + Notion Employees DB; **not** canonicalised into Beta `org_persons` / assignments |

Do **not** invent people into Core. Seed only after human identity confirm.

---

## 3. Real daily loop (from authorised sources)

Evidence-backed map (Uma Blu primary; other BZG outlets earlier-stage per ops instructions):

**BEFORE OPEN**
- Fast-moving stock vs PAR (SOP-INV-001)
- Kitchen: temp logs, cold storage, prep vs expected covers (F&B Ops instructions)
- Bar: stock vs par, ice, speed rail, POS float (ops instructions)
- Floor: tables, POS operational, specials brief
- ClickUp BZG Ops open maintenance/supplier tasks affecting today
- Notion SOPs cross-check (authoritative per ops instructions)

**OPEN / OPERATING**
- ESB POS bills (branch **BLZ**) — sales, payments, discounts, status including Cancelled
- Order flow / complaints → ClickUp Food Complaint (ops instructions)
- Emergency PRs → HoD / Devi (SOP-INV-001 + Alchemist PR path)
- Receiving: qty/quality/expiry/price/FIFO checks (SOP-INV-001); GRN photo+manual variance (Felix: goods-receipt API unavailable)

**SHIFT / CLOSE**
- Closing stock update + waste log (SOP-INV-001 + Notion Waste Log DB)
- Cash count gap: **DESIGN-UmaBlu-Cash-Card-Reconciliation** — ESB has no settlement API; proposed 22:30 one-number cash count vs ESB cash total
- Alchemist: delivery/petty/prep bot cards still pending physical rollout (open tasks)

**NEXT-DAY**
- ESB nightly warehouse pull (~05:30) → sales/GL/material_usage
- Alchemist Control sales refresh ~05:47
- Sales-Capture vault note from daily-log
- Variance / exception only when thresholds breached (design — thresholds not yet Matt-authorised)

---

## 4. Systems map

| System | Responsibility |
|---|---|
| **ESB OMS/Core** | POS sales, menus, products, material usage, GL lines; Core purchasing/inventory reachable but largely not warehouse-ingested |
| **Wolf `esb.sqlite`** | Read warehouse copy of ESB (contextual) |
| **Alchemist (Telegram + Control sheet)** | PR submit/approve (Devi), delivery/petty/prep, AP/cash views |
| **Notion** | Ops DBs (tasks, waste, petty, stock, recipes, daily sales, PRs) — parallel ops store |
| **ClickUp BZG Ops** | Maintenance / complaints / deep-clean tasks |
| **Banks (monthly statements)** | Cash truth lag — no live bank feed |
| **Wolf Beta Core** | Org/approval/evidence primitives — **not yet wired to Uma Blu daily ops** |
| **Wolf uma-blu.html / finance boards** | Money/content surfaces — not daily venue control loop |

---

## 5. ESB access (read-only verified)

- **READ:** YES (OMS warehouse live; Core JWT previously proven Jul 2026 — ingestion of Core groups still pending per capability report)
- **WRITE performed this mission:** NO
- **Branch:** BLZ = Uma Blu (Felix)
- **SoT map:**
  - Sale / bill / payment mix / discount fields → **ESB**
  - Menu / product / BOM → **ESB**
  - Material usage (ingredient burn) → **ESB**
  - GL journal lines → **ESB** (accounting-grade feed; Wolf Accounting still specified as books SoT in Beta Data_Sources — do not collapse)
  - Goods receipts / POS settlement / cancel-menu detail reports → **ERP-only / no API** (Felix)
  - Live stock levels via external Basic stock-branch → historically blocked; treat stock as **PARTIAL / human+Notion+Alchemist** until Core inventory ingest proven

**Reconciliation IDs available:** `salesNum`, `billNum`, `branchCode=BLZ`, `salesPayments[].paymentMethodTypeName` (e.g. CARD), amounts, `statusName` (incl. Cancelled).

---

## 6. Profitability data maturity

| Lens | Available? | Notes |
|---|---|---|
| Revenue | **YES** | ESB sales + Sales-Capture + Alchemist (~IDR 15–16M/day recent) |
| COGS | **PARTIAL** | material_usage + recipe costing (~85% menu costed); 6 dishes still uncosted; true daily COGS not closed-loop without receipts |
| Labour | **PARTIAL / mostly MISSING for KPI** | Rostered hours → HR Master still open Alchemist task → blocks Sales-per-Labour-Hour |
| Waste | **PARTIAL** | Notion Waste Log + SOP + `bzg-waste-log.py`; not proven continuous |
| Discount / void | **PARTIAL** | ESB fields exist; Sep sample: discounts rare; Cancelled bills present (44 in Sep sample window) |
| Cash close | **NO deterministic** | Design exists; settlement API absent; human cash count not systematised in Wolf Core |
| Trustworthy daily 20% operating profit view | **NO** | Revenue strong; labour+overhead+full COGS+cash integrity incomplete |

---

## 7. Deterministic exceptions possible *now* (no new thresholds invented)

Candidates with **data already present** (threshold values still need business authority before alerting):

1. **ESB day not closed / pull stale** — warehouse max date vs calendar
2. **Cancelled / non-Finished bill rate spike** — `statusName` on sales
3. **Discount / promo / voucher total spike** — existing fields
4. **Sales anomaly vs 7-day baseline** — sales + Sales-Capture
5. **Missed Alchemist PR approval backlog** — Notion/Alchemist (ops)
6. **Open Critical ClickUp maintenance past SLA** — if ClickUp queried

**Not yet deterministic without new human evidence:**
- Cash mismatch (needs close count)
- Stockout vs PAR (needs live stock + PAR completeness)
- Excessive waste (needs reliable waste logging)
- Missed opening checklist (needs checklist completion evidence)

---

## 8. Knowledge gaps / human-held (after search)

**Truly human-held / not found as operable truth:**
1. Who is the named **closing-shift cash owner** each night (design open item)
2. Authorised **variance thresholds** (cash %, IDR)
3. Current live **PAR levels** per SKU (referenced everywhere; completeness unknown)
4. Exact **opening/closing checklist** executable steps for Uma Blu floor/bar/kitchen as current practice (Notion SOP pages not retrieved; ops instructions are summary)
5. Roster / who is on which shift today
6. Petty-cash tin current float baseline
7. Whether Alchemist delivery/petty/prep human rollout actually finished after Jul open tasks
8. Labour hours feed for daily labour cost
9. How service-charge / tips payout interacts with close (Notion tip task exists; process ownership human)
10. Matt 90-day bus-factor: supplier negotiation judgement, menu price decisions, >IDR 5M commitments, ESB credential relationship with Felix

**Why Wolf could not answer each:** no authorised structured source with current values after search — not empty Beta field alone.

---

## 9. Founder dependencies discovered

- Monday supplier payment PDF → Matt settles (Agent-BZG)
- Menu pricing / add-remove → Matt + GGV
- Food safety / critical equipment / health inspection → Matt Telegram
- Commitments > IDR 5M visibility (Devi approves PRs; Matt still money/settlement path)
- Cash leakage invisible without Matt chasing (recon design open since ≤25 Jul)
- Alchemist open inputs still waiting Matt (statements, MD summary) and Devi (cards, stock, hours)

---

## 10. Wolf Core reuse vs missing primitive

**Reusable as-is:** Person, Role, Position, Assignment, Scope, Work Item, Approval, Evidence, Audit, Authority, Delegation, SoD, Exception/Override.

**Missing Core primitive:** **NONE** for first vertical. Gap is **vertical wiring + human evidence capture**, not a new primitive.

**Do not** fork BZG-specific Work Item/Approval.

---

## 11. Recommended first vertical (ONE)

### **UMA BLU DAILY CLOSE + EXCEPTION HANDOVER**

**Why this one (not opening checklist, not full stock, not Issue CRM):**
- Happens **every trading day**
- Real pain **already documented** (cash-vs-card leakage invisible; ESB settlement API unavailable — Felix)
- ESB already supplies sales + `salesPayments` payment mix; Wolf should **not** replace POS
- Smallest human ask: **one cash-count evidence** at close (+ optional void/discount glance)
- Exception-first: quiet when clean; Work Item only on variance / cancelled spike / pull failure
- Exercises Core: Work Item + mandatory evidence + designated approver (Devi / Head of F&B) + audit
- Reduces founder dependency: Matt sees **exceptions**, not every bill
- Profit path: leakage + discount/cancel visibility protects contribution toward 20% target
- Small enough to human-commission after Habitat-style operator UI

**Expected Core path:**  
Close event → attach ESB day fingerprint + cash-count evidence → auto-calc variance → if over authorised threshold create Work Item → Devi approve/resolve → Exception log; Metricool/ESB writes untouched.

**ESB continues to own:** bills, payments, menu, material usage, GL feed.  
**Wolf owns:** close control evidence, variance exception, accountability, management visibility.

**What NOT to build now:** POS, ESB replacement, full stock engine, recipe engine, scheduling/HR system, AI venue manager, giant BZG app, loyalty/CRM, notification platform, inventing thresholds without Matt.

---

## 12. Grok challenge (independent)

1. Real problem? **YES** — recon design + Felix API gap.  
2. ESB already solve? **NO** for settlement/cash.  
3. Duplicate SoT? **NO** if ESB remains bill truth.  
4. Core handle? **YES**.  
5. Deterministic vs judgement? Variance math deterministic; threshold + dispute judgement.  
6. Evidence of completion? Cash count + ESB totals + approver decision.  
7. Annoying admin risk? High if multi-form; keep to **one number/photo**.  
8. Founder dependency? Cuts Matt daily recon chase.  
9. Profit? Leakage + cancel/discount control.  
10. Explicitly NOT build? Opening mega-checklist first (weaker data loop); stock engine before PAR truth; second Alchemist.

**GROK REVIEW: PASS**

---

## 13. Pilot humans (verified from sources — not invented seats)

- **Ops / approver:** Ni Putu Devi Parwati (Operational Lead / Uma Blu ops — Drive ops instructions + Notion HR conversation + Agent-BZG). **Not yet** in Beta `org_persons`.
- **Producer / closer:** named closing-shift staff — **HUMAN-HELD** until roster confirm (do not invent).
- **Finance observer (read):** Zayen pattern for AMG/BZG books replication — not required for close pilot.

---

## 14. Non-actions

No application code. No DB seed. No ESB write. No Production mutation. No ask to staff until Matt approves next slice.
