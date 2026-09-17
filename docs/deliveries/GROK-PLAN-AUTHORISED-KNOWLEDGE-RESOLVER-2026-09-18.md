# GROK PLAN — Authorised Knowledge Resolution v1 (P3 overnight continue)

**Date:** 2026-09-18
**Authority:** Matt CONTINUE overnight autonomous build + P3 AKR (opens backlog slice)
**CAP:** CAP-INTEL-02 + CAP-INTEL-03 (shared primitive)
**Beta only. No Production. No Habitat commissioning disturb. No memory_items auto-promote.**

## Scope (smallest deterministic software)

Implement `scripts/core/authorised_knowledge.py` + tests:

1. `resolve(scope, question_key, sources_registry)` pipeline:
   SCOPE → CANONICAL check → DISCOVER allowlisted sources → RETRIEVE (bounded) → RECONCILE identity → AUTHORITY classify → FRESHNESS → CONFLICTS → answer with provenance/confidence OR status enum

2. Status vocabulary (exact): NOT CANONICAL | NOT FOUND | INACCESSIBLE | CONFLICTED | UNKNOWN | plus resolved answer object when safe

3. Rules encoded:
   - EMPTY FIELD ≠ UNKNOWN
   - UNKNOWN requires search evidence (attempt log)
   - SOURCE FOUND ≠ AUTHORITATIVE ≠ CANONICAL
   - AI inference ≠ source evidence (no LLM invent in this slice)
   - Deterministic allowlist + timeout/cost caps (no crawl)

4. Habitat proof fixture (offline): Manrope vs Inter conflict → CONFLICTED or scoped resolution (brand kit vs UI) without human; empty canon field + found brand guide → NOT CANONICAL answer with provenance (not UNKNOWN)

5. Optional thin Beta API read-only Owner: `GET /api/knowledge/resolve?...` — only if cheap; else module+tests enough for BUILT

## Non-goals

- Vector DB / new agent / auto-promote to memory_items
- Live NAS/Drive crawl unbounded
- Asking staff
- Metricool/ESB/Yanolja writes
- Changing SYSTEM credits / dashboard 28% / Adoption %

## Success

- Unit tests cover EMPTY≠UNKNOWN, NOT FOUND, INACCESSIBLE, CONFLICTED, Habitat Manrope/Inter class
- Grok actual-diff PASS
- Peaches verify
- Evidence bind CAP-INTEL-02/03 only if BUILT bar met — PROVEN only with red-team pack
