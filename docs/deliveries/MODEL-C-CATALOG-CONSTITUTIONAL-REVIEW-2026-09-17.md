> **HISTORICAL EVIDENCE 2026-09-17** — Constitutional AMEND of v1. Findings applied in v2. Canonisation complete. Keep as review evidence; do not reopen as live gate.

# MODEL C CATALOG CONSTITUTIONAL REVIEW — 17 Sep 2026

**Status:** AMEND — do not canonise 78 as-is  
**Class:** READ-ONLY. No scoring / dashboard / code / DB / Production.  
**Inputs:** `MODEL-C-CAPABILITY-CATALOG-DRAFT-2026-09-17.md` + `WOLF-COMMAND-MASTER-SPECIFICATION.md`  
**WHERE:** Chat · Path `docs/deliveries/MODEL-C-CATALOG-CONSTITUTIONAL-REVIEW-2026-09-17.md`

## Verdict

CATALOG CONSTITUTIONAL REVIEW: **AMEND**  
78 CAPABILITIES REVIEWED: **YES**  
SAFE TO CANONISE: **NO**  
NEW SCORE CALCULATED: **NO**

## Material findings only

### MERGE
1. **CAP-GGV-02 + CAP-GGV-03** → one **Publish Gate & Operator Loop**. Habitat UX is commissioning of the gate, not a second mission capability.
2. **CAP-AMG-02 + CAP-AMG-03** → **Guest Journey Ops** (pre-arrival/check-in is journey stage, not separate capability).
3. **CAP-BZG-02 + CAP-BZG-08** → **Venue P&L & Master Rollup**.
4. **CAP-SALE-02 + CAP-SALE-03 + CAP-SALE-04** → one **Continuous Sale Evidence Pack** (finance/independence/transferability controls underneath). Keeps Sale from cloning FIN/HR/MSC as three peer systems.

### SPLIT / RENAME (grain)
1. **CAP-BZG-03 Uma Blu Daily Close** → **Venue Daily Close** (shared). Uma Blu = first adoption instance. Otherwise a 4th venue multiplies capabilities.
2. **CAP-AMG-01** rename intent to **Hotel PMS Orchestration** (Wolf owns workflows; Yanolja owns PMS facts).
3. **CAP-INTEL-01** underspecified blob → keep orchestration thin; **add** Retrieval/Memory Search, Provenance & Conflict, Decision Memory (see MISSING).

### MOVE DOMAIN
1. **CAP-AMG-08 Atrium Finance Ops Wire** → not an AMG capability; it is **entity adoption of CAP-FIN-03**. Remove from AMG denominator.
2. **CAP-CORE-12 SOP Factory** → treat as full **§8 SOP Factory** capability (Core or Ops). Current "link" wording is too weak for Spec weight — expand intent in place (domain can stay Core for now).

### REMOVE (not true capabilities)
1. **CAP-GGV-08 Agency Delivery Desks** — seat/UI surface, not a business capability.
2. **CAP-STRAT-03 Priority Discipline** — operating principle / rule, not a capability.
3. **CAP-AMG-08** — see MOVE (entity adoption).

### MISSING (approved Spec areas absent or too thin)
1. **§16 Documents, Records & Legal Defensibility** — callable records, retention, legal hold, dispute chronology, contract intelligence.
2. **§10 Cash forecast / budget / rolling forecast cadence** (13-week cash, annual+rolling).
3. **§10 Profit leakage intelligence** (waste, variance, discounts, OOO, unprofitable items, overservicing, etc.).
4. **§7 Intelligence machinery:** authorised retrieval/search; provenance & evidence classes; conflict/supersession; decision memory (beyond generic "Institutional Intelligence Layer").
5. **Delegation & escalation burn-down** — machinery to remove accidental Matt dependency (Spec founder-independence KPIs + §2 delegations).
6. **Secrets & environment separation** — secrets mgmt; Dev/Beta/Prod separation (§25).
7. **§12 Cash chain** (float→bank) — fold under Venue Daily Close as requirement if not added as separate cap.
8. **§13 Housekeeping / room operations** — fold under Daily Hotel Operating State / Guest Journey as requirements if not separate.

### EXTERNAL-SYSTEM BOUNDARY
- **ESB / Yanolja:** Spec is clear — external systems own transactional/PMS facts; Wolf orchestrates intelligence, finance, workflows. Draft duplicates pipes (`CAP-INTG-01/02/05`) beside business caps (`CAP-AMG-01`, `CAP-BZG-01`, `CAP-GGV-06`). **Keep connectors in D-INTG tagged OWNERSHIP=INTEGRATE**; entity caps tagged OWN workflows / CONSUME external SoT. Do not claim Wolf owns ESB/Yanolja truth.
- **Metricool / Banks / Google:** same INTEGRATE pattern.
- **NONE** as "Wolf wrongly claims ownership of PMS/POS" if ownership tags are applied; **PROBLEM** if left ambiguous.

### SHARED-vs-ENTITY
- **Uma-named Daily Close** fails shared test → rename to shared Venue Daily Close.
- **Habitat-named Publish Gate/UX** should be first adoption of GGV publish governance, not Habitat-only forever capabilities.
- **AMG Hotel OS** is shared architecture; additional hotels = property adoption/scope, not catalog clone.
- **FIN/HR/PROC** correctly shared once with entity adoption (do not clone per entity).

### Coverage grades
| Lens | Grade | Gaps |
| --- | --- | --- |
| Founder independence | FAIL | Delegation/escalation burn-down not explicit; Uma/Habitat naming hides adoption pattern; desks/priority noise |
| Profitability | FAIL | Missing cash/budget cadence + profit leakage; GGV/AMG/BZG P&L present but incomplete vs Spec §10/12/13 |
| Saleability | PASS* | Data Room good; *02–04 duplicate other domains unless merged to one evidence pack + Model E Sale dial |
| Intelligence | FAIL | Retrieval, provenance, conflict, decision memory underspec; risk of "one blob + agents" |
| Resilience | FAIL | DR present but secrets/env separation thin; legal records missing; crown jewels vs cyber split OK if clarified |
| Granularity invariance | PASS | Hierarchy rule correct; **FAIL in practice** while Uma/Habitat-specific rows remain |

### Adversarial simulations
| Attack | Result |
| --- | --- |
| Split any cap into 100 requirements | PASS **if** Model C enforced — count unchanged |
| Add 4th BZG venue | FAIL on current Uma-named close; PASS after Venue Daily Close shared |
| Add another hotel | PASS if AMG = shared Hotel OS + property adoption; FAIL if catalog cloned |
| Sell GGV independently | PASS domain separation; watch Core licence + intercompany boundaries |
| Matt disappears 90 days | FAIL until delegation/escalation + succession machinery explicit |
| ESB/Yanolja disappears | PASS only with explicit INTEGRATE vs OWN tags and fallback requirements |

### 8 open questions — resolved from canon
1. **Domains:** Keep Finance/HR/Procurement separate — Spec §§9–11 are distinct approved areas. Not Corporate Backbone collapse.
2. **Intercompany Client Mode:** IN SCOPE — Spec §5.3 AMG/BZG as internal clients of GGV.
3. **Trading/Flint:** OUT of SYSTEM mission % — Spec §18 Personal Command Boundary.
4. **Weights:** Stay ESTIMATED/labelled until a registry owns them — no equal-weight mandate in canon.
5. **Sale ~3% SYSTEM + deeper Sale dial:** Architecturally consistent with Model C/E split from scoring audit.
6. **§16 Legal/Documents:** Must be a capability (or explicit MSC expansion) — Spec approved; not optional omit.
7. **Uma-only naming:** Wrong grain — Spec treats each venue as mini-business; shared venue capabilities + adoption.
8. **Approve before score change:** Process gate remains — not auto-canonised by this review.

### Genuine questions for Matt (3)
1. Sale SYSTEM denominator: **Data Room + Continuous Sale Evidence Pack + Buyer Mode/Attack** only — with detailed diligence living on the Sale dimension dial — **or** keep more Sale SYSTEM weight?
2. **2026 priority:** is Intercompany Client Mode / intercompany billing in the near SYSTEM build path, or deferred behind Atlas/Content?
3. After Peaches applies the AMEND list above to a revised draft (~75 caps), do you **approve that revised catalog** as the locked SYSTEM denominator (still no score change until a later explicit approve)?

## Recommended final capability count

**75** (target after AMEND)

Why changed from 78: remove 3 non-capabilities / wrong grain; merge 5 groups (−5 net from merges of 2+2+2+3); add ~5 Spec-missing (Legal records, cash/budget, profit leakage, intel memory machinery net, delegation, secrets) with housecash/HK folded as requirements where possible. Exact post-edit count may land 72–76; **75** is the target band. Not tuned to any %.

## Safe to canonise
**NO** — amend first, then Matt approve revised draft.
