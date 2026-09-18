# Model C ledger reconcile — CAP-INTEL-04 PROVEN

**Date:** 2026-09-18
**Actor:** Matthew Goss, owner audit. Peaches wrote the ledger only.
**Dashboard:** not changed.
**Scoring rules:** not changed.

## Check before write

File: `state/model-c-baseline-assessments.json` (77 rows).
Prior sum: **18.90 / 77 = 24.5455%** (audited 24.5%).
CAP-INTEL-04 was BUILT (0.25). CAP-INTEL-02 and CAP-INTEL-03 already PROVEN.

Delta: 0.25 → 0.80 = +0.55.
Expected: **19.45 / 77 = 25.2597%**. Audited **25.3%**.
The file agreed. Write proceeded.

## After write

CAP-INTEL-04 is PROVEN.
Sum: **19.45 / 77 = 25.2597%**. Audited SYSTEM **25.3%**.
Prior row is in `state/model-c-score-history.jsonl` (event `pre-INTEL-04-PROVEN`).

READY is not accepted. No dashboard change. No scoring-rule change.
