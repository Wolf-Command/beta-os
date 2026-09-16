# Master Build Dashboard — Builder README

**Canonical build-control register for Wolf Command.**

Source workbook (do not alter; update via deliberate registry edits when architecture/build decisions change):

`docs/canon/source/Wolf_Command_Master_Build_Dashboard_v1.xlsx`

Machine-readable exports of every tab (one CSV per sheet):

`docs/canon/build-dashboard/`

---

## What this workbook is

This workbook is the **canonical build-control register**.

It is not decorative documentation. It is the approved structure and build-state surface builders must keep current when architecture or build decisions change.

- **THE MASTER SPECIFICATION DEFINES INTENT.**
- **THE REGISTRIES DEFINE CURRENT APPROVED STRUCTURE AND BUILD STATE.**
- **THE CODE MUST NOT SILENTLY CONTRADICT EITHER.**

If code and canon conflict, **STOP** and surface the conflict before inventing a third answer.

---

## Hard truth labels

**CLAIMED ≠ VERIFIED.**

**DESIGNED ≠ BUILT ≠ TESTED ≠ LIVE.**

Workbook build rule (from README tab): `DESIGNED != BUILT != VERIFIED != LIVE.`

Change rule: `RED TEAM -> BETA -> VERIFY -> HUMAN APPROVAL -> PRODUCTION -> MEASURE.`

---

## Tabs (19) and what each controls

| Tab | CSV export | Controls |
| --- | --- | --- |
| README | `README.csv` | Purpose, north star, UX principle, build/change/daily rules for this register |
| Master Build | `Master_Build.csv` | Master capability/module backlog: ID, domain, priority, status, owner, deps, acceptance gate, next action |
| Organisation | `Organisation.csv` | Legal entities, ownership, saleability, Wolf licence model |
| Brands_Locations | `Brands_Locations.csv` | Brands/business units, locations, ops systems, P&L and shared services |
| Identity_Roles | `Identity_Roles.csv` | Roles/positions, login identity, dashboards, approval authority |
| Permissions | `Permissions.csv` | Permission matrix: role, scope, resource, action, limits, audit |
| Technology | `Technology.csv` | Technology inventory: why it exists, ownership of truth, lifecycle, exit conditions |
| Integrations | `Integrations.csv` | Integration contracts: source/target, data, method, fallback, error handling |
| Data_Sources | `Data_Sources.csv` | Authoritative data sources and ownership |
| Capabilities | `Capabilities.csv` | Capability register and status |
| SOP_Register | `SOP_Register.csv` | SOP inventory and linkage |
| KPI_Register | `KPI_Register.csv` | KPI definitions, owners, cadence, targets |
| Risks | `Risks.csv` | Risk register with mitigation and status |
| Decisions_Promises | `Decisions_Promises.csv` | Locked decisions and commitments (constitutional locks live here) |
| Sale_Readiness | `Sale_Readiness.csv` | Per-entity sale-readiness evidence gaps |
| Founder_Dependency | `Founder_Dependency.csv` | Founder dependency burn-down items |
| Interview_Ledger | `Interview_Ledger.csv` | Interview rounds → locked requirements → build implications |
| Commissioning | `Commissioning.csv` | Go-live commissioning checklist (architecture/security/permissions/tests/LIVE?) |
| Not_Yet | `Not_Yet.csv` | Explicitly deferred ideas and reconsideration triggers |

Sheet count must equal CSV export count (**19**).

---

## Builder obligations

1. When architecture or build decisions change, **update the appropriate registry tab** (then re-export CSVs under `build-dashboard/` if the workbook is the edit surface).
2. Do **not** let the workbook become stale documentation that drifts from reality or from code.
3. Status words mean what they say. Do not mark LIVE without commissioning evidence.
4. Prefer registry rows over tribal memory. Prefer Master Spec for intent; registries for approved structure and state.
5. Never “fix” a conflict by inventing a third design in code only.

---

## Paths

| Artifact | Path |
| --- | --- |
| Source workbook (binary, unmodified) | `docs/canon/source/Wolf_Command_Master_Build_Dashboard_v1.xlsx` |
| This README | `docs/canon/MASTER-BUILD-DASHBOARD-README.md` |
| CSV registries | `docs/canon/build-dashboard/*.csv` |
| Companion intent spec | `docs/canon/WOLF-COMMAND-MASTER-SPECIFICATION.md` |
| Spec source DOCX | `docs/canon/source/Wolf_Command_Master_Specification_v1.docx` |

Locked ★ 16 Sep 2026 — installed into Beta canon. Production remains sacred.
