# CAP-INTEL-02 / CAP-INTEL-03 — EVIDENCE BIND (AKR v1)

> **OWNER AUDIT 2026-09-18 — ACCEPTED BUILT, not PROVEN.**  
> CAP-INTEL-02 and CAP-INTEL-03 remain **BUILT**. No maturity credit beyond BUILT from this bind.

**Date:** 2026-09-18
**CAPs:** CAP-INTEL-02 (Authorised Retrieval & Institutional Memory) · CAP-INTEL-03 (Provenance / Confidence / Conflict Resolution)
**Prior:** SPECIFIED → **Accepted:** **BUILT** (not PROVEN)
**Commit:** `2908dad`
**Class:** BUILD SMALLEST DETERMINISTIC SOFTWARE

## Implementation

- `scripts/core/authorised_knowledge.py` — SCOPE→CANONICAL→DISCOVER→RETRIEVE→RECONCILE→AUTHORITY→FRESHNESS→CONFLICTS→answer/status
- Exact status vocab: NOT CANONICAL | NOT FOUND | INACCESSIBLE | CONFLICTED | UNKNOWN
- Caps: max 8 sources / resolve; max 256 KiB / source; no crawl; no LLM invent; no memory_items auto-promote
- Fixtures: `scripts/tests/fixtures/authorised_knowledge/` (Habitat Manrope vs Inter scoped lanes)
- Canon: `docs/RULE-Authorised-Knowledge-Resolution-2026-09-17.md`
- Plan/mission: `docs/deliveries/GROK-PLAN-AUTHORISED-KNOWLEDGE-RESOLVER-2026-09-18.md` · `docs/deliveries/CURSOR-MISSION-AUTHORISED-KNOWLEDGE-RESOLVER-2026-09-18.md`
- Grok review: `docs/deliveries/GROK-REVIEW-AKR-2908dad-2026-09-18.md` **PASS**

## Deterministic verification

```bash
python3 scripts/tests/test_authorised_knowledge.py
# PASS=51 FAIL=0
```

## Why not PROVEN / READY

- No live Owner API route / live allowlisted retrieval against real NAS/Drive/vault
- No sustained operational prove in a human workflow
- Dashboard 28% / official SYSTEM% / Adoption% untouched (non-goals of this slice)

## Honesty

- Production: untouched
- Habitat commissioning: undisturbed
- External writes: none
