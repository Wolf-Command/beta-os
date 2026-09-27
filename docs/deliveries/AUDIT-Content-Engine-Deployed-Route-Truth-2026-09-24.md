# AUDIT — Content Engine Deployed-Route Truth — 2026-09-24

**Run:** `BF-content-engine-haikal-fail-repair-20260924`
**Recorded:** 2026-09-24 13:00 WITA
**Beta :**8788 (`serve_beta`) · **Prod :**8787 pid 15975 sacred
**Soft head:** `f3ab8f7` preserved
**Haikal identity:** `PERS-HAIKAL` · `haikalqilbari123@gmail.com` · audience `SPECIALIST_CONTENT` · landing `/content-2.0`

## Wolf-wide lesson
**repo test ≠ deployed Beta route ≠ human commission.**

`BF-content-engine-staff-ux-20260924` ENGINEERING_PASS (PASS=48 + wave1) asserted upload stage **labels exist** and map from pipeline enums. Haikal on the deployed desk saw **no meaningful progress / completion**. Human overrides engineering for staff_ready.

## Routes Haikal hits
| Surface | Route |
|---------|-------|
| Content Plan | `/content-2.0` → view `plan` |
| Upload | `/content-2.0#upload` / view `upload` |
| Library | `/content-2.0#library` / view `library` |
| Intelligence | `/content-2.0` → view `wolf` |
| Brand peers | `/content-habitat` etc. alias → `/content-2.0?brand=…` |

Unauthenticated `GET /content-2.0` on localhost returned **403** JSON scope-forbidden shell (`Content workspace is not in authorised scope`) — proves route is identity-gated; fixture/dev subject bypasses are not Haikal's browser path.

## Upload API surface (Beta)
- `POST /api/upload/smart` — multipart smart ingest
- `POST /api/upload/preview-names`
- `GET /api/upload/recent?brand=…`
- Library: `GET /api/assets?…`, `GET /api/assets/{id}/preview|download`, `POST /api/assets/zip`

## Root-cause bullets (progress discrepancy)

1. **COMPLETE never painted on success path (FE defect)**
   In `dashboards/content-2.0.html` upload success branch: status text becomes `Finished — N files. Open Library…` but **`paintUploadLifecycle("complete")` is never called**. Lifecycle can stall on uploading/processing/saving even when POST returns ok. Engineering tests that only grep stage **label strings** in HTML pass while Haikal sees no completion.

2. **Lifecycle is client-side theatre over a single POST — not the required pipeline**
   UI stages today: Uploading → Processing → Saving to Library → Complete (4 labels). Owner/Haikal required chain includes SAVING TO NAS → INDEXING → GENERATING THUMBNAIL/PREVIEW → AVAILABLE IN LIBRARY. FE advances stages around one `/api/upload/smart` fetch; there is no SSE/poll of NAS verify → index → thumb → library-available. Tests mapped enums; humans needed real stages.

3. **COMPLETE semantics ≠ Library-available**
   Historical Smart Upload path writes Beta `library_v2` mirror / DB rows; `nas_received` only after NAS verify. UI can treat response `ui_status` loosely while asset is not yet searchable/thumbable in Library. Human FAIL on Upload Completion + Upload→Library Registration matches this gap.

4. **Fixture / assertion bypass vs Haikal identity**
   Pack tests use Haikal subject headers / local assertions. Deployed Haikal session is Cloudflare Access + permission chain. Unauthenticated probe gets 403. Progress/registration failures under real ACL/NAS are invisible to HTML-label unit checks.

5. **Thumbnails: preview fail → blank tiles**
   Library grid uses `<img … src="/api/assets/${id}/preview" onerror="this.remove()">` (and/or text-kind badges in older paths). Preview failures remove the image → blank tiles as "normal." Human FAIL on Thumbnails; Preview = RETEST REQUIRED.

6. **Brand Registry not wired into CE selectors**
   Canonical `org_brands` exists (e.g. Atrium Lombok, Uma Blu, Habitat, Blu Zone Rainforest…) but CE still ships hard-coded `BRANDS` / `BRANDS_FALLBACK` (habitat, umablu, atrium, selo, tropik). Missing The One + Goss Group; names ≠ Owner canonical list; content `brands` table effectively Habitat-centric. Brand Filtering = RETEST REQUIRED; All Brand NAS Visibility = NOT YET PROVEN.

7. **NAS index thin / folder≠brand**
   Mounts under `/Volumes/01-Media-Library` (SMB). Tops include AMG, AMG-Atrium, BZG, Brand-Assets, Clients, GGV, _Imports, _Shared…
   `nas_index` sample ~100 rows (Brand-Assets, _Shared, GGV, Clients, BZG, AMG-Atrium) — **not** full tree. Habitat human visibility FAIL is consistent with incomplete in-place index + folder-name≠brand mapping.

8. **Wolf Intelligence = scaffolding**
   Staff WI panel explicitly lists "Not connected yet" / honest non-generation copy. Human FAIL. Rule: connect canonical WI with brand+ACL **or hide** from staff nav — no fabricated NAS knowledge.

## Brand Registry status
| Source | Status |
|--------|--------|
| `org_brands` in content library DB | PRESENT (partial relative to 8 required human names) |
| CE `/api/brands` / UI fallback | HARD-CODED subset — **not** registry-driven |
| Aliases/mappings for NAS folders | INCOMPLETE / UNKNOWN for several required brands |

## NAS roots per required brand (diagnosis snapshot)

| Brand (canonical) | NAS evidence (working) | Index state |
|-------------------|------------------------|-------------|
| Atrium | `/Volumes/01-Media-Library/AMG-Atrium` (+ AMG) | PARTIAL sample |
| Uma Blu | BZG / Uma-Blu-Cafe under BZG | PARTIAL sample |
| Selo Group | UNKNOWN / not clearly topped | UNKNOWN |
| Habitat | GGV / Brand-Assets / Clients? (folder≠name) | PARTIAL — human FAIL visibility |
| Tropik | UNKNOWN as top-level folder | UNKNOWN |
| The One | UNKNOWN | UNKNOWN |
| Blu Zone Rainforest Resto | BZG/Rainforest-Restaurant | PARTIAL sample |
| Goss Group | UNKNOWN / Brand-Assets Shared? | UNKNOWN |

Honesty: do **not** claim whole NAS available. Progressive in-place index required.

## Repair verification — 2026-09-24 13:35 WITA

Shared-root fix is on the restarted Beta process (`serve_beta.py`, port 8788). Production pid 15975 on :8787 was not restarted.

| Check | Result |
|-------|--------|
| `GET /api/content/repair-status` on :8788 | `run_id=BF-content-engine-haikal-fail-repair-20260924`, `complete_means=library_available`, `staff_ready=false` |
| `GET /content-2.0` with `X-Wolf-Subject` and no Cloudflare JWT | **403** — seat gate still holds. Client subject headers are not a Haikal browser session. |
| Haikal-scoped pipeline trace (same `handle_smart_upload` the server imports, `PERS-HAIKAL` scopes, `data_lane=test`) | asset 14, `library_available=true`, NAS file + hash + index + thumbnail, `ui_status=COMPLETE`. Atrium upload **403 forbidden**. |
| Habitat in-place index | 3 files indexed. Message: not the whole library. No move/rename/delete. |
| Staff nav | `apply_content_staff_desk` removes the Wolf Intelligence tab for `SPECIALIST_CONTENT`. Owner file keeps it. Intelligence is not connected. |

Evidence: `state/commissioning/evidence/CE-HAIKAL-UPLOAD-TRACE-2026-09-24.json`.

staff_ready remains false. This verification is not a Haikal human PASS.


## Preserve
- ZIP / download completion + integrity PASS — regression mandatory
- Content Plan PASS
- Library search structural PASS / multi-select PASS
- Soft head uncommitted work

## Repair implication
Fix shared roots in one pack: lifecycle+COMPLETE semantics, registration invariant, thumbs/preview, registry brand selector+upload-requires-brand, start in-place NAS index for authorised brands, Intelligence connect-or-hide, deployed Beta verify under Haikal-sim — then Peaches re-verify. staff_ready remains false.
