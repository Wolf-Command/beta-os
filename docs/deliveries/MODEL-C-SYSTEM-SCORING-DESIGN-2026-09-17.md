> **PROMOTED → CANONICAL RULES 2026-09-17** — Design reviewed and locked as `docs/MODEL-C-SYSTEM-SCORING-RULES.md`. This design file is historical evidence; prefer canon path for authority. State names ABSENT/SPECIFIED/BUILT/PROVEN/READY are canonical (not S1–S4 for UI/audit).

# MODEL C — SYSTEM SCORING DESIGN

**Status:** DESIGN COMPLETE — awaiting Matt approve of scoring rules (not live)  
**Class:** Design artifact only. No catalog change. No dashboard. No 28% change. No app code. No DB. No Production.  
**Authority input:** Matt APPROVED — MODEL C SYSTEM SCORING DESIGN (2026-09-17)  
**Canon denominator:** `docs/MODEL-C-CAPABILITY-CATALOG.md` (77 · 14) — UNCHANGED  
**WHERE:** `docs/deliveries/MODEL-C-SYSTEM-SCORING-DESIGN-2026-09-17.md`

CLAIMED ≠ VERIFIED · CLAIMED ≠ APPROVED · TARGET ≠ ACTUAL

---

## 1. What SYSTEM measures

**SYSTEM definition (locked by this design):**  
How much of the approved Wolf capability architecture has been correctly implemented and technically proven.

SYSTEM stops at **technical readiness**. It does **not** score:

| Concern | Dimension instead |
| --- | --- |
| Humans using it in real work | OPERATING ADOPTION |
| Trustworthy outcomes / metrics | DATA / MEASUREMENT |
| Accidental Matt dependency | FOUNDER INDEPENDENCE |
| Trusted books / cash / margin control | FINANCIAL CONTROL |
| Buyer inheritability / VDR / transition | SALE READINESS |

Human commissioning, live use, measurement, and founder independence are **out of SYSTEM** so they cannot be counted twice.

---

## 2. Capability maturity states (SYSTEM ladder)

Keep five states. Collapsed from longer candidate lists (APPROVED/BUILDING/RED-TEAMED/DEPLOYED as separate peers were rejected as too many for humans and easy to game with paperwork).

| Code | State | Meaning | Credit toward that capability |
| --- | --- | ---: |
| S0 | **ABSENT** | Not in build scope yet / no approved requirements pack | 0.00 |
| S1 | **SPECIFIED** | Capability has approved requirement set bound to canon ID | 0.25 |
| S2 | **BUILT** | Implementation exists for the approved requirement set | 0.50 |
| S3 | **PROVEN** | Deterministic tests green + required adversarial review on material surface | 0.75 |
| S4 | **READY** | Deployed where applicable + technical dependencies met (technically ready) | 1.00 |

### Why these five

- **ABSENT vs SPECIFIED:** catalog listing alone ≠ SPECIFIED. Specifying = approved requirements pack for that CAP-ID.
- **Dropped APPROVED as separate:** approval of requirements is the gate into SPECIFIED evidence, not its own credit band.
- **Dropped BUILDING:** in-progress is not a maturity credit; it stays S1 until BUILT evidence lands.
- **Merged TESTED + RED-TEAMED → PROVEN:** both are verification; red-team is a *required evidence class* for material/NEW CAPABILITY surfaces, not a sixth state.
- **Merged DEPLOYED + TECHNICALLY READY → READY:** deployed-route proof (where surface has a route) plus dependency readiness are one terminal SYSTEM state.

### Per-state rules

| State | Required evidence | Allowed previous | Regression of *maturity*? | External ownership effect | Partial allowed? |
| --- | --- | --- | --- | --- | --- |
| S0 ABSENT | None / explicit not-started | — | N/A | Same for all ownership tags | N/A |
| S1 SPECIFIED | Approved requirements pack linked to CAP-ID (canon + versioned req list). Peaches prose alone ≠ enough. | S0 | No (history kept). Forward only unless req pack withdrawn (rare admin). | INTEGRATE/OBSERVE/DERIVE: specify Wolf-side contract, not vendor roadmap | Yes via requirement credit (§3) |
| S2 BUILT | Code/schema/config/artifacts under CAP-ID mapping; machine-locatable | S1 | No. Breakage → HEALTH flag, not demote to ABSENT | INTEGRATE: connector + mapping code exists; vendor product existing ≠ BUILT | Yes |
| S3 PROVEN | Deterministic tests green for approved reqs; Grok/actual-diff red-team when NEW/material; CLAIMED≠VERIFIED | S2 | No for maturity. Failed re-prove → HEALTH=FAILING or hold promotion | INTEGRATE: contract tests against fixtures/sandbox; vendor uptime ≠ PROVEN | Yes |
| S4 READY | Deployed-route / runtime proof on Beta (or declared non-UI surface proof); required technical dependencies READY | S3 | No for maturity. Outage → HEALTH | INTEGRATE: Wolf path READY even if vendor write-locked (write lock may cap OPERATING ADOPTION / DATA, not erase SYSTEM READY if read/orchestrate path proven). Vendor downtime → HEALTH on integration path, not rewrite history | Yes — READY only when *weighted* req credit ≥ threshold (default 1.00 of approved set) |

**Default promotion rule:** state = highest contiguous ladder achieved for the capability’s **requirement-credit** (≥ state threshold). No skipping S1→S3 without S2 evidence.

---

## 3. Partial capabilities (anti-inflation)

### Method: Locked Requirement Credit (LRC)

1. Each capability may have an **approved requirements set** `R = {r1…rn}`.
2. Each `ri` has a **locked weight** `w_i` with `Σ w_i = 1.0` at approval time.
3. Each `ri` has a binary or ladder credit `c_i ∈ {0, 0.25, 0.5, 0.75, 1.0}` using the same SYSTEM ladder applied to that requirement’s evidence.
4. Capability SYSTEM score contribution:
   - `cap_frac = Σ (w_i × c_i)`
   - Mapped to display state by thresholds:  
     `≥0.25→S1`, `≥0.50→S2`, `≥0.75→S3`, `≥1.00→S4` (with S4 also needing deploy/deps gates).

### Invariance tests (must PASS)

| Attack | Result |
| --- | --- |
| Split one requirement into ten with equal share of the *same* locked weight | PASS — total weight unchanged; maturity unchanged |
| Add ten new requirements without Matt/approved re-lock of weights | FAIL closed — rejected; weights only change on approved amend |
| Create “sub-capabilities” as new CAP-IDs without catalog amend | FAIL closed — denominator frozen at 77 |
| Checklist flood under Sale | PASS — Sale 60 stay CONTROLS; do not enter LRC as peer CAP rows |

**Bounded sub-capabilities:** allowed only as *named requirement groups* under one CAP-ID, never as new denominator rows.

---

## 4. Capability weights

| Option | Explain | Game | Maintain | Business | Stability |
| --- | --- | --- | --- | --- | --- |
| A Equal 77 | Best | Hard | Trivial | Ignores criticality | Best |
| B Domain→equal within | OK if domains honest | Domain gaming | Medium | Better narrative | Medium |
| C Explicit criticality | Relevant | Easy to politics | High | Highest if honest | Weak |
| D Hybrid | Flexible | Medium | High | Medium | Medium |

**Decision: EQUAL capability weights for SYSTEM.**

Rationale: Model C already spent constitutional effort on grain. Equal weights make SYSTEM = mean of 77 `cap_frac` values. Criticality belongs in **which capabilities exist** (catalog), not silent multipliers. Domain narrative rollups may average caps *inside a domain for display* without changing SYSTEM.

**Final numeric criticality weights: NOT assigned** (architecture does not make them objectively obvious without politics).

---

## 5. Domain weights

**SYSTEM scoring: DOMAIN WEIGHTS NOT REQUIRED.**

`SYSTEM% = (Σ cap_frac_i) / 77 × 100`

Domain weights are optional **presentation** only (e.g. “Core domain mean”). Changing domain weights must not change SYSTEM% unless Matt separately approves a different formula.

Governance if Matt later wants domain-weighted SYSTEM: single Matt approve, freeze file, change only with catalog-class amend; never tune to a target %.

---

## 6. External system scoring (OWN / INTEGRATE / OBSERVE / DERIVE)

| Tag | What “mature” means | Evidence focus | Vendor operational? |
| --- | --- | --- | --- |
| **OWN** | Wolf workflow/control correct end-to-end on Wolf | Spec→build→prove→deploy of Wolf surfaces | N/A |
| **INTEGRATE** | Wolf connector/contract/orchestration correct | Mapping schema, connector tests, auth to external, read/write policy honesty (write-lock explicit) | Vendor up ≠ INTEGRATE mature; vendor down ≠ erase historical READY (HEALTH) |
| **OBSERVE** | Reliable governed read path | Ingest freshness SLA, source attribution, no silent fabricate | Same |
| **DERIVE** | Governed calculation from authoritative inputs | Formula provenance, inputs bound to OWN/INTEGRATE/OBSERVE sources, conflict rules | Same |

Write-lock on Metricool (example): CAP-INTG-05 / CAP-GGV-02 can be SYSTEM READY for *read + gate* while OPERATING ADOPTION / publish outcomes stay capped until write path approved.

---

## 7. Shared capability vs adoption

**CAP-BZG-03 Venue Daily Close**

| Fact | SYSTEM | OPERATING ADOPTION |
| --- | --- | --- |
| Capability built/proven/ready once | High / READY | — |
| Uma Blu commissioned | unchanged | Uma = adopted |
| Rainforest / Merah not adopted | unchanged | those venues = not adopted |
| Add 5th venue | **SYSTEM% unchanged** | adoption denominator for that capability grows (venues in scope) |

**Proof:** SYSTEM averages 77 capabilities, not venues. Adoption score = f(adopted instances / in-scope instances) per capability, rolled into OPERATING ADOPTION dimension — never into SYSTEM.

SHARED / ADOPTION: **PASS**

---

## 8. Build maturity vs current health

| Concept | Stores | Changes when |
| --- | --- | --- |
| **BUILD MATURITY** (SYSTEM state / cap_frac) | Highest verified ladder + LRC | New verified evidence; approved amend |
| **CURRENT HEALTH** | HEALTHY / DEGRADED / FAILING (separate flag) | Prove scripts, runtime, connector, Pulse/Gauge |

Broken after commissioning → HEALTH=FAILING (or DEGRADED), maturity history remains READY. Dashboard must show both. Health is **not** a SYSTEM maturity state.

CURRENT HEALTH SEPARATE FROM MATURITY: **YES**

---

## 9. Evidence sources (CLAIMED ≠ VERIFIED)

| State | Acceptable evidence | Reject |
| --- | --- | --- |
| SPECIFIED | Versioned requirements pack + link to CAP-ID; Matt/approved canon cite | Chat claim only |
| BUILT | Repo paths / schema / config inventory mapped to CAP-ID | “We built it” without locator |
| PROVEN | CI/test logs; red-team note on actual diff for material/NEW | Untested happy path |
| READY | Deployed-route HTTP/runtime proof; dependency READY matrix | Local-only file without route when surface is UI |

Peaches prose may *point* to evidence; it is not evidence.

---

## 10. Model E — non-overlapping definitions

| Dimension | One sentence | Owns evidence like |
| --- | --- | --- |
| **SYSTEM** | Is the machinery correctly specified, built, proven, and technically ready? | LRC, tests, red-team, deploy proof |
| **OPERATING ADOPTION** | Are named humans actually using the capability in real work? | Staff commissioning, real actions, seats |
| **DATA / MEASUREMENT** | Can Wolf observe trustworthy outcomes and learn from them? | Metric freshness, SoT integrity, TARGET≠ACTUAL honesty |
| **FOUNDER INDEPENDENCE** | Can the operation run without accidental Matt dependency? | Delegation burn-down, succession, 7/30/90/365 tests |
| **FINANCIAL CONTROL** | Can management trust money, profitability, and financial controls? | Close quality, reconcile, leakage, AR/AP, cash |
| **SALE READINESS** | Can a buyer understand, inherit, and operate the business? | Evidence pack, VDR, buyer mode, transition |

**No double counting rule:** an event credits the *primary* dimension. Example: Habitat human publish credits ADOPTION (and maybe DATA if outcomes logged), not an extra SYSTEM bump if already READY.

MODEL E NON-OVERLAPPING: **PASS** (by definition + ownership of evidence)

---

## 11. Combined overall number?

**Recommendation: NO default combined OVERALL %.**

Show six dimension dials. Matt likes one headline — honesty wins: averaging SYSTEM software readiness with founder independence and sale readiness falsely implies substitutability.

**If Matt later demands one TRANSFORMATION number:**

- Principle only (no live calc): explicit Matt-approved dimension weights summing to 1.0; each dimension 0–100; TRANSFORMATION = Σ w_d × dim_d.
- Must label **TRANSFORMATION (weighted Model E)** — never “progress” alone.
- Gaming hardness: medium (weight politics); mitigate by freezing weights and publishing them.
- **Not approved now. Not calculated now.**

COMBINED OVERALL NUMBER RECOMMENDED: **NO**

---

## 12. Simulations (illustrative — not live scores)

### Abstract cases

| Case | SYSTEM | ADOPTION | DATA | FOUNDER | FIN | SALE | HEALTH |
| --- | --- | --- | --- | --- | --- | --- | --- |
| A Specified only | S1 | low | low | — | — | — | n/a |
| B Built+tests, not deployed | S3 | low | low | — | — | — | may be n/a |
| C Deployed, humans never used | S4 | low | low | — | — | — | HEALTHY possible |
| D Human commissioned, write-locked ext | S4 possible | partial | capped | — | — | — | OK |
| E Live daily, no outcome metrics | S4 | high | low | — | — | — | OK |
| F Working, Matt-dependent | S4 possible | high | ? | **low** | ? | low | OK |
| G Mature; 1 of 5 venues | S4 | 20% of that cap’s adoption | — | — | — | — | OK |
| H Breaks after commissioning | S4 **unchanged** | may fall | may fall | — | — | — | **FAILING** |

### Real examples (simulation only — canonical state not changed)

| Capability | Likely SYSTEM band (sim) | Notes |
| --- | --- | --- |
| **Habitat Publish Gate** (CAP-GGV-02) | S3–S4 | Built+tests+Beta UI; human commissioning → ADOPTION not SYSTEM; Metricool write off → DATA/publish outcomes capped |
| **Uma Blu Daily Close** (CAP-BZG-03) | S3–S4 | Capability READY once; Uma adoption separate; other venues not in SYSTEM |
| **RBAC** (CAP-CORE-04) | S3–S4 | Server-enforced; prove matrix = PROVEN/READY evidence |
| **Authority Limits** (CAP-CORE-05) | S2–S4 | Built; live limits at 0 is *policy config*, not immaturity of evaluator machinery — distinguish config from SYSTEM |
| **Authorised Knowledge Resolution** (CAP-INTEL-02/03) | S1–S3 | Rule canonised; full machinery prove may lag — SPECIFIED strong; READY needs runtime prove |
| **Sale Buyer Data Room** (CAP-SALE-02) | S0–S1 | Catalog READY as row; implementation immature — SYSTEM low; Sale 60 controls do not inflate |

---

## 13. Red team

| Attack | Defence | Result |
| --- | --- | --- |
| Row-count gaming | Denominator locked 77 | PASS |
| Requirement splitting | LRC locked weights | PASS |
| Capability splitting | Catalog amend only | PASS |
| Arbitrary weighting | Equal caps for SYSTEM | PASS |
| Tiny capability inflation | Constitutional grain + equal weight still needs catalog amend | PASS |
| Coding without adoption | SYSTEM vs ADOPTION split | PASS |
| Adoption without reliable system | ADOPTION without READY is hollow; report both | PASS |
| Tests without deployed route | Cannot reach S4 | PASS |
| Vendor mistaken for Wolf maturity | Ownership tags + INTEGRATE evidence | PASS |
| New venue lowers SYSTEM% | Adoption rule; SYSTEM unchanged | PASS |
| Stale capability appears healthy | HEALTH separate | PASS |
| Founder dependency hidden by software | FOUNDER dimension | PASS |
| Finance immaturity hidden by software | FINANCIAL CONTROL dimension | PASS |
| Sale checklist flooding | Controls ≠ caps | PASS |
| Future scope changes denominator | Only via catalog amend (correct); silent add = incorrect blocked | PASS |

GRANULARITY INVARIANCE: **PASS**  
GAMING RESISTANCE: **PASS**  
GROK RED TEAM: **PASS**

---

## 14. Explicit non-goals of this design

- No replacement of displayed 28%
- No Progress Dashboard modification
- No application code
- No operational DB / Production mutations
- No change to 77-cap catalog
- No live SYSTEM% calculation claimed as official
- No Model E dimension weights approved
- No TRANSFORMATION composite approved

## 15. Recommended next action

**MODEL C SCORING RULES LOCK** — Matt approve this design (states, LRC, equal weights, health split, no combined default). Then a later mission: evidence harness + migration plan that *labels* 28% legacy until cutover.

---

## Appendix — Formula (design only, not live)

```
cap_frac_i = Σ_j (w_ij × c_ij)          # LRC; Σ w = 1
SYSTEM%     = (Σ_i cap_frac_i) / 77 × 100
HEALTH_i    ∈ {HEALTHY, DEGRADED, FAILING}  # orthogonal
ADOPTION%   = separate dimension (not defined numerically here)
```

28% remains **LEGACY BUILD-TRACKER ESTIMATE — PENDING MODEL C SCORING MIGRATION**.
