# GROK PLAN — P0 Smart Upload detail regression — 2026-09-22

## Class
FIX (regression). Staff blocker. Haikal cannot upload. Beta `:8788` only. No Production mutation.

## Root cause (Peaches diagnosed — verify then fix)
`POST /api/upload/preview-names` → `smart_upload.preview_batch` validates **top-level** `body.detail` / `body.default_detail` via `phase26_team.detail_valid`.

`dashboards/content-2.0.html` `buildReview()` only puts detail on **`files[].detail`** (`owner-testimonial`) and does **not** send top-level `detail`.

So UI shows Subject=Allen testimonial + Default detail=owner-testimonial, but preview API sees empty top-level detail → exact error:
`detail required — need ≥1 meaningful slug token`

`owner-testimonial` IS a meaningful slug (`detail_valid` True when tested at top-level).

## Fix (smallest correct)
1. **Server** `scripts/smart_upload.py` `preview_batch`: if top-level detail empty, derive from first non-empty `files[].detail` (and still require ≥1 meaningful token). Keep empty/useless detail failing.
2. **UI** `dashboards/content-2.0.html`: also send top-level `detail: detailDefault` in preview body (and refreshOnePreview). Defense in depth.
3. **Regression test** exact case: subject `Allen testimonial`, detail only on `files[0].detail` = `owner-testimonial` → preview HTTP 200. Empty detail still 400. Single-char / whitespace still fail. Deterministic naming unchanged.
4. Do not change hash/duplicate logic. No Metricool. No prod.

## Prove
- Unit/integration test PASS with exact failing example
- Hit live Beta `:8788` `/api/upload/preview-names` with file-level-only detail → 200
- Anon still gated as today
- Restart/reload Beta content-2.0 if needed

## EXIT
`EXIT: SUCCESS` with test counts + curl proof + files touched.
