# Wolf Connection Commissioning Register
Date: 22 Sep 2026 ~20:35 WITA
Root: `/Users/wolfterminal/beta-os`
Method: live Mac mounts + Integration Health readonly + code/env key presence (no secret values) + System-Registry B2 docs.

## Rollup
| Bucket | Count / note |
|--------|----------------|
| COMMISSIONED READ | 0 (none Owner-commissioned under this program yet) |
| COMMISSIONED WRITE | 0 |
| WRITE LOCKED (recommend) | ESB, Yanolja, Alchemist new-write, Klaviyo write, Metricool publish, Email auto-send, Production mutate, Sheets new workflow |
| UNKNOWN | B2 health, Klaviyo live, GWS/Drive/Gmail in Beta, Sheets, CF JWT verify, full NAS asset total |
| BLOCKED | Missing access will be listed explicitly when hit — none inventing secrets |
| TRANSITIONAL | Alchemist RO, Klaviyo reader code, local library_v2 Content Engine |
| RETIRED | ClickUp, Telegram |
| PRODUCTION MUTATIONS | NONE (pid sacred; this program Beta-only) |

## NAS
| Field | Value |
|-------|-------|
| NAS CONNECTION | SMB mounts from 192.168.77.130 (Mr Wolf) — CONNECTED |
| CANONICAL ROOTS | `/Volumes/01-Media-Library` (ops media); also 00-Editing-Workspace, 02-Stock-Assets, 03-Templates, 04-Time-Machine, 05-Wolf-Vault-Mirror |
| Media Library top | AMG, AMG-Atrium, BZG, Brand-Assets, Clients, GGV, _Imports, _Shared, _clickup-attachment-archive, _needs_sorting |
| TOTAL DISCOVERED ASSETS | UNKNOWN full tree; shallow maxdepth4 Media Library ≈ 39986 files |
| INDEXED in Wolf | content_library.sqlite assets (incl. smart_upload + NAS sample index); Brand-Assets + continue tops (AMG-Atrium/BZG/GGV/Clients/_Shared caps); full NAS tree UNKNOWN; staff_ready=false |
| UNCLASSIFIED | Vast majority of NAS — not full-tree indexed |
| DUPLICATES | Hash dup-check on upload (never silent discard); full NAS dup pass UNKNOWN |
| RIGHTS UNKNOWN | Default until classified |
| UPLOAD PATH | Smart Upload → staging → Beta library_v2 mirror → `_Imports/Wolf-Library/...` on NAS; `nas_received=true` only when file verified on NAS |
| SEARCH PATH | `/api/assets` (scope-gated) + `/api/nas/index/search` (sample); relative paths only |
| BACKUP STATUS | Historical B2 LaunchAgents (footage-b2-sync, b2-archive, backup); R2 disabled 18 Aug cost lock. Last success tonight = UNKNOWN |
| RESTORE STATUS | Drill docs exist; live restore prove = UNKNOWN / not run |
| RBAC STATUS | Person→Role→Assignment→Scope→Permission→Audience; brand scope enforced on upload + assets API |
| DESKTOP / MOBILE | Global Wolf shell + Content Engine Library (select all / deselect / ZIP / provenance / NAS badge) |
| HAIKAL HUMAN TEST | engineering prep v2 done (operator path + checklist); Haikal human upload/search/preview/ZIP **not yet signed** |
| READY FOR STAFF TOMORROW | **NO** (staff_ready=false; proven=false; ready=false) |

## Systems (summary)
See `WOLF-CONNECTION-OWNER-APPROVAL-LIST-2026-09-22.md` for YES/NO.
Per-system detail continues under executor / next packs. Do not patch old connection lists — this register is canonical from this directive.
