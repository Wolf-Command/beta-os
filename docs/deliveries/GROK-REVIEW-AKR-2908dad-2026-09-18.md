# GROK REVIEW — Authorised Knowledge Resolver v1 `2908dad`

**Commit:** `2908dad` feat(CAP-INTEL-02/03): Authorised Knowledge Resolver v1 (AKR)
**Date:** 2026-09-18 ~06:45 WITA (factory watch ADVANCE → GROK_REVIEW → Peaches verify)
**Verdict:** **PASS**
**Run:** `BF-akr-v1-20260918`

## Diff vs plan / mission

| Requirement | Required | Present in 2908dad | Result |
| --- | --- | --- | --- |
| Resolver module | `scripts/core/authorised_knowledge.py` | 785-line deterministic `resolve()` pipeline | PASS |
| Status vocabulary exact | NOT CANONICAL / NOT FOUND / INACCESSIBLE / CONFLICTED / UNKNOWN | Module constants + tests | PASS |
| EMPTY ≠ UNKNOWN | Empty canon + found source → NOT CANONICAL w/ provenance | `test_empty_field_not_unknown` + Habitat fixtures | PASS |
| Habitat Manrope vs Inter | Scoped brand_identity vs ui_chrome (not CONFLICTED) | Fixtures + `test_manrope_vs_inter_scoped` | PASS |
| Same-lane conflict | CONFLICTED when peer authority disagrees | `test_conflicted_same_lane` | PASS |
| Caps | max 8 sources; max 256KB | Constants + cap tests | PASS |
| No LLM invent | Deterministic only | No http/openai/urllib; INFERENCE rejected | PASS |
| No memory_items promote | Non-goal | Honesty flags false; no promote code | PASS |
| Tests | PASS/FAIL runner | `test_authorised_knowledge.py` | PASS |
| Optional Owner API | Only if cheap | Skipped (module+tests enough for BUILT) | PASS (allowed skip) |

## Red team

| Attack | Result |
| --- | --- |
| Invent answer from INFERENCE source | PASS — rejected; NOT FOUND/UNKNOWN with attempt log |
| Flatten SOURCE FOUND = CANONICAL | PASS — status NOT CANONICAL; provenance `canonical: false` |
| Treat empty canon as UNKNOWN | PASS — continues search; returns NOT CANONICAL when found |
| Unbounded crawl / >8 sources | PASS — hard cap; skipped counted |
| Oversized source (>256KB) | PASS — skipped; attempt mentions max_bytes |
| Cross-brand bleed (Uma into Habitat) | PASS — RECONCILE brand mismatch skip |
| Network in unit fixtures | PASS — relative fixture paths only; no http |
| Habitat commissioning / Metricool / ESB / Production | PASS — commit touches docs + AKR module/tests/fixtures/claim only |

## Verification (Peaches re-run)

- `python3 scripts/tests/test_authorised_knowledge.py` → **PASS=51 FAIL=0**
- HEAD = `2908dadc8fdc96152adf127af79d8942a8ddac78`
- Dirty-tree WIP (Progress/Model C/phase26 etc.) untouched by this commit

## Maturity

- CAP-INTEL-02 / CAP-INTEL-03 → **BUILT** (module + fixture proof). **Not PROVEN** (no live Owner API / live authorised retrieval pack). **Not READY**.

## Out of scope leftovers

- Owner GET `/api/knowledge/resolve` (optional; deferred)
- Live NAS/Drive registry wiring
- memory_items promote (explicit non-goal)
- PROVEN red-team pack against live allowlisted sources
