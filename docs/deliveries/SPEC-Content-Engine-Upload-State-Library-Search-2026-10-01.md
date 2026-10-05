# SPEC — Content Engine Upload State + Library Search (1 Oct 2026)

**Run:** `BF-content-engine-upload-state-library-search-20261001`
**Owner order:** Matthew via Peaches — expanded scope **before** Haikal retest (Haikal retest HOLD)
**Parent:** `BF-content-engine-haikal-upload-14fail-20261001` (Peaches light verify PASS · commit `e0896ae` · ffmpeg PATH · E1–E8 PASS · staff_ready still false)
**Class:** Credit Conservation exception (active) · human commissioning follow-on · Beta only
**Workspace:** `/Users/wolfterminal/beta-os` · branch `build/wolf-command-rebuild` · soft head `e0896ae` (preserve uncommitted sibling work)
**Live Beta:** `scripts/serve_beta.py` pid **30689** · port **8788** · log `/tmp/serve_beta.log`
**Prod:** `:8787` pid **15975** READ-ONLY SACRED
**RULE:** `docs/RULE-Content-Engine-Upload-State-Library-Search-2026-10-01.md`
**Thin BF brief:** `state/build-factory/briefs/BRIEF-BF-content-engine-upload-state-library-search-20261001.md`
**Paste brief:** `briefs/cursor/BF-content-engine-upload-state-library-search-20261001.md`
**GATE:** `state/build-factory/GATE-BF-content-engine-upload-state-library-search-20261001.json`
**Prior FAIL/RESULT:** `state/final-completion/beta-house-20261001/CONTENT-ENGINE-HAIKAL-UPLOAD-14FAIL-20261001.json` · `state/build-factory/RESULT-CONTENT-ENGINE-HAIKAL-UPLOAD-14FAIL-20261001.md`
**staff_ready:** false · **Haikal retest:** HOLD until Peaches verify of **this** pack

## Context (facts — do not re-litigate)
- Prior root cause accepted: launchd PATH missing Homebrew ffmpeg → poster fail after NAS write → UI treated `library_available=false` as batch fail despite HTTP 200 / bytes on NAS.
- Catalog Tropik `bbq-night-grill` batch `bmuowp00n`: **12** rows (seq 001–012); owner reported **14**; two filenames UNKNOWN / not force-success.
- Poster backfill already done for asset ids 19–32; do not claim human PASS from that.

## Goal
1. Honest **upload lifecycle** states so store success is not erased by derivative failure; staff can Retry Preview without re-upload.
2. **Reconcile** Haikal Tropik BBQ ~14 MOV (NAS vs catalog vs derivatives vs pre-storage fail vs dups) without destroying provenance.
3. **One Library** search/filter that is case-insensitive, AND-combined, server-side paginated, and discoverable after upload.

## SOFTWARE-FIRST order
SPEC → data (assets / nas_index / derivatives / hashes) → perms (brand ACL) → rules (lifecycle + reconcile) → API (`/api/upload/smart`, annotate, `/api/assets`, nas library search) → UI (`dashboards/content-2.0.html`) → tests.

Prefer shared roots: `scripts/smart_upload.py`, `scripts/core/content_engine_repair.py`, `scripts/serve_beta.py` `query_assets` / upload handlers, Library override in content-2.0. Reuse Wolf Core. No finance/ops tip-checkout.

---

### 1. Upload lifecycle model (P0)
Canonical stages (map real pipeline; never invent fake progress):

`RECEIVED / UPLOADING → FILE STORED → INDEXED → DERIVATIVES PROCESSING → READY`

Fail states (distinct):
- `STORAGE FAILED`
- `INDEX FAILED`
- `DERIVATIVE FAILED` (includes poster/thumb/preview)

Rules:
- Poster / derivative fail **after** FILE STORED ≠ upload fail.
- Staff sentence example: **"Video uploaded successfully. Preview processing failed — Retry Preview."**
- **Retry Preview** operates on the **existing** asset (stable id / content hash). No second NAS write; no duplicate catalog row.
- Idempotent: re-submit of same bytes → honest duplicate / already-in-library path (preserve prior 14fail E6 behaviour).
- UI must not treat `!library_available` alone as full upload failure when `nas_received` / FILE STORED is true — split outcome: stored vs preview-ready.
- Keep human-useful `staff_message`; stack traces only in admin/audit logs (`state/content-engine/upload-audit.jsonl` or equivalent).

### 2. BBQ reconcile (Tropik · detail `bbq-night-grill`)
Inventory and classify each of the ~14 owner-reported MOVs against:
- NAS bytes present?
- Catalog `assets` row?
- Derivatives (poster/thumb) present?
- Failed pre-storage (never written)?
- Duplicate / same-hash collision?

Actions:
- Auto-repair **only** when deterministic (e.g. missing poster for existing NAS+row → generate poster; missing index for existing NAS with clear hash → index once).
- Never delete by assumption. Never force-mark commissioning success.
- Ambiguous (especially the **2 UNKNOWN** filenames vs 12 catalog rows) → write a human-review list under `state/build-factory/` or `state/commissioning/evidence/` — do not invent filenames.
- Preserve batch `bmuowp00n` provenance.

### 3–11. One Library (search + filters)
- **Empty search ≠ empty library** when authorised assets exist (honest empty only when truly zero matches for current filters).
- **Brand is a filter**, not a requirement that blanks the whole library incorrectly; support This Brand / All Authorised / individual from brand-context provider.
- **Search** is case-insensitive across **real indexed fields**: title/canonical name, description if present, original + canonical filenames, brand, stage, media type, content type/tags if stored, shoot date, subject, location, detail, and other real columns — **no fake metadata**.
- **Filters AND** together (q AND brand AND media_type AND stage AND readiness AND shoot_date AND subject AND location …).
- **Shoot date** filter must use shoot date, never silently substitute upload/`date_added`.
- **Server-side** search + pagination (page size ≤48). Never download ~38k assets to filter in the browser. Remove/disable any leftover client-only filter path that re-fetches unbounded lists then `.filter` in JS (legacy `loadLibrary` before the override is a smell — ensure the active path is server-paged only).
- After a successful upload, asset must be **discoverable** in Library via search/filter for that brand/detail/subject within the same session (refresh OK; silent invisibility FAIL).
- Preserve Select All / Deselect / Download ZIP when >0 (regression).

### 12. Engineering prove matrix (Owner / Peaches — all required on Beta :8788)

**Upload lifecycle**
- U1 FILE STORED with DERIVATIVE FAILED → staff message + Retry Preview; **not** counted as full upload fail
- U2 Retry Preview succeeds without re-upload / without dup NAS bytes / without second catalog row
- U3 STORAGE FAILED still hard-fails with human-useful error + Retry upload where safe
- U4 multi-file partial: stored items stay; derivative-only fails retryable per item
- U5 prior E1–E8 regression still green (ffmpeg PATH / smart upload / no prod touch)

**BBQ reconcile**
- B1 written inventory: NAS ∩ catalog ∩ derivatives ∩ gaps for `bbq-night-grill`
- B2 deterministic fixes applied only where proven; UNKNOWN gap listed for human review
- B3 no force-success; no deletes by assumption; batch provenance intact

**Library**
- L1 empty `q` + This Brand with assets → non-empty grid (or honest “no assets for this brand”)
- L2 case-insensitive `q` hits filename/subject/detail (and other real fields claimed)
- L3 combining filters uses AND (narrows, never ORs unexpectedly)
- L4 shoot_date filter does not match on upload date alone
- L5 pagination: page size ≤48; `matched`/`pages` honest; no full-corpus client load
- L6 fresh upload appears in Library search for its brand/detail
- L7 ZIP / multi-select still works

Evidence:
- `state/build-factory/RESULT-BF-content-engine-upload-state-library-search-20261001.md`
- `state/commissioning/evidence/CE-UPLOAD-STATE-LIBRARY-SEARCH-GATE-2026-10-01.json`
- tests under `scripts/tests/` (extend or add; FAIL=0 on touched suite)

### 13. Stop / out of scope
- STOP for **Peaches light verify**. Do **not** issue Haikal retest. Do not ping Matt READY.
- Out: Prod mutate · invent LIVE · staff_ready=true · Exit Report · Wolf Intelligence · ask Haikal/Matt to diagnose · redesign Content Plan · tip-checkout finance/ops · new agents · speculative breadth

## Deliver / EXIT
Commit(s) on Beta branch with tests; restart **only** Beta serve if required; print EXIT with U*/B*/L* PASS/FAIL, commit hash, test counts, honest residuals (esp. BBQ UNKNOWN). `staff_ready` remains false.
