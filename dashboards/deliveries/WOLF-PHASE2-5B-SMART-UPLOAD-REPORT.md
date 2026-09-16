# WOLF Phase 2.5B — Smart Upload Naming MVP
**For:** Peaches only  
**When:** 2026-09-15 13:25 WITA  
**Lane:** Beta OS `/Users/wolfterminal/beta-os/` on **:8788 ONLY**  
**URL:** https://beta.wolfcommand.net/content-2.0.html  

---

## Executive result: **PASS**

Smart Upload Naming MVP is live on Beta. Team can drop 5–50 camera RAW files without renaming; Content Engine generates Wolf canonical filenames + structured metadata. Content Plan preserved. **:8787 untouched. No Metricool write. No publish. No live AI. No semantic/CV matching. Test lane does not pollute ops Library.**

---

## Acceptance checklist

| # | Criterion | Result |
|---|---|---|
| 1 | Multi-file batch (preview + sequential upload) | **PASS** |
| 2 | Brand required | **PASS** |
| 3 | Stage default RAW (EDIT/FINAL available) | **PASS** |
| 4 | Shoot date required | **PASS** |
| 5 | Subject required | **PASS** |
| 6 | Location optional | **PASS** |
| 7 | Per-file detail (optional, editable in Review) | **PASS** |
| 8 | Original filename preserved (path-stripped; ext lowercased) | **PASS** |
| 9 | Server owns canonical Wolf name | **PASS** |
| 10 | Unique sequence; never overwrite | **PASS** |
| 11 | Meta persists in SQLite | **PASS** |
| 12 | Plan/card optional nullable | **PASS** |
| 13 | No camera rename required | **PASS** |
| 14 | Unsafe MIME/ext rejected (415) | **PASS** |
| 15 | No FS paths in UI / assets API JSON | **PASS** |
| 16 | Clear statuses UPLOADING/CHECKING/READY/FAILED + LIBRARY_* | **PASS** |
| 17 | Test lane does not pollute ops Library | **PASS** |
| 18 | Content Plan still works | **PASS** |
| 19 | :8787 untouched (PID 22123) | **PASS** |
| 20 | Automated suite 36/36 | **PASS** |

**Automated:** `python3 scripts/tests/test_phase2_5b_smart_upload.py` → **pass=36 fail=0**

---

## Naming

Pattern: `brand_STAGE_type_subject_detail_YYYYMMDD_sequence.ext`

Example: `habitat_RAW_video_habitat-villa_pool-wide_20260915_001.mp4`

- Lowercase tokens; **STAGE** uppercase `RAW|EDIT|FINAL`
- RAW → `_001`; EDIT/FINAL → `_v01`
- Slug-normalize free text
- Collision-safe vs DB + `library_v2/{STAGE}/` (`_x2` suffix only if exact name exists)
- Never trust original as canonical

---

## UX (content-2.0.html → Upload)

3-step wizard:

1. **Batch** — Brand*, Stage* (default RAW), MediaType*, ShootDate*, Subject*, Location?, default Detail?, Plan?, Card?
2. **Files** — drag/select (keep camera names)
3. **Review** — Preview | Original | Detail? | Generated name → **UPLOAD**

NAS banner is honest: connected vs not. **`nas_received` always false** this MVP (writes Beta `library_v2` only; no fake NAS received).

---

## APIs (8788)

| Method | Path | Notes |
|---|---|---|
| GET | `/api/nas/status` | Honest mount probe |
| POST | `/api/upload/preview-names` | Name preview; `can_upload` |
| POST | `/api/upload/smart` | Multipart smart ingest; `can_upload` |
| GET | `/api/upload/recent` | Recent smart uploads (lane-aware) |
| GET | `/api/assets?data_lane=` | Default **operational** (hides test) |

Legacy `POST /api/upload/remote` + staging commit unchanged.

---

## DB (additive)

Migration: `scripts/migrations/migrate_phase2_5b_smart_upload.py` (+ `003_phase2_5b_smart_upload.sql` notes)

Columns added on `assets` + `staged_assets`:  
`original_filename, canonical_filename, subject, detail, location, shoot_date, sequence_token, media_type, uploaded_by, uploaded_at, content_plan_id, content_card_id, processing_status, library_status, data_lane, batch_id`

Queryable text meta only — **no vectors**.

Library statuses: `UPLOAD_RECEIVED` → `CHECKING` → `LIBRARY_READY` | `FAILED`

---

## Files changed

| Path | Role |
|---|---|
| `scripts/wolf_naming.py` | **NEW** naming module |
| `scripts/smart_upload.py` | **NEW** smart ingest helper |
| `scripts/migrations/migrate_phase2_5b_smart_upload.py` | **NEW** idempotent migrator |
| `scripts/migrations/003_phase2_5b_smart_upload.sql` | **NEW** notes |
| `scripts/migrations/__init__.py` | **NEW** |
| `scripts/serve_beta.py` | Routes + assets lane filter + EDIT stage |
| `scripts/stage_inspector.py` | STAGES += EDIT |
| `dashboards/content-2.0.html` | 3-step Smart Upload wizard |
| `scripts/tests/test_phase2_5b_smart_upload.py` | **NEW** acceptance |
| `scripts/tests/fixtures_smart_upload/` | Test JPEGs (test lane) |

**Backups:**  
`archive/baks/*phase2-5b-20260915-132017`  
`catalog/backups/content_library.sqlite.bak-phase2-5b-20260915-132017`

---

## Serving status

- **:8788** listening (`127.0.0.1:8788`, Python serve_beta) — **OK**
- **:8787** PID **22123** unchanged — **OK**
- Health: `{"ok": true, "root": "beta-os", "planner": "sqlite"}`
- NAS probe: connected at `/Volumes/01-Media-Library` (message honest; no NAS ingest)

---

## Limitations (MVP)

- No NAS copy/sync — Beta `library_v2` only
- No Content Plan asset-matching / READY/PARTIAL/FILM auto
- No embeddings / CV / semantic match
- No Metricool write / publish / Remotion / CF / live AI
- Original basename: path-stripped + ext lowercased (underscores kept)
- Video/audio fixtures not in automated suite (JPEG magic path covered); real Haikal files will exercise video
- Cloudflare Access JWT still not wired (dev subject header)

---

## Confirmations (hard)

| Guard | Status |
|---|---|
| NO :8787 touch | **CONFIRMED** (PID 22123) |
| NO Metricool write | **CONFIRMED** |
| NO publish | **CONFIRMED** |
| NO live AI | **CONFIRMED** |
| NO semantic match | **CONFIRMED** |
| NO test contamination of ops Library | **CONFIRMED** (`data_lane=test` filtered) |

---

## Haikal — test instructions (5–10 REAL files)

**URL:** https://beta.wolfcommand.net/content-2.0.html  
**Subject (dev):** set local subject to `haikalqilbari123@gmail.com` if prompted / already defaulted.

### Steps
1. Open **UPLOAD** tab.
2. Read NAS banner (connected or not — do not expect “NAS received”).
3. **Step 1 Batch:** Brand=habitat (or your brand), Stage=RAW, Media type matching files, Shoot date = shoot day, Subject e.g. `habitat-villa`, Location optional, Detail optional, Plan/card optional.
4. **Step 2:** Drop **5–10 real** camera files (do **not** rename).
5. **Step 3:** Check generated names; tweak Detail per file if needed → **UPLOAD**.
6. Confirm statuses → READY; open **LIBRARY** and find Wolf names; originals shown as metadata.
7. Open **Content Plan** — confirm fortnight plan still loads/edits.

### Feedback questions (reply to Peaches)
1. Were generated names clear enough without training?
2. Which fields felt unnecessary or missing (location, plan link, detail)?
3. Did any real file type fail (codec/ext)?
4. Is Review step useful, or should upload start sooner?
5. Any confusion vs “NAS received” messaging?
6. Approx time for your 5–10 file batch?
7. Anything blocking daily use?

---

## Paths / URL summary

- Root: `/Users/wolfterminal/beta-os/`
- UI: `dashboards/content-2.0.html` → https://beta.wolfcommand.net/content-2.0.html  
- DB: `catalog/content_library.sqlite`
- Library: `library_v2/{RAW,EDIT,FINAL}/`
- Report copies: `/tmp/WOLF-PHASE2-5B-SMART-UPLOAD-REPORT.md` + `dashboards/deliveries/WOLF-PHASE2-5B-SMART-UPLOAD-REPORT.md`
