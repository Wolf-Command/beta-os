# CRM-IDENTITY-1 RESULT — Customer identity/memory vertical slice (no cross-client leak)

**As of:** 2026-09-30 ~01:01 WITA · **Branch:** `build/wolf-command-rebuild` (beta-os)  
**Ports:** Prod `:8787` pid **15975** READ-ONLY untouched · Beta test harness ephemeral  
**Flags:** `staff_ready=false` · `human_commissioned=false` · **No push** · **Did not start FIN-INTERCO-1 / HEADCHEF / Exit Report**

## Decision / canon

Serves **FINAL_WOLF_COMPLETION_MISSION Phase 2 pack CRM-IDENTITY-1** (armed 2026-09-30) — vertical slice toward **CAP-CRM-02 / IL-R9** on the **existing** `scripts/core/crm_identity_memory.py` path.  
**Not PROVEN/READY.** Yanolja graph merge stays **BLOCKED_EXTERNAL**. No second CRM identity system.

## What landed

### 1) Canonical stub + confidence + client isolation
- Extended `crm_identity_memory.py` with `client_scope` (GGV: `habitat` | `ivy`), confidence fields (`match_confidence` / `confidence_band` = uncertain), and `human_review_when_uncertain`
- Cross-client **read** and **link** refused (`cross_client_refused`) — client boundaries override identity matching
- Links remain `REVIEW_REQUIRED` candidates; merge path still does not collapse rows
- Yanolja kind / evidence → `yanolja_blocked_external` (no invented PMS identity)

### 2) Thin Beta desk + API
- Page `/crm/identity-1` (`dashboards/crm-identity-1.html`; aliases `/crm-identity-1`)
- API `GET /api/crm/identity-1` (auth) → slice payload
- Unsigned → **403** (fail-closed)
- Honesty tiles: stub · confidence · human review · client isolation · Yanolja BLOCKED_EXTERNAL · CAP-CRM-02 maturity
- Desk links into existing CRM identity desk + operator depth + integrations honesty board

### 3) Honesty pins
| Pin | Value |
| --- | --- |
| CAP-CRM-02 | **SPECIFIED** · ceiling BUILT · `cap_crm_02_proven=false` |
| Match confidence | **uncertain** (never invented verified) |
| Human review when uncertain | **true** · no auto-merge |
| Cross-client leak | **false** · isolation ENFORCED |
| Yanolja graph merge | **BLOCKED_EXTERNAL** |
| Fake pipeline / auto-merge | **false** |
| `staff_ready` / `human_commissioned` | **false** |
| Second CRM system | **false** |

## Tests

| Suite | Result |
| --- | --- |
| `scripts/tests/test_crm_identity1_20260930.py` | **PASS=140 FAIL=0** |
| `test_crm_identity_memory.py` (re-run) | **PASS=103 FAIL=0** |
| `test_crm_identity_operator_depth.py` (re-run) | Honesty/RBAC checks PASS through Amanda; later **pre-existing** Haikal seat fixture raises `existing CRM seat permission is not present` — not introduced by this pack |

Shots: `docs/wolf/ops/shots/crmidentity1-desk-desktop.png`, `crmidentity1-desk-phone.png`, `crmidentity1-client-isolation.png`, `crmidentity1-yanolja-blocked.png`, `crmidentity1-unsigned-deny.png`.

## Files

- Core: `scripts/core/crm_identity_memory.py` (extended — not a second system)
- Serve: `scripts/serve_beta.py` (`_crm_identity1_dispatch`)
- UI: `dashboards/crm-identity-1.html`
- Shell crumbs/canonical: `scripts/core/wolf_shell.py`
- Tests: `scripts/tests/test_crm_identity1_20260930.py`
- Stamp: `state/final-completion/packs/CRM-IDENTITY-1-ARM.json`

## Out of scope (not started from this EXIT)

- **FIN-INTERCO-1** (next — Peaches/parent arms after verify; Cursor must not auto-chain)
- Auto-merge, Yanolja live graph, fake leads pipeline, seating people
- HEADCHEF / Exit Report / prod mutate / push / flipping commissioning flags
- Fixing unrelated pre-existing Haikal CRM seat fixture in operator-depth suite

## EXIT

**EXIT:0**

`staff_ready=false` · `human_commissioned=false` · prod pid 15975 untouched · no push · did not auto-chain next pack.
