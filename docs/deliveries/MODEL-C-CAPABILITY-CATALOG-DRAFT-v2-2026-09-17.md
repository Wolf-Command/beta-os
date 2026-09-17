> **PROMOTED → CANONICAL 2026-09-17** — v2 draft text promoted to `docs/MODEL-C-CAPABILITY-CATALOG.md` after Matt approve. This draft file preserved unchanged in body; use canon path going forward.

# MODEL C — CANONICAL CAPABILITY CATALOG DRAFT v2

**Status:** DRAFT FOR FINAL MATT APPROVAL — not yet CANONICAL LOCK  
**Not approved:** new Progress formula · replacing 28% · live scoring  
**Class:** READ-ONLY docs. No dashboard / scoring / application code / DB / Production / Habitat / Uma mutations.  
**Inputs:** v1 draft + constitutional AMEND + Matt decisions (Sale SYSTEM scope; Intercompany near-term IN SCOPE)  
**WHERE:** `docs/deliveries/MODEL-C-CAPABILITY-CATALOG-DRAFT-v2-2026-09-17.md`

---

## Hierarchy

MISSION → DOMAIN → CAPABILITY → REQUIREMENT / CONTROL / TASK / MILESTONE

Only **CAPABILITY** enters the SYSTEM denominator.  
Adoption (entity / brand / property / venue) changes maturity, not capability count.

## Ownership enum

| Tag | Meaning |
| --- | --- |
| **OWN** | Wolf owns the canonical workflow/capability |
| **INTEGRATE** | External system owns canonical transactional facts; Wolf consumes/orchestrates |
| **OBSERVE** | Wolf reads source data but does not control the system |
| **DERIVE** | Wolf calculates a governed view from canonical sources |

Wolf never claims ownership of ESB or Yanolja transactional truth.

## Out of SYSTEM score

| Item | Treatment |
| --- | --- |
| Personal Command / Trading (Spec §18) | OUT |
| Build Factory health | OUT (HEALTHY/DEGRADED/FAILING dial) |
| Sale 60 diligence cells | CONTROLS under Sale capabilities + future Sale dimension |
| UI pages / API endpoints / agents | Never capabilities |
| Dual Approval | Requirement class under CAP-CORE-07 Approval Engine |

## Model E dimensions (definitions only — no scores)

1. **SYSTEM** — this catalog  
2. **OPERATING ADOPTION** — humans using capabilities  
3. **DATA / MEASUREMENT** — trustworthy metrics  
4. **FOUNDER INDEPENDENCE** — intentional authority vs accidental dependency  
5. **FINANCIAL CONTROL** — books, cash, leakage, close  
6. **SALE READINESS** — buyer evidence / VDR / transition  

---

## Domains and capabilities

### D-CORE — Wolf Core (12)

| ID | Capability | Ownership | Scope | Intent / adoption |
| --- | --- | --- | --- | --- |
| CAP-CORE-01 | Organisation Registry | OWN | SHARED | Canonical Group→Entity→Brand→Location→Dept hierarchy. |
| CAP-CORE-02 | Person & Auth Identity | OWN | SHARED | Permanent Person; CF JWT → Person binding. |
| CAP-CORE-03 | Role / Position / Assignment | OWN | SHARED | Jobs change without losing history. |
| CAP-CORE-04 | Permission & Authority Engine | OWN | SHARED | Deterministic server-enforced RBAC. |
| CAP-CORE-05 | Authority Limits Evaluator | OWN | SHARED | Amount/scope limits on actions. |
| CAP-CORE-06 | Work Items / Promises / Decisions | OWN | SHARED | Material promises leave a defensible trail. |
| CAP-CORE-07 | Approval Engine | OWN | SHARED | Human authority for material decisions; Dual Approval is a requirement class inside this capability when policy demands two persons. |
| CAP-CORE-08 | Segregation of Duties | OWN | SHARED | Conflicting duties cannot combine end-to-end. |
| CAP-CORE-09 | Evidence Requirements | OWN | SHARED | Mandatory evidence before approve/live. |
| CAP-CORE-10 | Exception / Override Governance | OWN | SHARED | Break-glass logged and reviewable. |
| CAP-CORE-11 | SOP Factory | OWN | SHARED | Full loop: real work → evidence → learning → proposed SOP change → approval → versioning → training/acknowledgement → operational use; no silent history rewrite. |
| CAP-CORE-12 | Delegation & Escalation Burn-down | OWN | SHARED | Distinguish intentional Owner authority from accidental founder dependency; delegations time-bounded; escalation burn-down measurable; supports 7/30/90/365 independence tests. |

### D-GGV — GGV (6)

| ID | Capability | Ownership | Scope | Intent / adoption |
| --- | --- | --- | --- | --- |
| CAP-GGV-01 | Content Machine | OWN | GGV | Strategy→plan→asset→workflow→learn for agency and brand content. |
| CAP-GGV-02 | Publish Gate & Operator Loop | OWN | GGV | Work Item + draft evidence + designated approvers + human operator loop before publish. Adoption: Habitat = first adoption; future brands reuse same capability. |
| CAP-GGV-03 | Client Profitability | OWN | GGV | Client/contract/project/deliverable P&L with staff and external cost allocation — machinery toward GGV ~70% operating-profit target (TARGET≠ACTUAL). |
| CAP-GGV-04 | Lead Triage & Speed-to-Lead | OWN | GGV | Hot leads answered/escalated from approved facts; uncertainty escalates. |
| CAP-GGV-05 | Brand Social Performance | DERIVE | GGV | Governed social performance views for brands. Adoption: Consumes Metricool via CAP-INTG-05 (INTEGRATE); does not own Metricool. |
| CAP-GGV-06 | Intercompany Client Mode | OWN | GGV | AMG/BZG as formal internal clients of GGV: service records, invoices, allocation, arms-length evidence, AR/AP treatment, audit trail. Near-term after Habitat/Uma commissioning; before Finance/Procurement maturity claim. Tax treatment OUT of this catalog. |

### D-AMG — AMG (7)

| ID | Capability | Ownership | Scope | Intent / adoption |
| --- | --- | --- | --- | --- |
| CAP-AMG-01 | Hotel PMS Orchestration | OWN | AMG | Wolf orchestrates staffing, tasks, intelligence, reporting from PMS facts. Adoption: Yanolja owns reservation/PMS transactional truth (CAP-INTG-01 INTEGRATE). Additional hotels = property adoption, not catalog clone. |
| CAP-AMG-02 | Guest Journey Operations | OWN | AMG | Enquiry→booking→pre-arrival→arrival→stay→checkout→return memory as one journey capability. |
| CAP-AMG-03 | Packages as Products | OWN | AMG | Stay+activity packages as first-class commercial products with margin/SOP. |
| CAP-AMG-04 | Daily Hotel Operating State | OWN | AMG | Machine-generated daily ops (occupancy, ARR, arrivals/departures, OOO, forecast); housekeeping/room queues as requirements under this capability. |
| CAP-AMG-05 | Hotel Revenue & Yield | OWN | AMG | Rates, occupancy, ADR/RevPAR visibility — machinery toward AMG ~20% operating-profit target (TARGET≠ACTUAL). |
| CAP-AMG-06 | Guest Experience Loop | OWN | AMG | Requests/incidents with SLA/escalation; memorable service trail. |
| CAP-AMG-07 | Service Improvement Loop | OWN | AMG | Review evidence → recognition/training/process improvement (reviews earned, never solicited). |

### D-BZG — BZG (7)

| ID | Capability | Ownership | Scope | Intent / adoption |
| --- | --- | --- | --- | --- |
| CAP-BZG-01 | F&B POS Orchestration | OWN | BZG | Wolf controls intelligence, finance, procurement, risk and cross-system workflows from POS facts. Adoption: ESB owns detailed F&B stock/transaction truth (CAP-INTG-02 INTEGRATE). |
| CAP-BZG-02 | Venue P&L & Management Rollup | OWN | BZG | Each venue mini-business budget/KPI/dashboard; BZG Master rollup — machinery toward BZG ~20% operating-profit target (TARGET≠ACTUAL). Adoption: Venues adopt; adding venues does not clone this capability. |
| CAP-BZG-03 | Venue Daily Close | OWN | BZG | Daily close + exception handover + cash chain requirements (float→bank). Adoption: Uma Blu = first adoption; Rainforest/Merah/Rooftop = future adoption — not new capabilities. |
| CAP-BZG-04 | Inventory & Stock Control | OWN | BZG | Theoretical vs actual variances, waste/comps/voids analysed; ESB remains transactional SoT. |
| CAP-BZG-05 | Central Kitchen & Shared Cost Allocation | OWN | BZG | Evidence-based shared cost allocation across venues. |
| CAP-BZG-06 | Recipe / Cost Standards | OWN | BZG | BOM, yield/waste, theoretical cost, menu-engineering analysis. |
| CAP-BZG-07 | Review & Reputation Capture | OBSERVE | BZG | Reviews earned organically; signal into training/process — Wolf observes/derives, does not solicit. |

### D-HR — HR / People (5)

| ID | Capability | Ownership | Scope | Intent / adoption |
| --- | --- | --- | --- | --- |
| CAP-HR-01 | People Master Record | OWN | SHARED | Canonical employee/position/assignment truth per legal entity. |
| CAP-HR-02 | Hiring & Onboarding | OWN | SHARED | Manpower→recruit→onboard→probation workflows. |
| CAP-HR-03 | Training & Competency | OWN | SHARED | Training/acknowledgement after SOP changes; competency checks before LIVE. |
| CAP-HR-04 | Payroll Inputs | OWN | SHARED | Clean attendance/leave/pay inputs to finance. |
| CAP-HR-05 | Retention & Succession Signals | OWN | SHARED | People risk and succession visibility without accidental Matt dependency. |

### D-FIN — Finance / Accounting (8)

| ID | Capability | Ownership | Scope | Intent / adoption |
| --- | --- | --- | --- | --- |
| CAP-FIN-01 | Wolf Accounting Core | OWN | SHARED | Official accounting per legal entity + group mapping for consolidation. |
| CAP-FIN-02 | Bank Statement Ingest & Reconcile | INTEGRATE | SHARED | Weekly/monthly statement upload→reconcile until proven bank APIs. Adoption: Banks own account truth; Wolf ingests files (CAP-INTG-04). |
| CAP-FIN-03 | Entity Finance Boards | OWN | SHARED | Per-entity finance operating surfaces (GGV/Atrium/Uma adoption). Adoption: Replaces former Atrium Finance Wire as AMG-specific capability. |
| CAP-FIN-04 | Invoicing & Receivables | OWN | SHARED | Issue/correct invoices; AR trail. |
| CAP-FIN-05 | Management Reporting | OWN | SHARED | P&L, BS, cash flow, trial balance, management accounts; TARGET≠ACTUAL vs margin goals. |
| CAP-FIN-06 | Intercompany Billing | OWN | SHARED | Arms-length invoices/allocation/AR-AP between GGV↔AMG/BZG paired with CAP-GGV-06. Tax treatment deferred. |
| CAP-FIN-07 | Budget / Forecast / Cash Cadence | OWN | SHARED | Annual budget + rolling forecast + 13-week cash per entity; updates as evidence arrives. |
| CAP-FIN-08 | Profit Leakage Intelligence | OWN | SHARED | Continuous identification of waste, variance, discounts, OOO, unprofitable items, overservicing, subscription waste, preventable maintenance — supports margin targets without embedding targets in every cap. |

### D-PROC — Procurement (3)

| ID | Capability | Ownership | Scope | Intent / adoption |
| --- | --- | --- | --- | --- |
| CAP-PROC-01 | Supplier Register & Intelligence | OWN | SHARED | Suppliers with price/quality/reliability/concentration visibility. |
| CAP-PROC-02 | Purchase & Approval Flow | OWN | SHARED | Request→quotes→PO→receive→match→pay approval; SoD enforced. |
| CAP-PROC-03 | Payment Tracking | OWN | SHARED | Payment runs prepared/tracked; PAID only with settlement evidence. Initiation may remain outside Wolf. |

### D-CRM — Customer / CRM / Packages (4)

| ID | Capability | Ownership | Scope | Intent / adoption |
| --- | --- | --- | --- | --- |
| CAP-CRM-01 | Lead CRM | OWN | SHARED | Leads owned, aged, followed with client-data boundaries. |
| CAP-CRM-02 | Customer Identity & Memory | OWN | SHARED | Canonical Customer ID / identity graph with confidence matching; human review when uncertain. |
| CAP-CRM-03 | Package Intelligence | OWN | SHARED | Package performance, margin, demand across channels. |
| CAP-CRM-04 | Email Marketing Wire | INTEGRATE | SHARED | Brand email where applicable; connector honesty (Klaviyo/AC not conflated). |

### D-MSC — Maintenance / Security / Compliance (5)

| ID | Capability | Ownership | Scope | Intent / adoption |
| --- | --- | --- | --- | --- |
| CAP-MSC-01 | Asset & Maintenance Register | OWN | SHARED | Asset condition and maintenance tracked. |
| CAP-MSC-02 | Access & Cloudflare Posture | OWN | SHARED | Seats, doors, Access includes; Matt-owned flips preserved. |
| CAP-MSC-03 | Compliance Pack | OWN | SHARED | Licences, statutory, policy compliance evidence. |
| CAP-MSC-04 | Cybersecurity Baseline | OWN | SHARED | MFA, device posture, audited access; crown-jewel adjacent but not DR playbook. |
| CAP-MSC-05 | Documents / Records / Legal Defensibility | OWN | SHARED | Callable context-aware records; retention; legal hold; dispute chronology; contract intelligence; no silent destroy of audit evidence. |

### D-STRAT — Strategy / Command (2)

| ID | Capability | Ownership | Scope | Intent / adoption |
| --- | --- | --- | --- | --- |
| CAP-STRAT-01 | 12-Week Year Cadence | OWN | SHARED | Vision→annual→12WY→department→individual; activity≠outcome. |
| CAP-STRAT-02 | Owner Radar / Mission Control | OWN | SHARED | Pulse + Exceptions; bird's-eye until satisfied; progressive quiet. Priority discipline is a requirement of this cadence, not a separate capability. |

### D-INTEL — Wolf Intelligence (5)

| ID | Capability | Ownership | Scope | Intent / adoption |
| --- | --- | --- | --- | --- |
| CAP-INTEL-01 | Orchestration / Reasoning Surface | OWN | SHARED | One institutional WI experience; DATA→TOOLS→REASONING→SYNTHESIS→HUMAN; no agent zoo. |
| CAP-INTEL-02 | Authorised Retrieval & Institutional Memory | OWN | SHARED | Search authorised sources; Brand Memory vs Learning Memory separated; empty≠UNKNOWN. |
| CAP-INTEL-03 | Provenance / Confidence / Conflict Resolution | OWN | SHARED | Evidence classes; confidence; conflict/supersession; approved truth outranks model observations. |
| CAP-INTEL-04 | Decision Memory | OWN | SHARED | Material decisions, options considered, approvals, outcomes preserved and recallable. |
| CAP-INTEL-05 | Learning / Experiments / Performance Policy | OWN | SHARED | Observation→lesson candidate→human approve→rule; performance learning; noise suppression — not a capability per persona. |

### D-INTG — Integrations / Infrastructure (7)

| ID | Capability | Ownership | Scope | Intent / adoption |
| --- | --- | --- | --- | --- |
| CAP-INTG-01 | Yanolja Connector | INTEGRATE | SHARED | Reservation/PMS facts into Wolf. Adoption: Yanolja owns transactional truth. |
| CAP-INTG-02 | ESB Connector | INTEGRATE | SHARED | F&B sales/inventory/ops facts into Wolf. Adoption: ESB owns transactional truth. |
| CAP-INTG-03 | Google Workspace Connector | INTEGRATE | SHARED | Mail/calendar/documents/auth as authorised. |
| CAP-INTG-04 | Bank Statement Connector | INTEGRATE | SHARED | Statement file import path for finance reconcile. |
| CAP-INTG-05 | Metricool Connector | INTEGRATE | SHARED | Social performance data into Wolf. Adoption: Metricool owns platform analytics. |
| CAP-INTG-06 | Technology & Capability Registries | OWN | SHARED | Tech inventory, ownership of truth, lifecycle, exit conditions. |
| CAP-INTG-07 | Secrets & Environment Separation | OWN | SHARED | Secrets management; Dev/Beta/Prod separation; no secrets in SOPs/chats; sanitised test data preference. |

### D-DR — Information / DR (2)

| ID | Capability | Ownership | Scope | Intent / adoption |
| --- | --- | --- | --- | --- |
| CAP-DR-01 | Backup / Restore Testing / Disaster Recovery | OWN | SHARED | Nothing backed up until restore tested; tiered RTO/RPO; business continuity folded here as operating requirement. |
| CAP-DR-02 | Crown Jewel Protection | OWN | SHARED | Crown-jewel identification, independent failure domains, Matt-only full playbook default per Spec. |

### D-SALE — Sale Readiness (4)

| ID | Capability | Ownership | Scope | Intent / adoption |
| --- | --- | --- | --- | --- |
| CAP-SALE-01 | Continuous Sale Evidence Pack | OWN | SHARED | Consumes evidence from Finance/HR/Legal/Ops/Compliance/Tech domains — does NOT clone those capabilities. 60 diligence cells are CONTROLS underneath. |
| CAP-SALE-02 | Buyer Data Room | OWN | SHARED | Continuously updated VDR; diligence becomes controlled access. |
| CAP-SALE-03 | Buyer Mode / Controlled Export | OWN | SHARED | Exposes only approved company-specific diligence data and Ask context; hides crown jewels and cross-company intelligence. |
| CAP-SALE-04 | Buyer Attack & Transition Readiness | OWN | SHARED | Buyer Attack Audit + transition readiness; Wolf licence post-sale boundary preserved. |

## Denominator summary

| Domain | Count |
| --- | ---: |
| Wolf Core | 12 |
| GGV | 6 |
| AMG | 7 |
| BZG | 7 |
| HR / People | 5 |
| Finance / Accounting | 8 |
| Procurement | 3 |
| Customer / CRM / Packages | 4 |
| Maintenance / Security / Compliance | 5 |
| Strategy / Command | 2 |
| Wolf Intelligence | 5 |
| Integrations / Infrastructure | 7 |
| Information / DR | 2 |
| Sale Readiness | 4 |
| **TOTAL** | **77** |

| Scope | Count |
| --- | ---: |
| SHARED | 57 |
| GGV-specific | 6 |
| AMG-specific | 7 |
| BZG-specific | 7 |

## Sale SYSTEM capabilities (Matt decision)

1. CAP-SALE-01 Continuous Sale Evidence Pack  
2. CAP-SALE-02 Buyer Data Room  
3. CAP-SALE-03 Buyer Mode / Controlled Export  
4. CAP-SALE-04 Buyer Attack & Transition Readiness  

60 diligence cells = CONTROLS / EVIDENCE beneath these (and future Sale dimension). Not peer capabilities.

## Granularity invariance (v2 red-team)

| Attack | Result |
| --- | --- |
| Split 1 capability into 100 requirements | PASS — count unchanged |
| Add 10 venues | PASS — Venue Daily Close / Venue P&L adoption only |
| Add second hotel | PASS — AMG Hotel OS property adoption, not clone |
| Add 500 sale diligence checks | PASS — CONTROLS only |
| New UI page / API endpoint | PASS — not a capability |
| New external vendor | PASS — connector adoption / INTEGRATE row; not automatic mission size |

## Profitability machinery (TARGET≠ACTUAL)

GGV ~70% / AMG ~20% / BZG ~20% operating-profit targets are managed via: Client Profitability, Hotel Revenue & Yield, Venue P&L & Rollup, Accounting Core, Management Reporting, Budget/Forecast/Cash, Profit Leakage, Intercompany Billing — not by embedding targets into every capability.

## Explicit non-goals

- No change to displayed 28%  
- No Progress scoring formula change  
- No application code  
- No Intercompany build in this mission  
- No tax treatment design  
- No CANONICAL LOCK until Matt says so  
