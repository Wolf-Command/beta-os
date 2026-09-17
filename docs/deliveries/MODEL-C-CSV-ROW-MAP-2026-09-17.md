> **SUPERSEDED 2026-09-17** — v1 CSV map. Use `MODEL-C-CSV-ROW-MAP-v2-2026-09-17.md` (companion to canon).

# MODEL C CSV ROW MAP — 17 Sep 2026

**Status:** DRAFT companion to capability catalog  
**Factory:** `BF-model-c-capability-catalog-20260917`  
**Rule:** IN_DENOMINATOR only if maps to a CAP-* capability. Sale checklist cells = DEMOTE_TO_CONTROL.

As of: 2026-09-17 ~20:55 WITA

## Legend

| Code | Meaning |
| --- | --- |
| IN_DENOMINATOR | Counts as / merges into the named capability |
| DEMOTE_TO_CONTROL | Maturity evidence under a capability; not a peer row |
| OUT_OF_DENOMINATOR | Explicitly excluded from SYSTEM score |
| UNMAPPED | Needs Matt decision |

## Master_Build.csv (16)

| Source ID | Current label | Map |
| --- | --- | --- |
| MB-001 | Organisation Registry | IN_DENOMINATOR → CAP-CORE-01 |
| MB-002 | Identity / Role / Position / Assignment | IN_DENOMINATOR → CAP-CORE-02 + CAP-CORE-03 |
| MB-003 | Permission & Authority Engine | IN_DENOMINATOR → CAP-CORE-04 |
| MB-004 | Tasks / Promises / Decisions | IN_DENOMINATOR → CAP-CORE-06 |
| MB-005 | Institutional Intelligence Layer | IN_DENOMINATOR → CAP-INTEL-01 |
| MB-006 | Content Machine | IN_DENOMINATOR → CAP-GGV-01 |
| MB-007 | Uma Blu Operating Slice | IN_DENOMINATOR → expands toward CAP-BZG-01..08 (parent stub) |
| MB-008 | Yanolja Operating Slice | IN_DENOMINATOR → expands toward CAP-AMG-01..09 (parent stub) |
| MB-009 | Wolf Accounting | IN_DENOMINATOR → CAP-FIN-01 |
| MB-010 | Wolf Procurement | IN_DENOMINATOR → CAP-PROC parent |
| MB-011 | Wolf HR | IN_DENOMINATOR → CAP-HR parent |
| MB-012 | SOP Factory | IN_DENOMINATOR → CAP-CORE-12 |
| MB-013 | Matt Command | IN_DENOMINATOR → CAP-STRAT-02 |
| MB-014 | Data Room / Buyer Mode | IN_DENOMINATOR → CAP-SALE-01 |
| MB-015 | Technology / Integration / Capability Registries | IN_DENOMINATOR → CAP-INTG-06 |
| MB-016 | Backup & Disaster Recovery | IN_DENOMINATOR → CAP-DR-01 |

## Overlay rows (11)

| Source ID | Map |
| --- | --- |
| OV-AUTH-JWT | IN_DENOMINATOR → CAP-CORE-02 |
| OV-AUTHORITY | IN_DENOMINATOR → CAP-CORE-05 |
| OV-APPROVAL | IN_DENOMINATOR → CAP-CORE-07 |
| OV-DUAL | IN_DENOMINATOR → CAP-CORE-08 |
| OV-SOD | IN_DENOMINATOR → CAP-CORE-09 |
| OV-EVIDENCE | IN_DENOMINATOR → CAP-CORE-10 |
| OV-EXCEPTION | IN_DENOMINATOR → CAP-CORE-11 |
| OV-HABITAT-GATE | IN_DENOMINATOR → CAP-GGV-02 |
| OV-HABITAT-UI | IN_DENOMINATOR → CAP-GGV-03 |
| OV-UMA-CLOSE | IN_DENOMINATOR → CAP-BZG-03 |
| OV-KNOWLEDGE-RULE | IN_DENOMINATOR → CAP-INTEL-02 |

## Integrations.csv (5)

| Source ID | Map |
| --- | --- |
| INT-YAN-WOLF | IN_DENOMINATOR → CAP-INTG-01 |
| INT-ESB-WOLF | IN_DENOMINATOR → CAP-INTG-02 |
| INT-GWS-WOLF | IN_DENOMINATOR → CAP-INTG-03 |
| INT-BANK-WOLF | IN_DENOMINATOR → CAP-INTG-04 |
| INT-MET-WOLF | IN_DENOMINATOR → CAP-INTG-05 |

## Sale_Readiness.csv (60) — all DEMOTE_TO_CONTROL

| Source | Map |
| --- | --- |
| GGV: Finance quality | DEMOTE_TO_CONTROL → CAP-SALE-02 |
| GGV: Profitability / EBITDA | DEMOTE_TO_CONTROL → CAP-SALE-02 |
| GGV: Quality of earnings | DEMOTE_TO_CONTROL → CAP-SALE-02 |
| GGV: Customer concentration | DEMOTE_TO_CONTROL → CAP-SALE-04 |
| GGV: Supplier concentration | DEMOTE_TO_CONTROL → CAP-SALE-04 |
| GGV: Management depth | DEMOTE_TO_CONTROL → CAP-SALE-03 |
| GGV: Founder dependency | DEMOTE_TO_CONTROL → CAP-SALE-03 |
| GGV: SOP coverage | DEMOTE_TO_CONTROL → CAP-SALE-03 |
| GGV: Training coverage | DEMOTE_TO_CONTROL → CAP-SALE-03 |
| GGV: Compliance | DEMOTE_TO_CONTROL → CAP-SALE-04 |
| GGV: Contract quality | DEMOTE_TO_CONTROL → CAP-SALE-04 |
| GGV: Data quality | DEMOTE_TO_CONTROL → CAP-SALE-04 |
| GGV: Technology portability | DEMOTE_TO_CONTROL → CAP-SALE-04 |
| GGV: Cybersecurity | DEMOTE_TO_CONTROL → CAP-SALE-04 |
| GGV: Asset condition | DEMOTE_TO_CONTROL → CAP-SALE-04 |
| GGV: Brand/IP ownership | DEMOTE_TO_CONTROL → CAP-SALE-04 |
| GGV: Employee retention | DEMOTE_TO_CONTROL → CAP-SALE-03 |
| GGV: Succession | DEMOTE_TO_CONTROL → CAP-SALE-03 |
| GGV: Operational consistency | DEMOTE_TO_CONTROL → CAP-SALE-03 |
| GGV: Growth opportunities | DEMOTE_TO_CONTROL → CAP-SALE-04 |
| AMG: Finance quality | DEMOTE_TO_CONTROL → CAP-SALE-02 |
| AMG: Profitability / EBITDA | DEMOTE_TO_CONTROL → CAP-SALE-02 |
| AMG: Quality of earnings | DEMOTE_TO_CONTROL → CAP-SALE-02 |
| AMG: Customer concentration | DEMOTE_TO_CONTROL → CAP-SALE-04 |
| AMG: Supplier concentration | DEMOTE_TO_CONTROL → CAP-SALE-04 |
| AMG: Management depth | DEMOTE_TO_CONTROL → CAP-SALE-03 |
| AMG: Founder dependency | DEMOTE_TO_CONTROL → CAP-SALE-03 |
| AMG: SOP coverage | DEMOTE_TO_CONTROL → CAP-SALE-03 |
| AMG: Training coverage | DEMOTE_TO_CONTROL → CAP-SALE-03 |
| AMG: Compliance | DEMOTE_TO_CONTROL → CAP-SALE-04 |
| AMG: Contract quality | DEMOTE_TO_CONTROL → CAP-SALE-04 |
| AMG: Data quality | DEMOTE_TO_CONTROL → CAP-SALE-04 |
| AMG: Technology portability | DEMOTE_TO_CONTROL → CAP-SALE-04 |
| AMG: Cybersecurity | DEMOTE_TO_CONTROL → CAP-SALE-04 |
| AMG: Asset condition | DEMOTE_TO_CONTROL → CAP-SALE-04 |
| AMG: Brand/IP ownership | DEMOTE_TO_CONTROL → CAP-SALE-04 |
| AMG: Employee retention | DEMOTE_TO_CONTROL → CAP-SALE-03 |
| AMG: Succession | DEMOTE_TO_CONTROL → CAP-SALE-03 |
| AMG: Operational consistency | DEMOTE_TO_CONTROL → CAP-SALE-03 |
| AMG: Growth opportunities | DEMOTE_TO_CONTROL → CAP-SALE-04 |
| BZG: Finance quality | DEMOTE_TO_CONTROL → CAP-SALE-02 |
| BZG: Profitability / EBITDA | DEMOTE_TO_CONTROL → CAP-SALE-02 |
| BZG: Quality of earnings | DEMOTE_TO_CONTROL → CAP-SALE-02 |
| BZG: Customer concentration | DEMOTE_TO_CONTROL → CAP-SALE-04 |
| BZG: Supplier concentration | DEMOTE_TO_CONTROL → CAP-SALE-04 |
| BZG: Management depth | DEMOTE_TO_CONTROL → CAP-SALE-03 |
| BZG: Founder dependency | DEMOTE_TO_CONTROL → CAP-SALE-03 |
| BZG: SOP coverage | DEMOTE_TO_CONTROL → CAP-SALE-03 |
| BZG: Training coverage | DEMOTE_TO_CONTROL → CAP-SALE-03 |
| BZG: Compliance | DEMOTE_TO_CONTROL → CAP-SALE-04 |
| BZG: Contract quality | DEMOTE_TO_CONTROL → CAP-SALE-04 |
| BZG: Data quality | DEMOTE_TO_CONTROL → CAP-SALE-04 |
| BZG: Technology portability | DEMOTE_TO_CONTROL → CAP-SALE-04 |
| BZG: Cybersecurity | DEMOTE_TO_CONTROL → CAP-SALE-04 |
| BZG: Asset condition | DEMOTE_TO_CONTROL → CAP-SALE-04 |
| BZG: Brand/IP ownership | DEMOTE_TO_CONTROL → CAP-SALE-04 |
| BZG: Employee retention | DEMOTE_TO_CONTROL → CAP-SALE-03 |
| BZG: Succession | DEMOTE_TO_CONTROL → CAP-SALE-03 |
| BZG: Operational consistency | DEMOTE_TO_CONTROL → CAP-SALE-03 |
| BZG: Growth opportunities | DEMOTE_TO_CONTROL → CAP-SALE-04 |

## Capabilities.csv extras

| Source ID | Map |
| --- | --- |
| CAP-CONTENT-SHELL | IN_DENOMINATOR → CAP-GGV-01 (alias) |
| CAP-WI-MULTI | OUT_OF_DENOMINATOR (NOT TARGET) |
| CAP-MET-READ | IN_DENOMINATOR → CAP-GGV-06 / CAP-INTG-05 |
| CAP-YAN-API | IN_DENOMINATOR → CAP-INTG-01 / CAP-AMG-01 |
| CAP-ESB-API | IN_DENOMINATOR → CAP-INTG-02 / CAP-BZG-01 |
| CAP-FIN | IN_DENOMINATOR → CAP-FIN-01 |
| CAP-PROC | IN_DENOMINATOR → CAP-PROC parent |

## Founder_Dependency.csv (4)

| Source ID | Map |
| --- | --- |
| FD-001..004 | DEMOTE_TO_CONTROL → CAP-SALE-03 (+ Model E FOUNDER INDEPENDENCE dial) |

## Commissioning.csv

All commissioning checklist columns = EVIDENCE on the named release capability, not denominator rows.

## Counts

| Class | Count |
| --- | ---: |
| Current scored tracker rows (approx) | 92 |
| Sale rows demoted to CONTROL | 60 |
| Proposed Model C capabilities (denominator) | 78 |
| OUT_OF_DENOMINATOR explicit | Personal Command; Factory health; CAP-WI-MULTI |
| UNMAPPED needing Matt | Spec §16 Legal depth; non-Uma BZG outlets; Trading |

## Integrity check

IN_DENOMINATOR capability count must stay stable when Sale controls are split or merged.
