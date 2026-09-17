> **SUPERSEDED 2026-09-17** — v1 draft. Replaced by v2 then CANONICAL `docs/MODEL-C-CAPABILITY-CATALOG.md`. Kept for history. Do not use as denominator.

# MODEL C CAPABILITY CATALOG DRAFT — 17 Sep 2026

**Status:** DRAFT FOR MATT APPROVAL — not live scoring  
**Factory run:** `BF-model-c-capability-catalog-20260917`  
**Class:** READ-ONLY. No dashboard / scoring formula / application code / DB / Production / Habitat / Uma mutations.  
**Prerequisite:** `docs/deliveries/MISSION-PROGRESS-SCORING-AUDIT-2026-09-17.md`  
**WHERE:** Chat · Path `docs/deliveries/MODEL-C-CAPABILITY-CATALOG-DRAFT-2026-09-17.md`  
**As of:** 2026-09-17 ~20:55 WITA

---

## Hierarchy (Model C)

MISSION (Wolf Command)
  -> DOMAIN (deliberate mission weight; registry-owned later)
       -> CAPABILITY (ONLY these enter the SYSTEM denominator)
            -> REQUIREMENT / CONTROL / TASK / MILESTONE
                 (establish capability maturity only; do NOT inflate mission %)

**Granularity rule:** Splitting one capability into ten requirements must not change that domain's mission weight or the mission denominator count. Merging ten requirements into one capability must not suddenly make the empire look more complete.

---

## Out of mission SYSTEM score

| Item | Treatment |
| --- | --- |
| Personal Command (Spec §18) | OUT — personal calendar/diet/trading personal |
| Build Factory health | OUT — HEALTHY/DEGRADED/FAILING dial, not mission |
| Sale diligence checklist cells | CONTROLS under Sale capabilities — not peer capabilities |
| Commissioning checklist rows | EVIDENCE / MILESTONE on a capability — not denominator rows |

---

## Proposed DOMAINS (14)

Weights are **DRAFT ESTIMATED** only. Not live. Not tuned to the old 28%.

| Domain ID | Domain | Draft weight | Spec anchor |
| --- | --- | ---: | --- |
| D-CORE | Wolf Core | 18% | §§2–4, 6, governance engines |
| D-GGV | GGV | 12% | §5.3 + Content Machine |
| D-AMG | AMG | 12% | §5.1 + §13 |
| D-BZG | BZG | 12% | §5.2 + §12 |
| D-HR | HR / People | 6% | §9 |
| D-FIN | Finance / Accounting | 8% | §10 |
| D-PROC | Procurement | 4% | §11 |
| D-CRM | Customer / CRM / Packages | 5% | §14 |
| D-MSC | Maintenance / Security / Compliance | 4% | §15 |
| D-STRAT | Strategy / Command | 4% | §17 |
| D-INTEL | Wolf Intelligence | 5% | §7 |
| D-INTG | Integrations / Infrastructure | 4% | §§19–20 |
| D-DR | Information / DR | 3% | §25 |
| D-SALE | Sale Readiness | 3% | §24 |
| | **Total** | **100%** | |

---

## Capabilities by domain

### D-CORE — Wolf Core (12)

| ID | Capability | Intent | Evidence types |
| --- | --- | --- | --- |
| CAP-CORE-01 | Organisation Registry | Canonical Group→Entity→Brand→Location→Dept hierarchy | schema prove, legal reconcile |
| CAP-CORE-02 | Person & Auth Identity | Permanent Person; CF JWT → Person binding | auth tests, seat prove |
| CAP-CORE-03 | Role / Position / Assignment | Jobs change without losing history | assignment tests |
| CAP-CORE-04 | Permission & Authority Engine | Deterministic server-enforced RBAC + limits | permission matrix prove |
| CAP-CORE-05 | Authority Limits Evaluator | Amount/scope limits on actions | unit + live limits honesty |
| CAP-CORE-06 | Work Items / Promises / Decisions | Material promises leave a trail | work-item evidence |
| CAP-CORE-07 | Approval Engine | Human authority for material decisions | approval path tests |
| CAP-CORE-08 | Dual Approval | Two independent persons where required | dual-approval tests |
| CAP-CORE-09 | Segregation of Duties | Conflicting duties cannot combine | SoD tests |
| CAP-CORE-10 | Evidence Requirements | Mandatory evidence before approve/live | evidence gate tests |
| CAP-CORE-11 | Exception / Override Governance | Break-glass logged and reviewable | exception path tests |
| CAP-CORE-12 | SOP Factory link | SOP inventory linked to roles/workflows | SOP register coverage |

### D-GGV — Goss Group Ventures (8)

| ID | Capability | Intent | Evidence types |
| --- | --- | --- | --- |
| CAP-GGV-01 | Content Machine | Strategy→plan→asset→workflow→learn loop | board prove, plan cadence |
| CAP-GGV-02 | Habitat Publish Gate | Work Item + draft evidence + designated approvers | Habitat operator loop |
| CAP-GGV-03 | Habitat Human Operator UX | Producers/approvers run gate without Peaches | human commissioning |
| CAP-GGV-04 | Client Profitability | Client/contract/project P&L with cost allocation | finance tiles |
| CAP-GGV-05 | Lead Triage & Speed-to-Lead | Hot leads answered/escalated from approved facts | lead board prove |
| CAP-GGV-06 | Brand Social Ops (Metricool read) | Social performance into Wolf | Metricool connector |
| CAP-GGV-07 | Intercompany Client Mode | AMG/BZG as formal internal clients | agreements + billing |
| CAP-GGV-08 | Agency Delivery Desks | Amanda/Haikal/Misa desks as operating surfaces | seat prove |

### D-AMG — Atrium Management Group (9)

| ID | Capability | Intent | Evidence types |
| --- | --- | --- | --- |
| CAP-AMG-01 | Yanolja PMS Binding | Yanolja authoritative for exposed hotel ops data | API contract + reconcile |
| CAP-AMG-02 | Guest Journey Ops | Enquiry→booking→stay→checkout→return memory | journey / PMS events |
| CAP-AMG-03 | Pre-arrival & Check-in Flow | Pre-arrival completion; swift check-in/out | SOP + pilot |
| CAP-AMG-04 | Packages as Products | Stay+activity packages first-class commercial | package catalog |
| CAP-AMG-05 | Daily Hotel Operating State | Machine-generated daily ops report | auto vs manual report |
| CAP-AMG-06 | Hotel Revenue / Yield | Rates, occupancy, ADR visibility | revenue tiles |
| CAP-AMG-07 | Guest Experience Loop | Requests/incidents service trail | guest tickets |
| CAP-AMG-08 | Atrium Finance Ops Wire | Hotel finance board consuming Core accounting | Zayen board prove |
| CAP-AMG-09 | Service Improvement Loop | Continuous service improvement evidence | review/KPI cadence |

### D-BZG — Blu Zone Group (8)

| ID | Capability | Intent | Evidence types |
| --- | --- | --- | --- |
| CAP-BZG-01 | ESB POS Binding | ESB authoritative F&B transactional SoT | ESB connector + outlets |
| CAP-BZG-02 | Venue Mini-Business P&L | Each outlet budget/KPI/dashboard; Master rollup | outlet boards |
| CAP-BZG-03 | Uma Blu Daily Close | Daily close + exception handover | close prove + human closer |
| CAP-BZG-04 | Inventory / Stock Control | Stock, voids, discounts under control | ESB inventory |
| CAP-BZG-05 | Central Kitchen / Shared Cost Alloc | Usage-based shared cost allocation | allocation evidence |
| CAP-BZG-06 | F&B Recipe / Cost Standards | Repeatable standards without robotic hospitality | recipe/cost SOPs |
| CAP-BZG-07 | Review / Reputation Capture | Reviews earned — signal into Wolf | reputation feed |
| CAP-BZG-08 | Multi-outlet Rollup | BZG Master consolidates venues | master dashboard |

### D-HR — HR / People (5)

| ID | Capability | Intent | Evidence types |
| --- | --- | --- | --- |
| CAP-HR-01 | People Master Record | Staff identity, docs, bank/NPWP, roles | HRIS desk prove |
| CAP-HR-02 | Hiring / Onboarding | Hire→seat→desk→training path | Tisa flow |
| CAP-HR-03 | Training & Desk SOP | Role training complete before LIVE | training prove |
| CAP-HR-04 | Payroll Inputs | Clean payroll inputs to finance | payroll truth |
| CAP-HR-05 | Retention / Succession Signals | People risk visible without Matt | retention metrics |

### D-FIN — Finance / Accounting (6)

| ID | Capability | Intent | Evidence types |
| --- | --- | --- | --- |
| CAP-FIN-01 | Wolf Accounting Core | Shared ledger pattern all brands | Zayen Core prove |
| CAP-FIN-02 | Bank Statement Ingest | Monthly statements → reconcile | ingest registry |
| CAP-FIN-03 | Brand Finance Boards | GGV / Atrium / Uma finance tiles | board prove |
| CAP-FIN-04 | Invoicing / Receivables | Issue/correct invoices | invoice Save→Issue |
| CAP-FIN-05 | Management Reporting | P&L / EBITDA by entity | report prove |
| CAP-FIN-06 | Intercompany Billing | Arm's-length GGV↔AMG/BZG billing | billing evidence |

### D-PROC — Procurement (3)

| ID | Capability | Intent | Evidence types |
| --- | --- | --- | --- |
| CAP-PROC-01 | Supplier Register | Suppliers with concentration visibility | register |
| CAP-PROC-02 | Purchase / Approval Flow | Procurement with authority limits | approval path |
| CAP-PROC-03 | Payment Tracking | Payment status honesty | payment lane |

### D-CRM — Customer / CRM / Packages (4)

| ID | Capability | Intent | Evidence types |
| --- | --- | --- | --- |
| CAP-CRM-01 | Lead CRM | Leads owned, aged, followed | lead boards |
| CAP-CRM-02 | Guest / Client Memory | Relationship memory across stay/client | CRM records |
| CAP-CRM-03 | Package Intelligence | Package performance & demand | package analytics |
| CAP-CRM-04 | Email Marketing Wire | Brand email where applicable | connector honesty |

### D-MSC — Maintenance / Security / Compliance (4)

| ID | Capability | Intent | Evidence types |
| --- | --- | --- | --- |
| CAP-MSC-01 | Asset / Maintenance Register | Asset condition tracked | register |
| CAP-MSC-02 | Access / Cloudflare Posture | Seats, doors, Access includes | access sweep |
| CAP-MSC-03 | Compliance Pack | Licences, contracts, statutory | legal files |
| CAP-MSC-04 | Cybersecurity Baseline | Crown-jewel protection posture | security checklist |

### D-STRAT — Strategy / Command (3)

| ID | Capability | Intent | Evidence types |
| --- | --- | --- | --- |
| CAP-STRAT-01 | 12-Week Year Cadence | Weekly tactics, lead measures, Sunday review | Helm/Radar |
| CAP-STRAT-02 | Owner Radar / Mission Control | One Owner home | radar prove |
| CAP-STRAT-03 | Priority Discipline | ≤3 needle-movers per role/unit/day | NOW board |

### D-INTEL — Wolf Intelligence (4)

| ID | Capability | Intent | Evidence types |
| --- | --- | --- | --- |
| CAP-INTEL-01 | Institutional Intelligence Layer | DATA→TOOLS→REASONING→SYNTHESIS→HUMAN | WI routing |
| CAP-INTEL-02 | Authorised Knowledge Resolution | Empty ≠ UNKNOWN; search authorised sources first | rule + prove |
| CAP-INTEL-03 | Learning / Rule Promotion | Observation→pattern→lesson→human approve | learn loop |
| CAP-INTEL-04 | Noise Suppression | Surface important risks; suppress noise | alert policy |

### D-INTG — Integrations / Infrastructure (6)

| ID | Capability | Intent | Evidence types |
| --- | --- | --- | --- |
| CAP-INTG-01 | Yanolja → Wolf | Hotel reservation/ops intelligence | INT-YAN-WOLF |
| CAP-INTG-02 | ESB → Wolf | F&B sales/inventory intelligence | INT-ESB-WOLF |
| CAP-INTG-03 | Google Workspace → Wolf | Mail/calendar/docs/auth | INT-GWS-WOLF |
| CAP-INTG-04 | Bank Statements → Finance | Cash/reconciliation file import | INT-BANK-WOLF |
| CAP-INTG-05 | Metricool → Intelligence | Social performance | INT-MET-WOLF |
| CAP-INTG-06 | Tech / Capability Registries | Technology inventory + exit conditions | MB-015 |

### D-DR — Information / DR (2)

| ID | Capability | Intent | Evidence types |
| --- | --- | --- | --- |
| CAP-DR-01 | Backup & Disaster Recovery | Restorable backups; reimport package | offsite prove |
| CAP-DR-02 | Crown Jewels Protection | Critical data identified and protected | §25 checklist |

### D-SALE — Sale Readiness (4 capabilities; 60 controls underneath)

| ID | Capability | Intent | Evidence types |
| --- | --- | --- | --- |
| CAP-SALE-01 | Data Room / Buyer Mode | Buyer-ready VDR surface | MB-014 / Vault |
| CAP-SALE-02 | Financial Sale Quality | Finance quality, EBITDA, QoE per entity | Sale controls (finance trio × 3 entities) |
| CAP-SALE-03 | Operating Independence | Founder dependency, management, SOP/training, succession | Sale controls (independence set × 3) |
| CAP-SALE-04 | Transferability Pack | Contracts, compliance, data/tech, cyber, brand/IP, concentration, growth | Remaining Sale controls × 3 |

**Controls (not denominator):** 20 Areas × 3 Entities = 60 Sale_Readiness.csv rows become maturity evidence under CAP-SALE-02..04.

---

## Denominator summary (DRAFT)

| Domain | Capabilities |
| --- | ---: |
| Wolf Core | 12 |
| GGV | 8 |
| AMG | 9 |
| BZG | 8 |
| HR / People | 5 |
| Finance / Accounting | 6 |
| Procurement | 3 |
| Customer / CRM | 4 |
| Maint / Sec / Compliance | 4 |
| Strategy / Command | 3 |
| Wolf Intelligence | 4 |
| Integrations / Infrastructure | 6 |
| Information / DR | 2 |
| Sale Readiness | 4 |
| **TOTAL proposed SYSTEM denominator** | **78** |

Current tracker comparison: **92 rows** (60 Sale controls demoted out of denominator under Model C).

**Simulated overall % under this catalog:** **UNKNOWN** (catalog not locked; maturity not re-scored; refusing to invent a number).

---

## Design notes

1. Overlay Core engines (Approval, Dual, SoD, Evidence, Exception, Auth JWT, Authority Limits) are first-class Core capabilities.
2. Finance / HR / Procurement leave false Core-only compression for scoring clarity; shared code may remain.
3. AMG/BZG expand from 1–2 giant slices into Spec-aligned operating capabilities.
4. Model E dimensions remain separate dials — this catalog is the SYSTEM dial only.
5. New approved Spec scope adds a capability ID via Matt approve; undocumented tracker rows do not.

---

## Open questions for Matt (max 8)

1. Keep 14 domains or collapse HR+Finance+Procurement under Corporate Backbone?
2. Is CAP-GGV-07 Intercompany Client Mode in-scope for 2026 SYSTEM score or deferred?
3. Should Trading / Flint stay Personal (OUT) forever for mission %?
4. Draft weights OK as ESTIMATED start, or equal weights until a registry exists?
5. Confirm Sale stays ~3% SYSTEM weight with deeper maturity on the Sale dimension dial?
6. Add Spec §16 Documents/Legal as its own capability now, or keep inside MSC Compliance Pack?
7. Is Uma Blu the only BZG venue capability set for now (other outlets later)?
8. Approve this catalog as scoring denominator before any Progress % formula change?

---

## Explicit non-goals

- No change to displayed 28%
- No Progress Dashboard UI change (visual freeze stands)
- No Master_Build / Sale_Readiness CSV rewrite yet
- No Production touch
