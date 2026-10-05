# Cursor brief — BF-content-engine-upload-state-library-search-20261001

Owner expanded scope **before** Haikal retest. Peaches holds Haikal retest. Credit exception active for this run only.

## Read and execute
1. `docs/deliveries/SPEC-Content-Engine-Upload-State-Library-Search-2026-10-01.md`
2. `docs/RULE-Content-Engine-Upload-State-Library-Search-2026-10-01.md`
3. Prior: `state/build-factory/RESULT-CONTENT-ENGINE-HAIKAL-UPLOAD-14FAIL-20261001.md` + FAIL JSON under `state/final-completion/beta-house-20261001/`

## Live tree
- Workdir `/Users/wolfterminal/beta-os` · soft head `e0896ae` (preserve dirty sibling work)
- Beta `:8788` pid **30689** · log `/tmp/serve_beta.log`
- Prod `:8787` pid **15975** sacred — never touch
- Key: `scripts/smart_upload.py`, `scripts/core/content_engine_repair.py`, `scripts/serve_beta.py` (`query_assets` + upload), `dashboards/content-2.0.html` (Library override + upload lifecycle)

## Must (SOFTWARE-FIRST)
1. **Lifecycle** — FILE STORED survives DERIVATIVE FAILED; staff Retry Preview on existing asset; no dup NAS/catalog.
2. **BBQ reconcile** — Tropik `bbq-night-grill` ~14 vs 12 catalog: inventory NAS/catalog/derivatives/gaps; deterministic fix only; UNKNOWN → human review list; no force-success / no delete-by-assumption.
3. **Library** — case-insensitive server-side search; filters AND; shoot_date ≠ upload date; page ≤48; empty q must not fake-empty; upload discoverable in Library.
4. Prove **U1–U5 · B1–B3 · L1–L7** on Beta. Write RESULT + evidence JSON.
5. STOP for Peaches verify. **Do not issue Haikal retest. staff_ready=false. Do not invent LIVE.**

## Out
Prod · diagnose asks to Haikal/Matt · Content Plan redesign · finance/ops tip-checkout · new agents · Exit Report / Wolf Intelligence

## Done when
Gates proven, commit + tests, EXIT printed, stopped for Peaches. Haikal retest remains Peaches-owned HOLD.
