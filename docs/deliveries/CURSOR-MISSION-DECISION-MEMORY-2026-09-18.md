# CURSOR MISSION — Decision Memory v1 (P4)

**Repo:** `/Users/wolfterminal/beta-os` (Beta only)
**CAP:** CAP-INTEL-04
**Follow:** `docs/deliveries/GROK-PLAN-DECISION-MEMORY-2026-09-18.md`
**Catalog intent:** Material decisions, options considered, approvals, outcomes preserved and recallable.

## Do
1. `scripts/core/decision_memory.py` — INSERT-only decision records + recall.
2. `scripts/tests/test_decision_memory.py` — PASS/FAIL runner, fixture DB only (temp file). No network.
3. Prove: no UPDATE/DELETE of history; correction is a new row; scope isolation; empty outcome stays UNKNOWN (never invented); recall max 50.

## Do NOT
- Build a dashboard UI
- Touch Habitat commissioning, Uma close, Metricool, ESB, Production
- Invent approvers, amounts, or outcomes
- Replace `scripts/core/audit.py`

## Verify
```bash
python3 scripts/tests/test_decision_memory.py
```
Print CURSOR_DONE, git log -1 --oneline, PASS/FAIL counts.
Commit referencing CAP-INTEL-04 Decision Memory v1.
