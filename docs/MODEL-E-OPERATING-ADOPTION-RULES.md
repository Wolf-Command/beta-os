# MODEL E — OPERATING ADOPTION RULES (CANONICAL)

**Status:** CANONICAL — rules locked (not an Adoption % · not dashboard)  
**Approved:** Matt APPROVED — LOCK MODEL E OPERATING ADOPTION RULES (2026-09-17, chat)  
**Design history:** `docs/deliveries/MODEL-E-OPERATING-ADOPTION-DESIGN-2026-09-17.md`  
**Frozen:** SYSTEM baseline 22.3% · catalog 77 · SYSTEM credits v1.0 · displayed 28% · Habitat/Uma commissioning  
**WHERE:** `docs/MODEL-E-OPERATING-ADOPTION-RULES.md`

CLAIMED ≠ VERIFIED · READY ≠ HUMAN COMMISSIONED · CAPABILITY ≠ ADOPTION · EXTERNAL SoT ≠ SHADOW

---

## 1. Definition

**OPERATING ADOPTION** = Are authorised humans actually using the required Wolf capabilities correctly in real operations?

SYSTEM measures machinery.  
OPERATING ADOPTION measures real operational use.

Completely separate. SYSTEM credit does not automatically earn Adoption credit.

---

## 2. Adoption unit

**Adoption Unit (AU)** = **CAP-ID × REQUIRED ADOPTION SCOPE**

Scope may be:

- entity  
- brand  
- venue  
- property  
- role-function cohort  

Use the narrowest meaningful operational scope **without** employee-count inflation.

Individual employees are normally **evidence** of adoption, not denominator units.

---

## 3. Denominator

Adoption denominator = **count of REQUIRED Adoption Units only**.

Not:

- 77 capabilities  
- employee count  
- UI pages  
- requirements count  
- workflow step count  

---

## 4. Applicability

| State | In denominator? |
| --- | --- |
| **REQUIRED** | YES |
| **PLANNED** | NO |
| **DEFERRED** | NO |
| **NOT APPLICABLE** | NO |

Every applicability state requires **provenance**.

- **PLANNED** / **DEFERRED**: reason + review trigger/date/event where appropriate.  
- **NOT APPLICABLE**: evidence of genuine non-applicability.  
- A required rollout may **not** remain PLANNED/DEFERRED merely to protect the percentage.  
- When an approved operational scope becomes genuinely due for rollout, it becomes **REQUIRED**.

Adding a possible future venue does **not** automatically dilute Adoption.  
Bringing that venue into an approved required rollout appropriately **does**.

---

## 5. Adoption states

| State | Meaning |
| --- | --- |
| **NOT STARTED** | Required AU exists but no valid real-world commissioning has begun |
| **COMMISSIONING** | Genuine authorised humans are proving the real operator workflow |
| **ADOPTED** | Required role-function has successfully used the capability in genuine operations with required evidence |
| **SUSTAINED** | Cadence-appropriate repeated genuine use; required role-function can operate it; chronic rescue absent; inappropriate shadow control paths retired |

### SYSTEM dependency gates (not duplicate scoring)

| Adoption state | Requires SYSTEM maturity |
| --- | --- |
| ADOPTED | SYSTEM ≥ **PROVEN** for that CAP |
| SUSTAINED | SYSTEM = **READY** for that CAP |

Real use may be **observed** while SYSTEM is immature; ADOPTED/SUSTAINED scoring gates still apply when credits are later locked.

---

## 6. Human commissioning

Valid commissioning requires **all** of:

1. REAL HUMAN  
2. REAL IDENTITY  
3. REAL AUTHORISATION  
4. REAL OPERATOR PATH  
5. REAL WORKFLOW  
6. REAL EVIDENCE  

**Does not count:**

- Test fixtures  
- API impersonation  
- Peaches (or any agent) operating it for staff  
- Matt performing another person's normal operational role merely to obtain a green state  

Matt counts where Matt is genuinely the intended operator/authority.

---

## 7. Sustained use

Do **not** use one arbitrary duration globally.

Evidence must match workflow cadence:

- Daily workflow → repeated expected daily use  
- Weekly workflow → repeated expected weekly use  
- Monthly / quarterly / exception → appropriate evidence window/events  

Sustained means the real operating process has settled into the intended system.

---

## 8. Shadow systems

An inappropriate parallel **control** path blocks **SUSTAINED**.

Examples (when used as unauthorised replacement/parallel control): WhatsApp, spreadsheets, paper, old dashboards, personal memory, Notion/ClickUp.

Do **not** classify an intentionally approved tool or external Source of Truth as a shadow system.

ESB / Yanolja / etc. may remain legitimate external systems per Model C ownership boundaries.

**External vendor use ≠ Wolf adoption.** AMG staff using Yanolja every day does not establish adoption of a Wolf/Yanolja capability. Adoption requires actual use of the Wolf capability at the canonical integration/orchestration boundary.

---

## 9. Founder rule

Preserve:

**INTENTIONAL FOUNDER AUTHORITY** versus **ACCIDENTAL FOUNDER DEPENDENCY**

- Matt's genuine Owner/Director actions may establish adoption for Matt-intended functions.  
- Matt rescuing somebody else's routine workflow does **not** establish normal adoption.  

Founder Independence remains a separate Model E dimension.

---

## 10. Person / role / handover (turnover)

Adoption attaches primarily to **scope + role/function**, not permanently to a named employee.

### Representation (locked)

| Layer | Behaviour on staff change |
| --- | --- |
| **AU identity** | Unchanged — person change does **not** create a new AU |
| **Historical adoption maturity** | Preserved (history cannot claim “never adopted”) |
| **Replacement operator** | Requires appropriate commissioning/handover |
| **Current adoption state** | May move to COMMISSIONING (or reflect incomplete handover) until replacement is commissioned |
| **Current adoption health** | May be DEGRADED/FAILING/UNKNOWN until replacement is ready — without erasing historical maturity record |

Distinguish:

- **historical adoption maturity** (append-only evidence trail on the AU)  
- **current adoption health / readiness of the replacement operator**

History must not lie either direction: do not erase past adoption; do not pretend the new person is already commissioned.

**TURNOVER PRESERVES HISTORY: YES**  
**REPLACEMENT RE-COMMISSION REQUIRED: YES**

---

## 11. Current adoption health

Keep **ADOPTION MATURITY** separate from **CURRENT ADOPTION HEALTH**.

Minimum vocabulary (aligned with Wolf health architecture):

**HEALTHY · DEGRADED · FAILING · UNKNOWN**

A workflow successfully adopted historically and later abandoned must **not** have its history erased. Current health must reveal it is no longer operating correctly.

No numeric health scoring in this lock.

---

## 12. Granularity

Denominator remains stable when:

- employee count changes  
- requirements split  
- UI pages change  
- workflow steps change  

Denominator changes when a genuine required adoption scope becomes operational/due.

---

## 13. Numeric credits

**NOT APPROVED.**

Preserve candidates for later calibration:

| Map | NOT STARTED / COMMISSIONING / ADOPTED / SUSTAINED |
| --- | --- |
| A Linear | 0 / 0.33 / 0.67 / 1 |
| B Sustain-heavy | 0 / 0.10 / 0.40 / 1 |
| C Commission-gated | 0 / 0.20 / 0.80 / 1 |

Do not select one in this lock.

---

## 14. Governance

Future rule changes require explicit Matt approval.  
Never tune applicability or states to improve a displayed percentage.  
Version history must remain traceable.

## Version history

| Version | Date | Change |
| --- | --- | --- |
| MODEL-E-ADOPTION-RULES-v1.0-2026-09-17 | 2026-09-17 | Initial lock from design artifact |
