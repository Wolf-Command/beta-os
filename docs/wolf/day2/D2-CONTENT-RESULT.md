# D2 — Content Engine background truth — 27 Sep 2026

TECHNICAL PROOF of the catalog counts and of a read-only exception list. DEPLOYED ROUTE PROOF on Beta `:8788` for that list. Not STAFF READINESS. Not HUMAN COMMISSIONING. Not OPERATING ADOPTION.

Beta/local only. Production `:8787` stayed pid 15975. Beta `:8788` was restarted with `launchctl kickstart -k` on `net.wolfcommand.serve-beta` only, from pid 4443 to pid 23945, still `scripts/serve_beta.py`. No money, bank, or payment action. No NAS file was moved, renamed, deleted, or written. No brand row was rewritten. `staff_ready` stays false. Human commissioned: no.

## BEFORE

Catalog `catalog/content_library.sqlite` at the start of this pack, read-only. Same figures as `state/nas-estate/FINAL-TRUTH-20260927.json` (`as_of` `2026-09-27T02:37:13+08:00`).

| | |
| --- | ---: |
| HASHED | 63246 |
| searchable (`SEARCHABLE` or `HASHED`) | 63246 |
| FAILED | 124 |
| genuine failures (not `missing_file`) | 124 |
| UNKNOWN brand | 4787 |
| theone | 0 |

Fail reasons: `thumb_failed` 107, `thumb_timeout` 15, `hash_error:OSError` 2.

The 124 rows were already in `state/nas-estate/exceptions.json`. They were not on the Library page and not on the Progress exception panels. Library search excludes `FAILED`.

Production listener pid 15975. Beta listener pid 4443. Auth mode `cloudflare_access`. Unsigned `/api/assets` is 403.

## DONE

No new module. No `FOLDER_RULES` change. No `nas_index` update. Unknown rows stayed UNKNOWN.

### Exceptions

`read_library_exceptions()` reads `state/nas-estate/exceptions.json` and returns filename, brand, and a plain reason. It does not return a volume path. Owner audience and the Creative Director role (`ROLE-GGV-CREATIVE-DIRECTOR`) receive `nas_exceptions` on `GET /api/assets`. Other content seats do not. The Library page adds a collapsed "Preview exceptions" list when that payload is present. Progress, which is owner-only, adds "Library preview exceptions" from the same file.

`scripts/serve_beta.py`, `scripts/core/progress_read_model.py`, and `dashboards/progress.html` already had other uncommitted work. The exception wiring in those three files is in the working tree that pid 23945 is running. It is not in this commit, so the other rebuild diff stays unstaged. The reader, the Library panel, and the test are committed.

### UNKNOWN folders

4,787 rows. Grouped by `source_root` and the first path segment, then the second segment where that bucket is large. No folder name is an unambiguous brand alias, so nothing was written to the brand-map config.

| files | hashed | failed | source_root | top folder |
| ---: | ---: | ---: | --- | --- |
| 2860 | 2857 | 3 | 01-Media-Library | `_Imports` |
| 1642 | 1641 | 1 | 01-Media-Library | `Clients` |
| 122 | 122 | 0 | 01-Media-Library | `BZG` |
| 106 | 105 | 1 | 01-Media-Library | `GGV` |
| 26 | 26 | 0 | 01-Media-Library | `Brand-Assets` |
| 25 | 25 | 0 | 01-Media-Library | `_clickup-attachment-archive` |
| 4 | 4 | 0 | 01-Media-Library | `_Shared` |
| 2 | 2 | 0 | 00-Editing-Workspace-3 | `_INBOX` |

Second segment for the large buckets:

| files | path |
| ---: | --- |
| 1660 | `01-Media-Library/_Imports/One-Touch-2026-06-03` |
| 1642 | `01-Media-Library/Clients/Tampah-Reserve` |
| 1188 | `01-Media-Library/_Imports/PC-6TB-2026-06-02` |
| 122 | `01-Media-Library/BZG/Staff` |
| 106 | `01-Media-Library/GGV/Footage` |
| 25 | `01-Media-Library/_clickup-attachment-archive/2026-06` |
| 19 | `01-Media-Library/Brand-Assets/AMG` |
| 12 | `01-Media-Library/_Imports/atlas-intake` |
| 4 | `01-Media-Library/Brand-Assets/Shared` |
| 3 | `01-Media-Library/Brand-Assets/GGV` |

Left UNKNOWN for a person to decide:

- `_Imports` (One-Touch, PC-6TB, atlas-intake) is an unsorted drop. A shoot titled "SURF SELONG" is a place name, not the folder `Selong-Selo`.
- `Clients/Tampah-Reserve` is a client. Tampah Reserve is not one of the eight registry brands.
- `BZG/Staff` is staff documents. Uma Blu and Rainforest already have their own folders and are not in this bucket.
- `GGV/Footage` holds Mandalika Beach Club, Silver workshop, Ziggy & Morrison, and similar. GGV is five brands, not one.
- `Brand-Assets/AMG` here is company fonts (`WorkSans`, `GildaDisplay`). `Brand-Assets/AMG/Atrium` is already `atrium` (27 rows) and is not in this UNKNOWN set.
- `Brand-Assets/GGV` here is three holding logos (`GGV-Logo-All-Gold.png`, `GGV-Logo.png`, `GGV-logo-ALL-Black.png`). Habitat, Selo, and Tropik kits under that tree are already mapped.
- `Brand-Assets/Shared` is music beds. `_Shared` includes Tampah social posts. `_clickup-attachment-archive` is an archive. `_INBOX` is two Atlas team-guide PDFs.

`_needs_sorting` exists on the volume and has 0 catalog rows.

### The One

Registry row `GGV-THEONE`, status SPECIFIED, display name "The One". Aliases in `org_brand_aliases`: `The One`, `theone`, `the-one`. Catalog rows with `brand_slug=theone`: 0. Catalog `rel` containing those aliases: 0.

Read-only directory listing, not a copy:

- `/Volumes/01-Media-Library` top: `AMG`, `AMG-Atrium`, `BZG`, `Brand-Assets`, `Clients`, `GGV`, `_Imports`, `_Shared`, `_clickup-attachment-archive`, `_needs_sorting`.
- `Brand-Assets/GGV`: Habitat, Selo, Tropik, fonts, logos, palettes, style-guides. No The One directory.
- `GGV`: `2025`, `2026`, `AI-Generated` (Habitat only), `Footage` (Amanda at Selong Selo, Mandalika Beach Club, Silver workshop, Ziggy & Morrison).
- `BZG`: Catering, PC-6TB, Pool-Bar, Rainforest-Restaurant, Rooftop-Bar, Room-Service, Staff, Uma-Blu-Cafe, Underground-Bar.
- `Clients`: Habitat, Selong-Selo, Tampah-Reserve, Tropic-at-Selong.
- `00-Editing-Workspace-3/active-projects/GGV`: Habitat, Selong-Selo. `Atlas-Drop`: Atrium, Habitat, Selo, Tropik, Uma-Blu.
- Shallow name scan of `GGV/2025`, `GGV/2026`, `_ARCHIVE`, `scratch`, `02-Stock-Assets-1`, and `03-Templates`: 0 hits for `the one`, `theone`, `the-one`, `the_one`.
- Stubs `/Volumes/00-Editing-Workspace` and `/Volumes/02-Stock-Assets` were not readable.

No The One folder and no catalogued The One file were found. This does not claim every non-media file inside `_Imports` was opened by hand. Those media files are already in the catalog, and none of their paths use the alias.

## VERIFIED

```
python3 scripts/tests/test_nas_estate_index.py | tail -12
PASS  search still hits hashed atrium — 1
PASS  search still hits hashed selo — 1
PASS  search still hits hashed habitat — 1
PASS  search count 63246 — hashed=63246 searchable=63246
PASS  library search count is the eight brands — matched=53615 eight=53615 shared_or_unknown=9631
PASS  live search stays unready
PASS  124 genuine failures listed — 124
PASS  exception list hides volume paths
PASS  owner sees exceptions
PASS  creative director role sees exceptions
PASS  other content seats do not get the exception list
EXIT: SUCCESS PASS=59 FAIL=0
```

```
python3 scripts/tests/test_content_engine_staff_ux.py | tail -3
PASS  production :8787 still up
PASS=54 FAIL=0
EXIT: SUCCESS
```

The first live-catalog run failed once because the read-only connection had no `sqlite3.Row` factory (`TypeError` in `_nas_card`). The test connection was given the row factory. That was the one repair. The suite then exited 0. No second repair.

Catalog searchable count is 63246 (`HASHED`, and `SEARCHABLE` or `HASHED`). `nas_library_search` for all brands with `SCOPE-WOLF-GROUP` returns `matched=53615`. The other 9631 HASHED rows are `SHARED_STOCK` 4849 and `UNKNOWN` 4782. The search compares `lower(brand_slug)` to the tokens `SHARED_STOCK` and `UNKNOWN`, so those two tokens do not match. That filter was not changed.

Beta after restart, short-lived simulation key removed afterwards (`cf-sim-public.jwk.json` absent). Counts only:

```
anon 403
cd_who 200 ROLE-GGV-CREATIVE-DIRECTOR org_assignments
cd_assets 200 nas_matched 53615 staff_ready False ex_count 124 ex_items 124 volumes False
cd_reasons {'thumb_failed': 107, 'thumb_timeout': 15, 'hash_error:OSError': 2}
cd_progress 403
owner_assets 200 nas_matched 53615 ex_count 124 items 124
owner_progress 200 count 124 items 124 empire 124 staff_ready False commissioned False
```

Served HTML: Creative Director `GET /content-2.0` 200 and the page source contains `paintLibraryExceptions`. Owner `GET /progress` 200 and the page source contains `Library preview exceptions`. Creative Director `GET /progress` 403. A signed-in browser click of the collapsed list was not done.

Listeners after the restart: `:8787` pid 15975. `:8788` pid 23945.

## WAITING HUMAN

- Which of the UNKNOWN folders, if any, belong to a registry brand. No mapping was applied.
- Where The One media lives, if it lives anywhere outside the trees listed above. Nothing was copied or invented.
- Whether the library is usable. `staff_ready` is still false. This pack does not commission Haikal.

## BLOCKERS

- The One: 0 catalog rows, and no alias-named folder in the listed NAS trees.
- UNKNOWN: 4,787 rows. Folder names were not unambiguous.
- 124 preview/hash failures stay failed. They are listed. They are not repaired.
- Owner and Creative Director library search `nas_matched` for all brands is 53615, not 63246. The catalog searchable count is 63246.

## NEXT HUMAN TEST

On Beta `:8788`, signed in as himself. Owner: open Progress and confirm "Library preview exceptions" lists 124 files (filename, brand, plain reason), and open Library and confirm the collapsed "Preview exceptions" list. Creative Director: open Library and confirm the same 124. Progress stays owner-only. Do not add files to make The One look populated. Do not mark the desk staff-ready from this list.

HUMAN COMMISSIONED: no

RESULT: PASS
