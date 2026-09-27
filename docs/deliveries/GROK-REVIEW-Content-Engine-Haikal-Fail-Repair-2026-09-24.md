# GROK REVIEW — Content Engine Haikal Fail Repair — 2026-09-24

**Run:** `BF-content-engine-haikal-fail-repair-20260924`  
**Branch:** `build/wolf-command-rebuild` · soft head `f3ab8f7` preserved  
**Beta:** :8788 restarted (`serve_beta.py`) · **Prod:** :8787 pid 15975 untouched  
**Human status:** `FAILED / RETEST REQUIRED` · **staff_ready:** false  
**CAP:** SPECIFIED  
**Tests:** repair PASS=57 FAIL=0 · staff UX PASS=52 FAIL=0 · wave1 PASS=21 FAIL=0

Engineering PASS does not override Haikal. This pack does not mark the desk commissioned, does not set staff_ready, and does not ping Matt FINISHED.

## What was wrong

Haikal on the deployed desk saw no meaningful upload completion. The page could finish a POST and still never call the complete stage. The four on-screen stages were client theatre around one request. Complete was not tied to a Library-available asset. Preview failures removed the image and left blank tiles. The brand menu was a hard-coded Content Engine list, not the Brand Registry. Wolf Intelligence told staff it was not connected.

## What changed

Shared root only. ZIP download still posts to `/api/assets/zip`.

1. **Lifecycle.** The desk shows Select file → Uploading → Processing → Saving to NAS → Indexing → Generating thumbnail/preview → Available in Library → ✓ Complete. Complete is painted only when `library_available` is true. A multi-file run shows progress, keeps successes, and retries only the failed files.
2. **Registration.** A successful response carries NAS file, hash, index, brand, library, and thumbnail. The failed stage stays visible. A Habitat test-lane upload (asset 14) came back `library_available=true` with all of those fields. An Atrium upload under Haikal’s scopes returned 403.
3. **Thumbnails.** Grid preview is a JPEG (photo thumb or video poster). A video tile keeps a Video mark. If the image fails, the tile says “Preview not ready” instead of disappearing. Click opens the real file.
4. **Brands.** The selector reads `org_brands` plus aliases. Missing required names were added to the registry as SPECIFIED, not invented as a page list. Haikal (SCOPE-GGV-CONTENT) sees Habitat, Selo Group, Tropik, and The One. Atrium, Uma Blu, Blu Zone Rainforest Resto, and Goss Group stay off his menu. Upload has no brand until a person chooses one. A filename can only suggest a brand, and the suggestion is not applied.
5. **NAS index.** Authorised files are indexed in place. Habitat: 3 files in this pass, with an explicit note that this is not the whole library. Selo, Tropik, The One, and Goss Group stay UNKNOWN where the folder mapping is unknown. Nothing was moved, renamed, deleted, or duplicated.
6. **Wolf Intelligence.** It is not connected to canonical Wolf Intelligence, so the staff nav no longer shows it. The owner file still contains the tab. No Content Engine agent and no swarm were added.

## Deployed route

`GET http://127.0.0.1:8788/api/content/repair-status` returns this run id, `complete_means=library_available`, and `staff_ready=false`.

`GET /content-2.0` with only `X-Wolf-Subject: haikalqilbari123@gmail.com` is still **403**. Beta is in Cloudflare Access mode, so a client subject header is not Haikal’s browser session. The pipeline trace used the same upload function the restarted Beta process imports, with `PERS-HAIKAL` scopes. That is not a human session on the desk.

Evidence: `state/commissioning/evidence/CE-HAIKAL-UPLOAD-TRACE-2026-09-24.json`  
Audit addendum: `docs/deliveries/AUDIT-Content-Engine-Deployed-Route-Truth-2026-09-24.md`

## Still required

Peaches verify, then Haikal on the real desk. The only next human label, after that, is **CONTENT ENGINE READY FOR HAIKAL RETEST**. staff_ready stays false until Haikal passes and the owner accepts.

## Tests

| Pack | Result |
|------|--------|
| `scripts/tests/test_content_engine_haikal_fail_repair.py` | PASS=57 FAIL=0 |
| `scripts/tests/test_content_engine_staff_ux.py` | PASS=52 FAIL=0 |
| `scripts/tests/test_haikal_content_ux_wave1.py` | PASS=21 FAIL=0 |

EXIT: SUCCESS

## SHELL CLEANUP — 2026-09-24 ~17:50 WITA

Same run `BF-content-engine-haikal-fail-repair-20260924`. Prior EXIT SUCCESS above covers the shared-root repair. It does **not** clear `CONTENT ENGINE READY FOR HAIKAL RETEST`. This section is the staff shell only. staff_ready stays false. Matt was not pinged.

### What the staff desk shows now

Header, left to right: menu, brand selector, CONTENT ENGINE, Content Plan, Library, Upload. Right side: Hi, {first name} and profile. The first name comes from the person record, not from a typed email.

Normal staff view no longer includes Boards, Wolf, Up, Back, Home, Dev identity, SPECIALIST_CONTENT, ROLE-CONTENT, the raw email, a healthy-storage green banner, or the operator-depth block. Those stay on the owner file. Server permissions are unchanged. Haikal’s Creative Director seat `ASG-HAIKAL-CD-1` → `ROLE-GGV-CREATIVE-DIRECTOR` was not reverted.

The brand menu still reads the Brand Registry through Assignment scope. All Brands appears only when that scope covers more than one brand. The eight required names remain registry rows.

Wolf Intelligence stays off the primary staff nav.

Upload no longer keeps the seven-stage strip on the page. A single status line appears while a file is moving. Retry still keeps successes. A connected library does not paint a green banner.

Media type on the form is Photo, Video, Audio, or Graphic (`image` / `video` / `audio` / `graphic`). There is no new Content Type list. Subject and detail still name the file. `broll` is not offered as a media kind.

Library cards lead with the thumbnail, then a human title from subject and detail, then brand, media type, and date. Technical filenames stay in Preview. Select, ZIP, and download are still on the page.

### Not claimed

Peaches has not verified this shell. The desk is not ready for a Haikal retest ping. staff_ready is false. A signed-in browser session was not available on `:8788` (the route still returns 403 without a real session). The shell was checked by rendering the staff and owner documents in the tests.

Beta `:8788` was restarted (pid 64587 at 17:49). Production `:8787` pid 15975 was not touched. Soft head remains `f3ab8f7`.

### Tests

| Pack | Result |
|------|--------|
| `scripts/tests/test_content_engine_haikal_fail_repair.py` | PASS=68 FAIL=0 |
| `scripts/tests/test_content_engine_staff_ux.py` | PASS=53 FAIL=0 |
| `scripts/tests/test_content_engine_staff_shell_cleanup.py` | PASS=44 FAIL=0 |
| `scripts/tests/test_haikal_content_ux_wave1.py` | PASS=21 FAIL=0 |

EXIT: SUCCESS


## PEACHES VERIFY — 2026-09-24 ~18:08 WITA

**Verdict:** PASS (ENGINEERING_PASS)  
**Independent re-run:** Repair PASS=68 FAIL=0 · Staff UX PASS=53 FAIL=0 · Shell cleanup PASS=44 FAIL=0 · Wave1 PASS=21 FAIL=0  
**ADDENDUM Staff Shell Cleanup:** PASS  
**staff_ready:** false (locked)  
**human_status:** FAILED_RETEST_REQUIRED  
**Next human label:** CONTENT ENGINE READY FOR HAIKAL RETEST  
**Prod :8787:** pid 15975 untouched · soft head `f3ab8f7` · Beta :8788 pid 64587  
**Breadth:** none armed · `PEACHES_VETO_CREDIT_CONSERVATION`  
**Run:** DONE / ENGINEERING_PASS closed
