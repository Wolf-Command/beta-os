# Model C ledger reconcile — CAP-INTEL-02 / 03 PROVEN

**Date:** 2026-09-18
**Actor:** Matthew Goss, owner audit (this turn). Peaches wrote the ledger only.
**Dashboard:** not changed. `scripts/core/progress_read_model.py` does not read this ledger.

## Check before write

Ledger file: `state/model-c-baseline-assessments.json` (77 rows).

Credits (locked): ABSENT 0, SPECIFIED 0.05, BUILT 0.25, PROVEN 0.80, READY 1.00.

Prior sum, counted from the file before this write: **17.80 / 77 = 23.1169%** (audited 23.1%).
States before: ABSENT 1, SPECIFIED 42, BUILT 22, PROVEN 9, READY 3.
CAP-INTEL-02 and CAP-INTEL-03 were both BUILT.

Expected after both move BUILT 0.25 → PROVEN 0.80: 17.80 + 1.10 = **18.90**.
18.90 / 77 = 24.5454…% → rounded audited **24.5%**.
The file agreed. Write proceeded.

## After write

Same file, same 77 rows.
States: ABSENT 1, SPECIFIED 42, BUILT 20, PROVEN 11, READY 3.
Sum: **18.90 / 77 = 24.5455%**. Audited SYSTEM **24.5%**.

Prior rows for these two caps are appended, not overwritten, in `state/model-c-score-history.jsonl` (event `pre-INTEL-02-03-PROVEN`).

The 17 Sep snapshot `docs/deliveries/MODEL-C-SYSTEM-EVIDENCE-LEDGER-2026-09-17.md` is left as history. It still says SPECIFIED for these two. That file is not the live ledger.

CAP-INTEL-04 stays BUILT in this write. This note does not promote it.

## Not done

- Progress dashboard still shows the legacy figure.
- `docs/MODEL-C-SYSTEM-NUMERIC-CREDITS.md` headline baseline is not rewritten. Scoring rules unchanged.
- Production untouched.
