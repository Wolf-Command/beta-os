# RULE — Content Engine Upload State + Library Search (2026-10-01)

## Locks
- Beta only: `/Users/wolfterminal/beta-os`, `scripts/serve_beta.py` on **:8788**.
- Prod **:8787** sacred — never mutate process, tree, DB, or configs used by prod.
- `staff_ready=false`. Do not invent LIVE. No Exit Report. No Wolf Intelligence pack from this run.
- Do not ask Haikal or Matt to diagnose.
- Do **not** issue Haikal retest — Peaches holds retest until this pack verifies.
- Hold prior FAIL + repair provenance (`BF-content-engine-haikal-upload-14fail-20261001`). Do not force-mark BBQ batch successful.
- BBQ reconcile: no delete by assumption; auto-fix only when deterministic; ambiguous → human review queue.
- Poster / derivative fail **after** FILE STORED ≠ upload fail. Retry Preview = existing asset only (hash/stable id); no re-upload / no duplicate NAS bytes.
- One Library: empty search must not look empty when assets exist; brand is a **filter**; search case-insensitive across real indexed fields only (no fake metadata); filters **AND**; shoot date ≠ silent upload date; **server-side** search + pagination (never load ~38k client-side).
- SOFTWARE-FIRST: SPEC → data → perms → rules → API → UI → tests. Reuse Wolf Core / existing upload + Library stack. No new agents/dashboards. No tip-checkout of finance/ops lanes.
- Credit exception active: this run id only (see `state/final-completion/beta-house-20261001/CREDIT-CONSERVATION.json`).

## Stop
Eng prove matrix PASS on Beta → STOP for Peaches light verify. Peaches alone issues Haikal retest after verify.
