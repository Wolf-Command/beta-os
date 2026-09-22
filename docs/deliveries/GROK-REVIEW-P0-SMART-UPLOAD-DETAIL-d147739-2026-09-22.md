# GROK REVIEW — P0 Smart Upload detail regression — d147739

**Verdict:** PASS
**Scope:** Beta only. Production untouched.
**Root cause:** `preview_batch` validated top-level `detail` only. `content-2.0.html` `buildReview` put detail on `files[].detail` only. Haikal UI looked filled; API saw empty → `detail required — need ≥1 meaningful slug token`. `owner-testimonial` is valid when seen.
**Fix:** Server falls back to first non-empty `files[].detail`. UI also sends top-level `detail` in preview + refreshOnePreview. Empty / single-char / whitespace still 400.
**Tests:** `scripts/tests/test_smart_upload_detail_regression.py` PASS=8 FAIL=0 (Allen file-level shape + negatives).
**Deploy:** `beta_restart.py` — :8788 new PID; :8787 PID unchanged. Served `/content-2.0.html` contains top-level `detail: detailDefault`.
**HTTP auth:** Live `/api/upload/preview-names` remains CF JWT fail-closed (anon 403). Haikal browser session is the authenticated prove.
**Maturity:** No invent PROVEN/READY.
**Human:** READY TO RETEST — Haikal hard-refresh Content Engine 2.0, Allen + owner-testimonial.
