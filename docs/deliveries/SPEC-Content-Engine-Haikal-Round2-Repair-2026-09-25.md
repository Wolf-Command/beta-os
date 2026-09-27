# SPEC — Content Engine Haikal Retest Round 2 Repair (25 Sep 2026)
Owner order: Matthew, 25 Sep 2026 22:01 WITA. One bounded repair. Credit Conservation exception (real human commissioning FAIL).
Round 2: Content Plan PASS · Shell PARTIAL FAIL · Library FAIL · Upload PARTIAL PASS · Brand context FAIL · staff_ready=false.
Beta only (/Users/wolfterminal/beta-os, :8788). PROD :8787 SACRED. Do not redesign working parts (Content Plan, Upload form structure, greeting, ZIP flow).

## Peaches pre-diagnosis (verified on Beta DB 25 Sep 22:10)
R1 SHARED BRAND ROOT CAUSE:
- core/wolf_shell.build_whoami(person_id=PERS-HAIKAL) returns a SEED assignment ASG-GGV-CONTENT / ROLE-CONTENT / SCOPE-GGV-CONTENT.
  It does NOT read the real DB assignment ASG-HAIKAL-CD-1 (POS-GGV-CREATIVE-DIRECTOR-1, ACTIVE) in catalog/content_library.sqlite org_assignments/org_assignment_scopes.
- ASG-HAIKAL-CD-1 active scopes are only: SCOPE-GGV-CONTENT, SCOPE-GGV-HABITAT-LEAD, SCOPE-CRM-HABITAT-LEAD, SCOPE-GGV-CONTENT-LIBRARY.
- core/nas_library.BRAND_SCOPES maps those to 4 brands only (habitat/selo/tropik/theone). Atrium needs SCOPE-AMG, umablu/rainforest need BZG scopes, goss needs SCOPE-WOLF-GROUP.
- org_brands already has all 8 required org ids (AMG-ATR, BZG-UMA, GGV-SELO, habitat, GGV-TROPIK, GGV-THEONE, BZG-RAIN, GGV-GOSS). Registry rows are fine.
- /api/brands (legacy content_brands_table) returns Habitat only — any UI still reading it is wrong.
- Haikal saw EMPTY dropdowns on deployed Beta, so there is also a front-end binding/field bug (slug vs id / wrong endpoint / auth fail). Find it with a real CF-shaped Haikal session sim against deployed :8788.

## Owner authorisation (this message)
Creative Director assignment must authorise ALL 8 content brands: Atrium, Uma Blu, Selo Group, Habitat, Tropik, The One, Blu Zone Rainforest Resto, Goss Group (+ All Brands).
Implement as a CONTENT-ONLY scope on the Creative Director assignment (e.g. SCOPE-WOLF-CONTENT-ALL-BRANDS mapped in BRAND_SCOPES to the 8 content brands). Must NOT grant finance/HR/leads/ops of AMG/BZG. Access derives from Assignment, never name.

## Fix (shared providers only, no page patches)
1. ONE brand-context provider: whoami reads real DB assignments; authorised_brands from Registry+scopes; one active brand (persisted once, e.g. localStorage + ?brand=) consumed by header, Content Plan, Library default filter, Upload preselect, theme, WI context.
2. Header: ☰ | [BRAND ▼] | CONTENT ENGINE | CONTENT PLAN | LIBRARY | UPLOAD | Hi, {first_name} | SIGN OUT. Hamburger = app switcher: Content Engine, Wolf Intelligence (marked unavailable if not useful). No Boards/Up/Back/engineering/system items. WI not in tab row.
3. ONE asset resolver for existing NAS index rows: real thumbnail/poster (generate/lookup, no move/rename of NAS tree, no re-upload), title = canonical title else ORIGINAL FILENAME, never "Untitled" if a filename exists; brand, media type, minimal metadata; no asset IDs shown.
4. Library: big search, brand filter (This Brand / All Authorised Brands / individual, from same provider), more filters, Select All, Deselect, Download ZIP when >0 (preserve working flow), clean grid. Preview modal: video playable, image large; title, brand, subject, shoot date, location, media type, content type/tags; Download + Close.
5. Upload: brand dropdown from provider, preselect active brand, user may change. Keep Brand/Stage/Media Type/Shoot Date/Subject/Location/Detail → Files → Review & Upload. Media Type (Photo/Video/Audio/Graphic) separate from Content Type (B-roll/Testimonial/Property/Food/People/Event/Lifestyle).
6. Upload progress: "Uploading 2 of 7 · 43%" → Processing → Saving to NAS → Adding to Library → ✓ Complete. Complete = file on NAS AND index row AND retrievable via Library API. Latest Uploads per-item: Uploading/Processing/Saving/Available in Library/Failed.

## Gate (deployed Beta :8788 Haikal-sim, all must pass)
G1 top brand dropdown populated (8 + All) · G2 switching brand changes Plan/Library/Upload context · G3 Library brand filter populated · G4 Library thumbs+titles resolve on real NAS media (report counts: resolved thumb / filename-title / Untitled=0) · G5 preview works (video+image) · G6 select/multi-select/ZIP still works · G7 Upload brand populated+preselected · G8 upload status real+simple · G9 Latest uploads show NAS/Library outcome · G10 Haikal = Creative Director via Assignment.
Plus: Content Plan tests still green; prod :8787 untouched; staff_ready=false.

## Stop rules
No new dashboards, agents, broad nav rebuild, speculative features. Commit on Beta branch with tests (extend scripts/tests/test_content_engine_haikal_fail_repair.py or new test_content_engine_haikal_round2.py). Restart ONLY beta serve_beta.py if needed. Write evidence JSON to state/commissioning/evidence/CE-HAIKAL-ROUND2-GATE-2026-09-25.json. Print EXIT summary with G1–G10 PASS/FAIL.
