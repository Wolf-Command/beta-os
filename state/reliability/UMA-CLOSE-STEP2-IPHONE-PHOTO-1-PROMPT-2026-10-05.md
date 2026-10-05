# UMA-CLOSE-STEP2-IPHONE-PHOTO-1 — surgical repair of Uma Blu staff close Step 2 photo upload (P0, Matt human test FAIL 19:18 WITA 5 Oct 2026)

You are the ONLY Beta writer for this slice. Surgical repair only. DO NOT redesign. Keep the six-step layout from UMA-CLOSE-6STEP-REBUILD-4 (BF-43d261ccbe02) exactly: 1 Choose date, 2 Shift report, 3 Bank receipts, 4 Count cash, 5 Review, 6 Submit. Do not change any other step's behaviour.

## Proven failure (already investigated by the executor — do not re-litigate, fix it)
Matt, real iPhone Safari, https://beta.wolfcommand.net/uma-blu-close, 29 Sep, Step 2: tapping TAKE/UPLOAD PHOTO showed the raw WebKit text "The string did not match the expected pattern."
- Throw site: `dashboards/uma-blu-close.html` line ~920 in `uploadShift()`: `const data = await res.json();` — no `res.ok` / content-type check, no try. WebKit's `Response.json()` on a non-JSON body throws `SyntaxError: The string did not match the expected pattern.`; the `onchange` handlers at ~1201/1202 then do `setMsg(err.message)` and show it raw. Same pattern in `uploadBankReceipt()` (~1053) and its handler (~1209).
- Why the body was not JSON: Beta (:8788) was being restarted repeatedly 19:16–19:23 WITA (launchd net.wolfcommand.serve-beta runs=97, last exit -15). cloudflared logged at 11:16:18Z `dial tcp 127.0.0.1:8788: connect: connection refused` and at 11:17:00Z `readfrom tcp ...->127.0.0.1:8788: write ...: use of closed network connection` (request body being streamed to an origin that died) → cloudflared answers 502 with an HTML error page → `res.json()` throws. The Beta origin itself always answers JSON for this route.
- Secondary real-iPhone gaps found in code: `scripts/core/bzg_daily_close.py` `save_close_receipt_bytes` rejects > 8,000,000 bytes (iPhone 24/48 MP photos exceed this); extension is chosen from filename/MIME only (Safari can send empty type, IMG_1234.HEIC, or no extension); HEIC originals are stored but the reader expects JPEG; `accept="image/*"` without HEIC hints.

## Required fix (exact scope)
### Client — `dashboards/uma-blu-close.html` only
1. Add one helper (e.g. `postPhoto(fd)`) used by `uploadShift` and `uploadBankReceipt`:
   - `fetch("/api/venue-close/receipt-photo", {method:"POST", credentials:"same-origin", body: fd})`.
   - Only parse JSON when `res.headers.get("content-type")` includes `application/json`; wrap parse in try/catch. Never call `res.json()` blind.
   - Retry automatically (max 3 attempts total, ~1.5 s then ~3 s backoff) when fetch rejects (network/TypeError) or status is 502/503/504/520–524 or the body is not JSON — this rides out a Beta restart. Rebuild the FormData per attempt from the same File.
   - On final failure: `console.error` the technical detail (status, content-type, attempt count) for diagnostics, then throw a staff-safe error. Never surface `err.message`, raw exception text, stack, provider/storage errors or internal ids to staff.
2. Step 2 visible states:
   - Uploading: disable TAKE PHOTO / UPLOAD PHOTO and show a visible loading line "Saving photo…" (an element with id `shiftSaving`).
   - Failure: show exactly the heading "PHOTO COULD NOT BE SAVED" and the line "Try again or upload an existing photo." (element id `shiftSaveFail`), with TAKE PHOTO and UPLOAD PHOTO usable again. Nothing else from the error.
   - Success: unchanged from cycle 4 (Shift report photo found · VIEW PHOTO · USE THIS REPORT · REPLACE).
   - Bank receipt upload failure (Step 3) uses the same two-line staff copy in its card; no other Step 3 change.
3. `shiftCam`, `shiftFile` (and `bankFile`) `onchange`: after reading `files[0]`, reset `e.target.value = ""` so re-choosing the same photo fires again. Handlers must never call `setMsg(err.message)` for uploads.
4. Input attributes: `shiftCam` → `accept="image/*,image/heic,image/heif,.heic,.heif"` and `capture="environment"`; `shiftFile` → same accept and NO capture attribute. Leave `bankFile` capture as is (out of scope), but add the same accept list.
5. Preview: keep `URL.createObjectURL(file)`; add `onerror` that hides the preview image (HEIC cannot render outside Safari) — never show an error for it.

### Server — minimal
1. `scripts/core/bzg_daily_close.py` `save_close_receipt_bytes`: raise the per-photo cap from 8,000,000 to 40,000,000 bytes (keep a cap; keep the 413 JSON shape with a staff_message "PHOTO COULD NOT BE SAVED"). Choose the stored extension by magic bytes first (JPEG FF D8 FF; PNG 89 50 4E 47; WEBP "RIFF....WEBP"; HEIC/HEIF ISO-BMFF `ftyp` with brand in heic/heix/hevc/hevx/heim/heis/mif1/msf1/heif → `.heic`), falling back to filename/MIME. Reject non-images with JSON 415 and the same staff copy.
2. Keep the ORIGINAL bytes byte-identical as the evidence file (already true — keep it). For HEIC/HEIF (and any image whose long edge > 3000 px), create a JPEG reading derivative next to the original (`<evidence_id>.read.jpg`, same evidence directory, so WOLF_EVIDENCE_ROOT / test isolation is respected) using `/usr/bin/sips` (macOS; HEIC capable) with a timeout, or Pillow for non-HEIC. Return `derivative_object_ref` and `kept_original: true`. Derivative failure must NOT fail the upload (original still saved; reader then reports it could not read → staff types figures with EDIT).
3. The shift/EDC read path that loads image bytes from `object_ref` (`_bzg_vision_image_bytes` / the close-receipt resolver) must use the derivative when present, with mime `image/jpeg`; otherwise the original. Do not change vision prompts/providers.
4. `/api/venue-close/receipt-photo` must always answer JSON. Any unexpected exception in this route → status 500 JSON `{"ok": false, "error": "photo_save_failed", "staff_message": "PHOTO COULD NOT BE SAVED"}` and the technical error/traceback logged to stderr (server log), never in the body.

## Tests (write and run)
- New `scripts/tests/test_uma_close_step2_iphone_photo1_20261005.py` (isolated temp DB + WOLF_EVIDENCE_ROOT temp dir, WOLF_TEST_MODE=1): multipart upload of (a) a 4032x3024 ~4 MB JPEG, (b) a >8 MB 24 MP JPEG, (c) a HEIC made with `sips -s format heic`, (d) the HEIC named `IMG_1234.HEIC` with content-type '' , (e) a JPEG with no filename extension and type application/octet-stream → all 200 JSON, original sha256 == stored file sha256, correct ext by magic, HEIC has a `.read.jpg` derivative; non-image → 415 JSON; forced exception → 500 JSON with staff copy only. Static checks: `res.json()` is never called blind in the upload path; staff copy strings present; shiftFile has no capture; accept includes heic.
- Regression must stay green: prove_uma_close_6step_rebuild4/3/2/1, complete1/2, nav_mobile1/2, queue1, evidence isolation tests.
- Real WebKit (Playwright webkit, iPhone 14 profile) on an ISOLATED copy server (temp DB copy + WOLF_EVIDENCE_ROOT temp dir; never live dirs): Step 2 TAKE PHOTO and UPLOAD PHOTO each with the files above via the real file inputs; plus a route that answers 502 text/html twice then passes (retry succeeds) and one that always answers 502 HTML (staff sees only the two-line copy, never "did not match").

## Hard rules
- Do NOT mutate or finalise Matt's real 29 Sep close (VDC-8fd544e2) or any 29 Sep live data — it stays incomplete. Do NOT touch 3 Oct (VDC-470e741f) or 4 Oct (VDC-64f5f529) data. Never upload to live from tests (WOLF_EVIDENCE_ROOT + temp DB only). Preserve the 52 quarantined synthetic files; delete nothing.
- Production pid 1297 on :8787 is sacred. Leave pid 2627 alone. Never print process command lines.
- No commit/push/merge/clean. No cloud agents. Never mark staff_ready / human_commissioned.
- Beta reload: run `python3 scripts/build-factory/bf_reload_gate.py`; only if it exits 0, do ONE `launchctl kickstart -k gui/$(id -u)/net.wolfcommand.serve-beta`, then wait for exactly one :8788 listener and /api/health 200. If the gate holds, wait 2 minutes and re-check (max 10 tries). NEVER restart Beta in a loop or from tests — repeated restarts are what broke Matt's upload.
- Do not edit GOD-MODE-DISPATCH.json, bf_dispatch.py or bf_reload_gate.py.

## Result
Write `state/reliability/UMA-CLOSE-STEP2-IPHONE-PHOTO-1-RESULT-2026-10-05.json` with: files_changed (with line ranges), throw_site, fix summary, tests_pass, tests_fail, regression results, webkit_proof summary, beta_pid_after_reload, staff_ready:false, human_commissioned:false. Finish with READY FOR HUMAN TEST only if tests_fail == 0; otherwise BLOCKED with reasons.
