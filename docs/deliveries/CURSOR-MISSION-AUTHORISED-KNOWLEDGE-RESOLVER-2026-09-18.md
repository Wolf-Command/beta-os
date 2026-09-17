# CURSOR MISSION — Authorised Knowledge Resolver v1 (P3)

**Repo:** `/Users/wolfterminal/beta-os` (Beta only)
**CAP:** CAP-INTEL-02 + CAP-INTEL-03
**Follow:** `docs/deliveries/GROK-PLAN-AUTHORISED-KNOWLEDGE-RESOLVER-2026-09-18.md`
**Canon:** `docs/RULE-Authorised-Knowledge-Resolution-2026-09-17.md`
**Proof case:** `docs/deliveries/HABITAT-FULL-AUTHORISED-KNOWLEDGE-SWEEP-2026-09-17.md`

## Do
1. Implement `scripts/core/authorised_knowledge.py` — deterministic resolver (no LLM invent).
2. Implement `scripts/tests/test_authorised_knowledge.py` — PASS/FAIL runner like other Core tests.
3. Fixtures under `scripts/tests/fixtures/authorised_knowledge/` for Habitat-like brand guide vs UI font conflict.
4. Encode caps: max 8 sources per resolve; max 256KB per source; fixture-only in unit tests (no network).
5. Status vocabulary exact: NOT CANONICAL | NOT FOUND | INACCESSIBLE | CONFLICTED | UNKNOWN (+ resolved answer when safe).
6. Prove EMPTY FIELD ≠ UNKNOWN when authorised source finds material.
7. Optional: Owner-only GET `/api/knowledge/resolve` in serve_beta if small; else skip UI.

## Do NOT
- Auto-write memory_items / canon stores
- Touch Habitat content_planner / commissioning
- External network in unit tests
- Production / Metricool / ESB writes
- New agent hire

## Verify
```bash
python3 scripts/tests/test_authorised_knowledge.py
```
Print CURSOR_DONE, git log -1 --oneline, test PASS/FAIL counts.
Commit with message referencing CAP-INTEL-02/03 AKR v1.
