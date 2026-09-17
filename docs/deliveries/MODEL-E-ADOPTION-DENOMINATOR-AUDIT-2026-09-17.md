# MODEL E — ADOPTION DENOMINATOR AUDIT (DISCOVERY)

**Status:** DISCOVERY — not locked
**Date:** 2026-09-17
**WHERE:** `docs/deliveries/MODEL-E-ADOPTION-DENOMINATOR-AUDIT-2026-09-17.md`

## Counts

- REQUIRED: 26
- PLANNED: 17
- DEFERRED: 1
- NOT APPLICABLE: 1
- Candidate AUs total: 45
- Future Adoption denominator if locked today: **26**

## REQUIRED AUs — why they belong

### `AU-GGV-02-HABITAT`
- CAP: `CAP-GGV-02` · Scope: Habitat Content operation (ENT-GGV / SCOPE-GGV-CONTENT / brand habitat)
- Why REQUIRED: Canon HABITAT-PUBLISH-GATE; first Content Machine adoption; live GPO/EVR; human commissioning ordered
- State: **NOT STARTED**

### `AU-BZG-03-UMA`
- CAP: `CAP-BZG-03` · Scope: Uma Blu (BZG-UMA)
- Why REQUIRED: Canon UMA-BLU-DAILY-CLOSE; Uma operational; Wolf close slice scoped Uma only; discovery confirms daily loop
- State: **NOT STARTED**

### `AU-CORE-02-WOLF-SEATS`
- CAP: `CAP-CORE-02` · Scope: Required authenticated Wolf seat cohort (GGV content + Owner seats currently seeded; CF Access doors)
- Why REQUIRED: Real Auth binding LIVE; CF Access is the door; staff must authenticate to use Wolf
- State: **ADOPTED**

### `AU-CORE-04-WOLF-RBAC`
- CAP: `CAP-CORE-04` · Scope: Wolf operators subject to server RBAC (same seat cohort as auth)
- Why REQUIRED: RBAC enforced on Beta boards; seats experience allow/deny
- State: **ADOPTED**

### `AU-CORE-07-HABITAT-PUBLISH`
- CAP: `CAP-CORE-07` · Scope: Habitat content publish approvals (ENT-GGV / SCOPE-GGV-CONTENT)
- Why REQUIRED: GPO-HABITAT-CONTENT-PUBLISH live; Core Approval canonical for Habitat publish
- State: **NOT STARTED**

### `AU-CORE-06-HABITAT-PUBLISH`
- CAP: `CAP-CORE-06` · Scope: Habitat publish Work Items
- Why REQUIRED: Publish gate uses Work Item + evidence trail
- State: **NOT STARTED**

### `AU-CORE-09-HABITAT-PUBLISH`
- CAP: `CAP-CORE-09` · Scope: Habitat content publish evidence (EVR-HABITAT-CONTENT-PUBLISH)
- Why REQUIRED: Live evidence requirement seeded for Habitat publish
- State: **NOT STARTED**

### `AU-CORE-06-UMA-EXCEPTION`
- CAP: `CAP-CORE-06` · Scope: Uma Blu close exception Work Items → Head of F&B
- Why REQUIRED: Uma close exception path assigns WI to HoF&B role
- State: **NOT STARTED**

### `AU-FIN-03-GGV`
- CAP: `CAP-FIN-03` · Scope: GGV Finance operators
- Why REQUIRED: ENT-GGV finance board is live operating surface; staff expected to use Wolf board for entity finance
- State: **NOT STARTED**

### `AU-FIN-03-AMG`
- CAP: `CAP-FIN-03` · Scope: Atrium Finance (Zayen board path)
- Why REQUIRED: ENT-AMG finance board is live operating surface; staff expected to use Wolf board for entity finance
- State: **NOT STARTED**

### `AU-FIN-03-BZG`
- CAP: `CAP-FIN-03` · Scope: BZG/Uma finance surfaces
- Why REQUIRED: ENT-BZG finance board is live operating surface; staff expected to use Wolf board for entity finance
- State: **NOT STARTED**

### `AU-FIN-04-GGV-INVOICE`
- CAP: `CAP-FIN-04` · Scope: GGV invoicing (Amanda desk / Habitat sale invoices)
- Why REQUIRED: Amanda invoice Save→Issue is live GGV operating path
- State: **NOT STARTED**

### `AU-FIN-02-BANK-INGEST`
- CAP: `CAP-FIN-02` · Scope: Group bank statement upload/reconcile (GGV+BZG+AMG accounts)
- Why REQUIRED: Standing monthly bank file process; no Indonesian bank feed — statement upload required
- State: **NOT STARTED**

### `AU-GGV-01-HABITAT`
- CAP: `CAP-GGV-01` · Scope: Habitat content production machine
- Why REQUIRED: Habitat is first Content Machine adoption brand; team operates content boards
- State: **NOT STARTED**

### `AU-CRM-01-HABITAT`
- CAP: `CAP-CRM-01` · Scope: Habitat leads board
- Why REQUIRED: Habitat leads live operating board
- State: **NOT STARTED**

### `AU-INTG-05-HABITAT`
- CAP: `CAP-INTG-05` · Scope: Habitat social performance read path
- Why REQUIRED: Metricool read used for Habitat numbers; write fail-closed intentional
- State: **NOT STARTED**

### `AU-GGV-05-HABITAT`
- CAP: `CAP-GGV-05` · Scope: Habitat governed social performance views
- Why REQUIRED: DERIVE views for Habitat Numbers
- State: **NOT STARTED**

### `AU-STRAT-02-OWNER`
- CAP: `CAP-STRAT-02` · Scope: Matt Owner Radar / Progress / Wolf NOW
- Why REQUIRED: Owner is intended operator of Radar/Progress
- State: **NOT STARTED**

### `AU-STRAT-01-GGV`
- CAP: `CAP-STRAT-01` · Scope: GGV 12WY / Helm cadence
- Why REQUIRED: 12WY locked as operating framework for GGV
- State: **NOT STARTED**

### `AU-CORE-01-WOLF-ORG`
- CAP: `CAP-CORE-01` · Scope: Wolf operators maintaining Org Registry (Owner/Peaches-governed seeds)
- Why REQUIRED: Org registry is live Beta truth for entities/brands/scopes
- State: **NOT STARTED**

### `AU-CORE-03-GGV-CONTENT-ROLES`
- CAP: `CAP-CORE-03` · Scope: GGV content assignments (Amanda/Haikal/Misa/Matt seeded)
- Why REQUIRED: Assignments seeded and used for Habitat scope
- State: **ADOPTED**

### `AU-MSC-02-CF-DOORS`
- CAP: `CAP-MSC-02` · Scope: Wolf CF Access door/seat management (Matt-owned flips)
- Why REQUIRED: CF Access is live security posture; Matt owns Include flips
- State: **NOT STARTED**

### `AU-INTEL-02-WOLF`
- CAP: `CAP-INTEL-02` · Scope: Wolf Ask/authorised retrieval operators (Owner + staff Ask Peaches)
- Why REQUIRED: Ask Peaches / authorised knowledge rule is live operating expectation
- State: **NOT STARTED**

### `AU-INTG-02-UMA`
- CAP: `CAP-INTG-02` · Scope: Uma Blu / BZG Wolf↔ESB boundary (close snapshot + warehouse)
- Why REQUIRED: Uma close depends on ESB fingerprint; ESB intentional SoT
- State: **NOT STARTED**

### `AU-CORE-08-UMA-CLOSE-SOD`
- CAP: `CAP-CORE-08` · Scope: Uma Blu close SoD (resolver ≠ sole verifier)
- Why REQUIRED: SoD built into Uma close exception path
- State: **NOT STARTED**

### `AU-CORE-10-UMA-EXCEPTION`
- CAP: `CAP-CORE-10` · Scope: Uma Blu close exceptions
- Why REQUIRED: Exception path in Uma close
- State: **NOT STARTED**

## PLANNED (out of denominator)

- `AU-BZG-03-RAINFOREST`: Earlier-stage per BZG ops discovery; not in Uma close slice · Trigger: Venue operational commissioning + approved Wolf Daily Close rollout
- `AU-BZG-03-MERAH`: Earlier-stage; not Wolf close scoped · Trigger: Venue operational commissioning + approved Wolf Daily Close rollout
- `AU-BZG-03-ROOFTOP`: Earlier-stage; not Wolf close scoped · Trigger: Venue operational commissioning + approved Wolf Daily Close rollout
- `AU-BZG-03-CATERING`: Not evidenced as operational Wolf close scope · Trigger: Venue operational commissioning + approved Wolf Daily Close rollout
- `AU-BZG-03-ROOM-SERVICE`: Not evidenced as operational Wolf close scope · Trigger: Venue operational commissioning + approved Wolf Daily Close rollout
- `AU-CORE-05-AMOUNT-GATES`: Evaluator SYSTEM PROVEN but live monetary Authority Limits intentionally 0; Habitat policies non-monetary · Trigger: First non-zero live Authority Limit policy approved for an operating workflow
- `AU-AMG-01-ATRIUM`: Atrium operational on Yanolja; Wolf PMS orchestration CAP not built (SYSTEM SPECIFIED); Yanolja daily use ≠ Wolf AU · Trigger: Wolf Yanolja connector + orchestration READY + approved rollout
- `AU-INTG-01-ATRIUM`: SYSTEM ABSENT for connector; no Wolf AU required until connector exists · Trigger: CAP-INTG-01 reaches READY + Atrium rollout approve
- `AU-GGV-02-ATRIUM`: Produce brand active; publish-gate reuse not yet REQUIRED rollout · Trigger: Approved Wolf publish-gate rollout for Atrium
- `AU-GGV-02-TROPIK`: Active produce brand; not first gate adoption · Trigger: Approved rollout
- `AU-GGV-02-SELO`: Active produce brand; not first gate adoption · Trigger: Approved rollout
- `AU-GGV-02-UMA`: Content board exists; Daily Close is separate AU · Trigger: Approved content-gate rollout if required
- `AU-PROC-02-GROUP`: Catalog SPECIFIED; Alchemist/ESB/Notion still primary; Wolf PO not REQUIRED rollout yet · Trigger: Approved Wolf purchase-flow rollout replacing shadow for named entity
- `AU-HR-01-GROUP`: People Master SYSTEM BUILT partial; Beta org_persons incomplete for BZG/AMG; not yet REQUIRED replacement of Notion HR · Trigger: HR people-master REQUIRED rollout + SYSTEM READY/PROVEN as applicable
- `AU-SALE-02-VDR`: SYSTEM SPECIFIED; no continuous VDR operating requirement due today · Trigger: Sale process / VDR operating cadence approved as REQUIRED
- `AU-GGV-06-IC`: Matt IN SCOPE near-term after Habitat/Uma; not build/adopt this mission yet · Trigger: Habitat/Uma progress + Intercompany mode go-live approve
- `AU-BZG-07-UMA-REVIEWS`: OBSERVE CAP SYSTEM SPECIFIED; not due as Wolf control path today · Trigger: Approved Wolf review-signal rollout

## DEFERRED

- `AU-CORE-12-INDEPENDENCE`: Delegation module BUILT; full burn-down/7-30-90-365 independence tests not operating requirement yet; Founder Independence dimension owns scoring later · Trigger: Matt approve independence-test operating cadence as REQUIRED

## NOT APPLICABLE

- `AU-BZG-03-ATRIUM-HOTEL-NA`: Venue Daily Close is BZG F&B venue close capability; Atrium hotel ops are AMG/PMS domain — wrong CAP for hotel night audit

## Special real cases

| Case | Result |
| --- | --- |
| Habitat Publish Gate | `AU-GGV-02-HABITAT` REQUIRED · NOT STARTED (commissioning waiting) |
| Uma Blu Daily Close | `AU-BZG-03-UMA` REQUIRED · NOT STARTED (no verified closer); Rainforest/Merah/Rooftop/Catering/Room Service PLANNED |
| Person/Auth | `AU-CORE-02-WOLF-SEATS` REQUIRED cohort · ADOPTED (real CF seats); not per-employee |
| Approval Engine | `AU-CORE-07-HABITAT-PUBLISH` REQUIRED · NOT STARTED; further entity scopes only when policies go live |
| Authority Limits | `AU-CORE-05-AMOUNT-GATES` PLANNED — live limits 0; trigger = first non-zero policy |
| Yanolja | `AU-AMG-01-ATRIUM` + `AU-INTG-01-ATRIUM` PLANNED; daily PMS use ≠ Wolf AU |

## Denominator red team

| Attack | Result |
| --- | --- |
| 77×entity×venue×role Cartesian | PASS — not used |
| Employee-count inflation | PASS — cohort scopes |
| Future venue dilution | PASS — PLANNED until trigger |
| Yanolja use as Wolf adoption | PASS — PLANNED Wolf AUs |
| ESB as shadow | PASS — intentional SoT |
| Authority Limits REQUIRED while limits=0 | PASS — PLANNED |
| Hiding required Habitat/Uma as PLANNED | PASS — both REQUIRED |

## Questionable REQUIRED (for Matt review before lock)

These are REQUIRED on applicability evidence but SYSTEM < PROVEN so adoption stays NOT STARTED — grain may be revisited:
- `AU-CRM-01-HABITAT`
- `AU-FIN-02-BANK-INGEST`
- `AU-FIN-03-AMG`
- `AU-FIN-03-BZG`
- `AU-FIN-03-GGV`
- `AU-FIN-04-GGV-INVOICE`
- `AU-GGV-01-HABITAT`
- `AU-GGV-05-HABITAT`
- `AU-INTEL-02-WOLF`
- `AU-INTG-02-UMA`
- `AU-INTG-05-HABITAT`
- `AU-MSC-02-CF-DOORS`
- `AU-STRAT-01-GGV`
- `AU-STRAT-02-OWNER`

## Questionable exclusions

- None material: future BZG venues and non-Habitat publish brands correctly PLANNED; Authority Limits correctly PLANNED while live limits=0.

NUMERIC ADOPTION CREDITS SELECTED: NO
ADOPTION % CALCULATED: NO
SYSTEM 22.3% CHANGED: NO
