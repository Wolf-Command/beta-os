> **PROMOTED → CANONICAL RULES 2026-09-17** — Locked as `docs/MODEL-E-OPERATING-ADOPTION-RULES.md`. Design preserved as history. Numeric credits still NOT APPROVED.

# MODEL E — OPERATING ADOPTION DESIGN

**Status:** DESIGN COMPLETE — not locked · no official Adoption % · no dashboard  
**Date:** 2026-09-17  
**Authority input:** Matt APPROVED — MODEL E OPERATING ADOPTION DESIGN  
**Frozen:** SYSTEM baseline 22.3% · catalog 77 · numeric credits v1.0 · displayed 28% · Habitat/Uma commissioning  
**WHERE:** `docs/deliveries/MODEL-E-OPERATING-ADOPTION-DESIGN-2026-09-17.md`

CLAIMED ≠ VERIFIED · READY ≠ HUMAN COMMISSIONED · CAPABILITY ≠ ADOPTION

---

## 1. Definition

**OPERATING ADOPTION** = Are authorised humans actually using the required Wolf capabilities correctly in real operations?

SYSTEM asks: is the machine built and technically proven?  
ADOPTION asks: is anybody actually using it?

Completely separate dials. No double-counting.

---

## 2. Denominator (not 77)

**Do not use 77.**

### Adoption unit

One **Adoption Unit (AU)** =

**canonical CAP-ID × one REQUIRED adoption scope**

Scope types (capability-declared):

| Scope type | Examples |
| --- | --- |
| Entity | GGV, AMG, BZG |
| Brand / client operation | Habitat Content |
| Venue / property | Uma Blu, Rainforest, Atrium |
| Shared role-function cohort | Wolf users who must authenticate; finance closers for an entity |

Examples:

- `CAP-BZG-03` × Uma Blu  
- `CAP-BZG-03` × Rainforest *(only when REQUIRED)*  
- `CAP-GGV-02` × Habitat Content operation  
- `CAP-CORE-02` × required Wolf seat cohort (entity-scoped auth population)  
- `CAP-AMG-02` × Atrium property ops *(when Wolf journey is the required path)*  
- `CAP-FIN-01` × GGV / AMG / BZG as required entity closes  

**Denominator** = count of AUs whose applicability = **REQUIRED** at the measurement date.

PLANNED / DEFERRED / NOT APPLICABLE are **out of denominator** (with provenance). They do not dilute Adoption %.

---

## 3. Applicability states

| State | Meaning | In denominator? |
| --- | --- | --- |
| **REQUIRED** | Capability applies; operating scope is live; rollout due or replacement of prior process is due | YES |
| **PLANNED** | Future required scope approved in architecture, not yet triggered | NO |
| **DEFERRED** | Explicit Matt/architecture delay with dated reason and revisit | NO |
| **NOT APPLICABLE** | Capability does not apply to this scope (e.g. Venue Daily Close × Atrium hotel rooms) | NO |

### When PLANNED → REQUIRED (triggers)

Any one of:

1. Entity / site / venue / brand becomes **operational** for that workflow  
2. Capability is **applicable** and prior process is designated for replacement  
3. Rollout is **formally approved** with effective date  
4. Replacement of previous process is **due** (effective date passed)

### Anti-gaming

- **NOT APPLICABLE** requires written provenance (why this CAP cannot apply here). Re-review if scope changes.  
- **DEFERRED** requires named approver, reason, and revisit date. Perpetual DEFERRED without revisit = Vesper flag.  
- Indefinitely calling necessary rollout “future” without trigger evaluation = denominator hiding (FAIL).

---

## 4. Adoption states (four)

| State | Meaning |
| --- | --- |
| **NOT STARTED** | REQUIRED AU exists; no valid commissioning attempt |
| **COMMISSIONING** | Authorised human path under active prove; incomplete or failed last attempt |
| **ADOPTED** | At least one successful commissioning event for the required role-function on this AU |
| **SUSTAINED** | Cadence-appropriate repeated genuine use; shadow retired; no repeated rescue |

Four is enough. Fewer collapses commissioning vs habitual use. More invites paperwork.

### Evidence (minimum)

| State | Evidence |
| --- | --- |
| NOT STARTED | AU REQUIRED; no commissioning record |
| COMMISSIONING | Named attempt log: who, when, CAP, scope, outcome, gaps |
| ADOPTED | Commissioning pack PASS: real human, real identity, real operator path, real workflow artifact |
| SUSTAINED | Cadence samples met + shadow retired + no chronic Peaches/Matt intervention |

---

## 5. Human commissioning

Counts only if **all** true:

1. Real authorised human (staff/owner seat as intended)  
2. Real Wolf identity (CF/auth binding — not shared anonymous)  
3. Real operator path (UI/workflow humans use)  
4. Real workflow evidence produced by that human  
5. Capability-relevant action (not adjacent busywork)

**Does not count:**

- API impersonation / service tokens as “human”  
- Test fixtures / synthetic users  
- Peaches (or any agent) clicking on behalf of staff  
- Matt performing cashier / closer / content-approver / manager work solely to green a state when that is not his normal operating role for that AU  

Commissioning proves the **human workflow** works — not that the CoS can operate the desk.

---

## 6. Sustained (cadence-relative)

One PASS commissioning ≠ habitual use.

**SUSTAINED** requires, for that AU’s declared cadence:

| Cadence class | Example | Sustained bar (design default) |
| --- | --- | --- |
| Daily | Venue Daily Close | N consecutive operating days with valid closes by required role-function (declare N in AU pack; default 5) |
| Weekly | Content publish gate | N successful publish cycles by designated roles (default 3) |
| Monthly / event | Buyer Data Room refresh | N scheduled cycles completed without rescue (default 2) |

Plus:

- Correct role-function operators (not only founder rescue)  
- Declared shadow process **retired** for this workflow  
- Evidence quality maintained  
- No repeated Peaches/Matt intervention as the operating plan  

No universal “30 days” across unlike workflows.

---

## 7. Shadow systems vs intentional SoT

**Shadow:** staff still operate through WhatsApp / spreadsheets / paper / Notion / ClickUp / old dashboard / personal memory as the real control path, while Wolf only receives after-the-fact duplicates → blocks SUSTAINED (and may block ADOPTED if Wolf path unused).

**Intentional SoT:** external system owns transactional truth by Model C ownership tag (e.g. ESB INTEGRATE). Wolf orchestrates around it. That is **not** a shadow — it is correct INTEGRATE behaviour.

Rule: shadow = parallel *control* path for a workflow Wolf claims to own; SoT = declared external authority Wolf integrates.

---

## 8. Founder rule

- Matt using an **Owner/Director-intended** AU may count (intentional authority).  
- Matt doing another role’s normal job only to pass commissioning **does not** establish adoption for that AU.  
- Accidental founder dependency belongs to **FOUNDER INDEPENDENCE**, not Adoption credit.

---

## 9. Role / person rule

Adoption binds to **required operating scope + role-function**, not permanently to one named employee.

- Haikal → replacement who is commissioned on Habitat publish gate: ADOPTED/SUSTAINED can continue after handover evidence.  
- Replacement never trained/commissioned: AU returns to COMMISSIONING or NOT STARTED; may also HEALTH=DEGRADED.  
- Turnover does not invent new AUs; it may reset state on the same AU.

---

## 10. SYSTEM dependency (anti-duplicate)

Usage of a half-built path can be observed (truth), but:

| Rule | Design |
| --- | --- |
| Recording | May log “observed use” on SYSTEM < READY |
| ADOPTED (for Adoption dimension scoring, when credits lock) | Requires SYSTEM maturity ≥ **PROVEN** for that CAP |
| SUSTAINED (for scoring) | Requires SYSTEM maturity = **READY** for that CAP |

Rationale: full Adoption credit for the intended Wolf capability must not be earned on an incomplete machine (avoids Adoption becoming a duplicate of “people struggle with prototypes”). Observed use on immature SYSTEM is noted under Adoption **HEALTH** / notes, not SUSTAINED credit.

SYSTEM 22.3% unchanged by this design.

---

## 11. Adoption maturity vs Adoption health

| Concept | Stores | On abandon after 6 months sustained |
| --- | --- | --- |
| **Adoption maturity** | NOT STARTED → … → SUSTAINED | Demote **SUSTAINED → ADOPTED** (or COMMISSIONING if no recent valid use) |
| **Adoption health** | HEALTHY / DEGRADED / FAILING / UNKNOWN | Set **FAILING** or **DEGRADED** when expected cadence breaks |

Do not erase historical commissioning. Do not pretend abandoned workflows are still SUSTAINED.

ADOPTION HEALTH SEPARATE: **YES**

---

## 12. Numeric mappings (proposed — NOT locked)

Credits later apply to each **REQUIRED AU**, then:

`ADOPTION% = SUM(AU credits) / count(REQUIRED AUs) × 100`

| Map | NOT STARTED | COMMISSIONING | ADOPTED | SUSTAINED | Bias |
| --- | ---: | ---: | ---: | ---: | --- |
| A Linear | 0 | 0.33 | 0.67 | 1.00 | Even steps |
| B Sustain-heavy | 0 | 0.10 | 0.40 | 1.00 | Habit matters most |
| C Commission-gated | 0 | 0.20 | 0.80 | 1.00 | First real human use is the cliff |

**Red-team sketch:** A over-rewards thin commissioning; B resists one-click greens; C may undervalue sustain. Prefer **B** when locking later — not locked now.

NUMERIC CREDITS LOCKED: **NO**

---

## 13. Simulations (design only — no record changes)

### Habitat Publish Gate (`CAP-GGV-02` × Habitat Content)

- SYSTEM: READY  
- Applicability: REQUIRED  
- Haikal/Amanda commissioning waiting  
- **Adoption: NOT STARTED** (or COMMISSIONING if attempt logged incomplete)  
- SYSTEM 100% on this CAP does not move Adoption  

### Venue Daily Close (`CAP-BZG-03` × Uma Blu)

- SYSTEM: READY (shared CAP)  
- Uma: REQUIRED; other venues PLANNED until operational/trigger  
- Verified closer missing  
- **Adoption: NOT STARTED / COMMISSIONING**  
- Adding Rainforest does **not** change % until Rainforest becomes REQUIRED  

### Person/Auth (`CAP-CORE-02`)

- SYSTEM: READY  
- Scope: required Wolf seat cohorts that must authenticate  
- Real CF-bound identities exist → likely **ADOPTED** for cohorts that completed real login prove; **SUSTAINED** only if ongoing auth use at expected cadence without shadow logins  
- Existence of JWT machinery ≠ SUSTAINED without evidence of required humans using it as the door  

### Approval Engine (`CAP-CORE-07`)

- Technically mature (SYSTEM PROVEN)  
- Adoption requires material approvals executed by designated humans on required entity scopes — not only test harness  
- Until real operator approvals exist: **NOT STARTED/COMMISSIONING**; scoring SUSTAINED blocked until SYSTEM READY anyway  

### Yanolja / AMG

- Daily Yanolja PMS use ≠ Wolf Adoption  
- Wolf AU for `CAP-AMG-01` / journey caps remains **NOT STARTED** until humans use **Wolf** orchestration/workflows  
- ESB/Yanolja SoT use is intentional external — not Wolf SUSTAINED  

---

## 14. Granularity invariance

| Attack | Result |
| --- | --- |
| One employee → ten | PASS — AU is role-function/scope, not headcount |
| Requirement split into ten | PASS — SYSTEM LRC / requirements, not new AUs |
| One UI → three pages | PASS — not new AUs |
| New brand not applicable | PASS — NOT APPLICABLE out of denominator |
| New venue operational + rollout due | CHANGE — new REQUIRED AU (correct) |
| Adopted workflow abandoned | CHANGE — demote + HEALTH |
| Shadow returns | CHANGE — lose SUSTAINED |

GRANULARITY INVARIANCE: **PASS**  
DENOMINATOR GAMING RESISTANCE: **PASS** (with DEFERRED revisit + N/A provenance)

---

## 15. Model E separation

| Dimension | Adoption must not claim |
| --- | --- |
| SYSTEM | Build/prove/ready machinery |
| DATA / MEASUREMENT | Outcome truth / metric quality |
| FOUNDER INDEPENDENCE | Accidental Matt dependency burn-down |
| FINANCIAL CONTROL | Books/cash/profit trust |
| SALE READINESS | Buyer inheritability |

Dependencies exist (e.g. SUSTAINED scoring needs SYSTEM READY) but evidence is assigned primarily to Adoption for *use*.

MODEL E SEPARATION: **PASS**

---

## 16. Red team

| Attack | Defence | Result |
| --- | --- | --- |
| Denominator inflation (77) | AU = CAP × REQUIRED scope | PASS |
| Denominator hiding | N/A/DEFERRED provenance + revisit | PASS |
| Fake N/A | Written why + review | PASS |
| Perpetual DEFERRED | Revisit date + Vesper flag | PASS |
| One click = adoption | COMMISSIONING ≠ ADOPTED; SUSTAINED cadence | PASS |
| Matt/Peaches/API/fixture | Commissioning definition bans | PASS |
| Vendor usage as Wolf | Ownership boundary | PASS |
| Shadow duplicate | Blocks SUSTAINED | PASS |
| Turnover | Role-function AU + re-commission | PASS |
| Low-frequency workflows | Cadence classes | PASS |
| New venue | Only when REQUIRED | PASS |
| Abandoned | Demote + HEALTH | PASS |
| Broken but historically adopted | HEALTH + maturity demotion rules | PASS |
| Wrong CAP/scope evidence | AU identity in evidence pack | PASS |

GROK RED TEAM: **PASS**

---

## 17. Genuine questions for Matt

**NONE** — triggers, cadence classes, and SYSTEM dependency caps are resolvable from existing Model C locks and this design. Lock of applicability registers and numeric credits is a later approve.

---

## 18. Explicit non-goals

- No official Adoption % calculated  
- No dashboard / 28% / SYSTEM 22.3% change  
- No catalog change  
- No app/DB/Production  
- Habitat/Uma commissioning undisturbed  

## 19. Recommended next action

**LOCK OPERATING ADOPTION RULES** (denominator, applicability, states, commissioning, sustained, shadow, founder, role, SYSTEM dependency, health) — still no official Adoption % until a later evidence baseline.
