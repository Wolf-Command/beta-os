# SPEC — Content Engine Haikal Fail Repair — 2026-09-24

**Run:** `BF-content-engine-haikal-fail-repair-20260924`
**Branch:** `build/wolf-command-rebuild` · soft head `f3ab8f7` (do not destroy)
**Workspace:** `/Users/wolfterminal/beta-os` · Beta :8788 only · Prod :8787 sacred
**RULE:** `docs/RULE-Content-Engine-Haikal-Fail-Repair-2026-09-24.md`
**AUDIT:** `docs/deliveries/AUDIT-Content-Engine-Deployed-Route-Truth-2026-09-24.md`
**CR:** `state/completion-register/content-engine-haikal-fail-repair-20260924.json`
**Parent CR:** `content-engine-staff-ux-20260924` (human_status FAILED_RETEST_REQUIRED)
**Commissioning:** `state/commissioning/CONTENT-ENGINE-HAIKAL-2026-09-24.md`
**Class:** Smallest coherent shared-root repair. Credit Conservation exception (human fail).
**Recorded:** 2026-09-24 13:00 WITA

## Goal
Make Haikal's Content Engine desk work on the **deployed Beta route under Haikal identity** for upload lifecycle, library registration, thumbnails, multi-brand registry ACL, in-place NAS index start, and Intelligence connect-or-hide — without breaking ZIP/download PASS.

## In scope (shared roots)

### 1. Upload lifecycle (P0)
Human stages (map real pipeline; never invent):

`SELECT FILE → UPLOADING → PROCESSING → SAVING TO NAS → INDEXING → GENERATING THUMBNAIL/PREVIEW → AVAILABLE IN LIBRARY → ✓ COMPLETE`

- Multi-file: Uploading N of M, individual where measurable, overall, completed count, failed count, current state.
- **COMPLETE = asset available through Library** — never because bytes hit temporary staging.
- On fail: what failed, which succeeded, which failed, retry. Preserve successful files; no forced full re-upload.
- Diagnose under Haikal REAL identity on deployed Beta route (`PERS-HAIKAL` / `haikalqilbari123@gmail.com`).

### 2. Upload → Library registration invariant
Trace ≥1 real Haikal-sim upload end-to-end:

`SUCCESSFUL UPLOAD → NAS FILE → HASH/EVIDENCE → INDEX → BRAND/SCOPE → LIBRARY RESULT → THUMBNAIL/PREVIEW`

Visible failed stage if any. No silent partial success.

### 3. Thumbnails
- Photos = image thumbs. Videos = useful poster + clear video indicator.
- Click opens preview. Test against real authorised NAS assets, not fixtures only.
- Blank tiles unacceptable as normal (fix `/api/assets/{id}/preview` failures that `onerror` remove the img).

### 4. Multi-brand library from Brand Registry
- Read authorised brands from **canonical Brand Registry** + aliases/mappings (not CE hard-coded `BRANDS` / `BRANDS_FALLBACK`).
- Brand selector on Plan/Upload/Library: **All Brands** + only authorised brands. Clean human names.
- ACL: Person→Role→Assignment→Scope→Permission→Audience.
- No discover via search/filters/URL/API/Intelligence/export if unauthorised. Hidden UI ≠ security.

### 5. Upload requires brand
- Brand before/during upload; preselect active context; obvious change.
- No silent filename guess. AI may SUGGEST brand; uncertain needs human confirm.
- Multi-brand only if canonical model allows.

### 6. Existing NAS — index in place
- Discover authorised NAS roots for all 8 required brands; map even when folder names ≠ brand names.
- Preserve original path/filename/provenance/hash/mapping/confidence/index state.
- Do **not** bulk move/rename/delete/duplicate NAS or require re-upload.
- Progressive indexing OK. Honest states: DISCOVERED / INDEXED / HASHED / THUMBNAIL READY / SEARCHABLE / FAILED / UNKNOWN.
- Owner/System coverage stats OK; Haikal sees media + human message if indexing underway.
- Never claim whole NAS available until measured.

### 7. Library UX (preserve simplified)
- Search first. Filters only where metadata supports: Brand, Category, Photo/Video, Location/Venue, Subject/Content Type, Date, Tags, Ready to Use. More filters for advanced.
- Thumbnails are the hero. No ops dashboard tiles before media.
- All Brands = search every authorised brand; brand label unobtrusive; can narrow to one.

### 8. Preserve ZIP/download PASS
- Regression test after changes. Preview retest after thumbs.

### 9. Wolf Intelligence — connect or hide
- Current scaffolding text is FAIL.
- Either connect to canonical Wolf Intelligence (ideas/captions/scripts/campaigns/improve/brand Q/authorised knowledge/media discovery/Plan assist) with **ACTIVE BRAND CONTEXT** + same permission model,
- **OR remove from staff nav until ready.**
- No CE agent. No swarm. No fabricated NAS knowledge. All Brands ≠ leak across unauthorised scopes.

### 10. Deployed-route truth defect
- Find root cause of progress discrepancy (stale Beta / wrong route / cache / FE-BE mismatch / permission path / NAS fail / fixture bypass / bad assertion).
- Record in AUDIT. Fix the shared root — do not only patch tests.

## Out of scope
- Prod :8787 mutation
- New agents / swarm / on-demand paid paths
- Speculative CE features beyond 1–10
- Bulk NAS reorganise
- Marking staff_ready / commissioned / Haikal PASS / Matt FINISHED ping

## Acceptance (engineering — still staff_ready=false)
1. Deployed Beta :8788 `/content-2.0` under Haikal-sim identity shows real lifecycle stages through COMPLETE only when Library-available.
2. ≥1 traced upload satisfies registration invariant with evidence artifact.
3. Library tiles show real thumbs/posters for authorised sample; blank not normal.
4. Brand selector sourced from Brand Registry; ACL deny proven for unauthorised brand.
5. Upload blocked/requires brand selection (no silent guess).
6. In-place NAS index started for authorised roots; honest coverage stats; Habitat visibility improved or honest "indexing underway".
7. ZIP/download regression PASS.
8. Intelligence connected usefully OR hidden from staff nav.
9. `docs/deliveries/GROK-REVIEW-Content-Engine-Haikal-Fail-Repair-2026-09-24.md` written.
10. Deterministic tests extended; FAIL=0 on pack tests.
11. Next human label only: **CONTENT ENGINE READY FOR HAIKAL RETEST** after Peaches verify + deployed evidence — never staff_ready from this pack.

## Tests to add/extend
- Lifecycle stage mapping + COMPLETE only on Library-available
- Registration invariant (NAS file + hash + index + library + thumb/preview fields)
- Thumbnail presence on real/fixture-NAS path
- Brand ACL deny
- ZIP regression (must stay green)
- Intelligence connect-or-hide assertion for SPECIALIST_CONTENT

## ADDENDUM — People Are Not Roles fold (2026-09-24 ~15:48 WITA)

Obey `docs/RULE-Wolf-People-Are-Not-Roles-2026-09-24.md` on close:
- Final verify: CE permissions from Assignment→Role, not PERS-HAIKAL / email hardcodes.
- Haikal-sim commissioning identity stays VALID.
- No historical attribution rewrite. No Cursor re-prompt. No new pack. No staff_ready.
- See `docs/deliveries/NOTE-CE-Haikal-Repair-People-Are-Not-Roles-Fold-2026-09-24.md`.

## ADDENDUM — Staff Shell Cleanup (2026-09-24 ~17:30 WITA)

Owner fold into this SPEC / run. **No new pack.** Cursor pid must not be killed for this fold.

Source of truth: `docs/deliveries/ADDENDUM-Content-Engine-Staff-Shell-Cleanup-2026-09-24.md`  
Fold note: `docs/deliveries/NOTE-CE-Staff-Shell-Cleanup-Fold-Into-Active-Pack-2026-09-24.md`

Acceptance extensions (engineering still `staff_ready=false`):
- Staff header/nav matches ADDENDUM target; engineering chrome removed from normal staff view
- Brand selector from Brand Registry + scope; WI hidden from primary CE nav until useful
- Upload: no permanent 7-stage pipeline on main page; truthful in-flight status; Retry on fail; no healthy-NAS green banner
- MEDIA TYPE vs CONTENT TYPE separation per ADDENDUM taxonomy note (canon `MEDIA_TYPES` in `scripts/wolf_naming.py`; no invented CONTENT TYPE enum)
- Library: thumb · human title · Brand·Media type·Date; technical names in Preview; ZIP/download preserved

**Gate:** Peaches verify must include shell criteria before `CONTENT ENGINE READY FOR HAIKAL RETEST`. If EXIT without shell work → FAIL shell criteria.
