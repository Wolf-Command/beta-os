# GROK PLAN — Uma Blu Daily Close + Exception Handover

**Run:** BF-uma-blu-daily-close-20260917  
**Approved scope:** Uma Blu only · Beta only · no ESB writes · no Production · Habitat untouched  
**Date:** 2026-09-17

## Verdict (Grok)

Strongest honest reconciliation with current ESB API access:

1. Snapshot Finished bills for branch `BLZ` on business date from warehouse/`esb.sqlite` (or live OMS read if wired; prefer warehouse with pull timestamp).
2. Sum `grandTotal` / `paymentTotal` / payment mix from `salesPayments` by `paymentMethodTypeName` (CASH / CARD / …).
3. **Cannot** compute perfect expected till cash from settlement report (Felix: unavailable). Therefore:
   - `esb_cash_declared_by_payments` = sum of CASH-type salesPayments (PROVENANCE: ESB payment lines) — labelled **ESB_CASH_FROM_PAYMENTS**, not settlement truth.
   - Human `declared_cash` = Core Evidence (DECLARED, not VERIFIED).
   - `variance_cash` = declared_cash − esb_cash_from_payments when both present.
4. Missing approved threshold → state **VARIANCE_REQUIRES_POLICY** (never ACCEPT). Zero live threshold rows.
5. Stale: if warehouse max pull / fingerprint changes after close snapshot → STALE / recalculate required.
6. Only extra integrity signal in-slice: **ESB data incomplete / empty day** blocks close (not cancel-rate / Alchemist / ClickUp — backlog).

## Domain object

Table `venue_daily_closes` (Beta catalog):

- close_id, entity_id=ENT-BZG, venue_brand_id=BZG-UMA, business_date (YYYY-MM-DD)
- state: OPEN | DATA_CAPTURED | EVIDENCE_SUBMITTED | RECONCILED | VARIANCE_REQUIRES_POLICY | EXCEPTION | RESOLVED | VERIFIED_CLOSED | CANCELLED
- esb_fingerprint_sha256, esb_pulled_at, esb_query_meta_json (branch=BLZ, date, bill_count, totals…)
- esb_totals_json (grand_total, payment_total, cash_from_payments, card_from_payments, other_from_payments, finished_count, cancelled_count) — server-computed only
- declared_cash_amount (nullable until evidence), declared_cash_evidence_id
- variance_cash_amount (nullable), variance_policy_id (nullable; live = none)
- work_item_id (nullable), resolved_at, verified_at, verified_by_person_id
- UNIQUE(entity_id, venue_brand_id, business_date) — idempotent open/replay

Client cannot submit expected totals, variance, or state.

## States (strict)

SUBMITTED ≠ RECONCILED ≠ VERIFIED  
EXCEPTION acknowledged ≠ RESOLVED ≠ VERIFIED_CLOSED  
DECLARED cash ≠ VERIFIED cash (no auto-verify cash)

Clean path without threshold: if variance==0 and fingerprint fresh and evidence present → may VERIFIED_CLOSED via system control (no Matt).  
Non-zero variance without policy → VARIANCE_REQUIRES_POLICY → Work Item EXCEPTION owned by Head of F&B / Devi assignment → resolve with evidence → verify by eligible verifier (not self-close laundering).

## Devi seed (authorised)

HR master + Notion Employees: Ni Putu Devi Parwati · personal_email **deviputu236@gmail.com** (AUTHORISED HR — not invented).

Create smallest:
- PERS-DEVI person
- AUTH-DEVI-EMAIL provider=email identifier=deviputu236@gmail.com
- POS for ROLE-BZG-HFB (or ROLE-BZG-OPS-LEAD if cleaner; prefer existing ROLE-BZG-HFB) scoped ENT-BZG + BZG-UMA
- Assignment ACTIVE
- Scope SCOPE-BZG-UMA (brand) + entity BZG
- RBAC: close_submit, close_resolve_exception, close_verify (SoD: closer ≠ sole verifier on own exception where practical)

Do **not** `if person_id == PERS-DEVI`.  
CF Access Include for her email is **Matt CF gate** — software binds identity; live CF seat may still be WAITING.

Closer role: ROLE-BZG-CLOSER (or permission on existing floor role) — **no named roster person** → commissioning WAITING FOR VERIFIED CLOSING OPERATOR.

## Modules

- `scripts/core/venue_close.py` — create/idempotent get, capture ESB snapshot, attach evidence, reconcile, exception WI, resolve, verify
- `scripts/core/esb_close_snapshot.py` — read-only fingerprint from esb.sqlite (path configurable; test isolation)
- API routes on `serve_beta.py` under `/api/venue-close/...`
- UI: `dashboards/uma-blu-close.html` mobile-first operator + tiny exception list
- Migration: seed Devi + scopes + close table; **live variance threshold rows = 0**; live monetary authority unchanged (0)
- Tests: `scripts/tests/test_uma_blu_daily_close.py` — all mandatory cases from Matt brief
- Canon: `docs/canon/UMA-BLU-DAILY-CLOSE.md`
- Do not touch Habitat content_planner / publish paths

## Honesty flags

```
settlement_api: UNAVAILABLE
esb_cash_basis: PAYMENT_LINES_NOT_SETTLEMENT
live_variance_threshold: 0
live_monetary_authority: 0
```

## Out of scope

POS, other venues, Alchemist, ClickUp, stock, recipes, payroll, inventing thresholds, Habitat, Production, ESB writes.
