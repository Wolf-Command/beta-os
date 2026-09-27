# AUDIT — GGV Finance Nota Storage Gap vs Owner Canon
**Date:** 2026-09-24 ~12:54 WITA · **Auditor:** Grok executor (Peaches) · **Surface:** Beta `/Users/wolfterminal/beta-os`  
**Parent run:** `BF-ggv-finance-mobile-nota-20260924` ENGINEERING_PASS PASS=138 FAIL=0  
**Correction run:** `BF-ggv-finance-nota-storage-accountant-20260924`  
**Canon:** RULE ADDENDUM Owner lock 2026-09-24 ~12:51 WITA

## Method
Read-only compare of current code/state against Owner storage + accountant canon. No prod touch. NAS mount probed live on Mac.

## NAS root discovery
| Item | Result |
|------|--------|
| Existing canon | `scripts/core/nas_library.py` `MEDIA_LIBRARY = Path("/Volumes/01-Media-Library")` |
| Connection commissioning register | SMB mounts from 192.168.77.130; canonical roots include `01-Media-Library` |
| Live probe 2026-09-24 ~12:53 WITA | `media_library_connected() == True` |
| `Finance/` under media library | **Absent** (not created yet) |
| GGV under media library | Present as media ops tree (`GGV/2026/photos|video|design|marketing`, Footage, …) — not Finance/Notas |
| Wolf content write jail | `_Imports/Wolf-Library` only — separate from Finance path contract |
| Verdict | **NAS root KNOWN** = `/Volumes/01-Media-Library`. Finance hierarchy path contract designed; folder creation deferred to implementation. Not `BLOCKED_NAS_ROOT`. |

## Gap matrix

| Canon | Current | Gap |
|-------|---------|-----|
| Wolf DB = index/metadata only | SQLite tables `ggv_notas`, `ggv_nota_files`, `ggv_uploads`, `ggv_vendors`, … hold workflow + `rel_path` | Partially OK as index; **path points at local blobs** |
| Canonical evidence on NAS | `STORE_DIR = BETA_ROOT / "state" / "ggv-finance-nota" / "blobs"` in `scripts/core/ggv_finance_nota.py` L49 | **FAIL — local Mac app state** |
| B2 = backup/DR + honest backup_state | No `backup_state` column/field on `ggv_nota_files` | **FAIL — missing** |
| Hierarchy `Finance/GGV/Notas/YYYY/MM` | Blobs under `state/ggv-finance-nota/blobs/{upload_id}/…` | **FAIL** |
| Per-file metadata set (original/canonical name, hash, size/type, nota/vendor/upload ids, timestamp, provenance, backup_state) | `ggv_nota_files`: `file_id, upload_id, nota_id, filename, content_type, sha256, rel_path, role, evidence_id, created_at` | **PARTIAL** — has hash/filename/type/ids; missing canonical_filename, size_bytes, vendor_id on file row, backup_state, nas_rel_path, explicit provenance fields |
| Users do not browse filesystem | Staff UI via `/ggv/finance` | OK for UX intent; storage still local |
| No auto ZIP of historical notas | No ZIP storage path found in finance nota module | OK (absence) |
| Year → Month → Nota views | History tab = search/list; no Year/Month logical grouping UI | **FAIL — missing** |
| MONTH EVIDENCE PACK export | Not present | **FAIL — missing** |
| Retention preserve-all / no auto-delete | Uploads `preserved INTEGER DEFAULT 1`; no retention job found | OK-ish; must keep explicit no-auto-delete |
| EXTERNAL ACCOUNTANT role | `OPERATING_ROLES = ("ROLE-MATT", "ROLE-CONTENT-MGMT")` only; held-back payment/bank/policy perms exist | **FAIL — role + accountant perms/scope missing** |
| Accountant workspace | Nav tabs: overview / notas / vendors / history only | **FAIL / optional** — absent; add only if cheap |
| Never fake BACKED UP | N/A (field absent) | Risk if added without wiring — SPEC requires UNKNOWN/PENDING default |
| Existing blobs to migrate | `find state/ggv-finance-nota/blobs` → **0 files** | Migration is path cutover + empty migrate; still must not leave STORE_DIR as canonical |

## Code anchors (factual)
- `scripts/core/ggv_finance_nota.py:49` — `STORE_DIR = BETA_ROOT / "state" / "ggv-finance-nota" / "blobs"`
- `scripts/core/ggv_finance_nota.py:276-287` — `ggv_nota_files` schema (no backup_state / nas path / size)
- `scripts/core/ggv_finance_nota.py:54-56` — operating roles Matt + Content Mgmt only
- `dashboards/ggv-finance.html` — tabs overview/notas/vendors/history; no Accountant; no Year/Month pack export
- `scripts/core/nas_library.py:34,150` — MEDIA_LIBRARY + ALLOWED_WRITE_PREFIX content jail

## Commissioning impact
- Cards `CMQ-GGV-FINANCE-NOTA-MATT` / `CMQ-GGV-FINANCE-NOTA-AMANDA` seeded READY_TO_TEST in `owner_commissioning_queue.seed_templates`.
- **Action:** HOLD / `BLOCKED_EXTERNAL` with reason `STORAGE_ARCH_PENDING` until arch pack ENGINEERING_PASS.
- Do not invent staff_ready / commissioned / telegram_retired.

## Summary (gaps to close)
1. Migrate canonical store from `state/.../blobs` → NAS `Finance/GGV/Notas/YYYY/MM` under `/Volumes/01-Media-Library`.
2. Extend file metadata + honest `backup_state` (default UNKNOWN/PENDING).
3. Seed `GGV EXTERNAL ACCOUNTANT` role + scope-enforced permissions; deny matrix on page/API/search.
4. Add Year/Month/Nota history views without mutating evidence.
5. Add MONTH EVIDENCE PACK export ZIP as product only (non-canonical).
6. Optional thin Accountant tab only if reuse is cheap; no fake totals.

## Non-claims
- NAS Finance folder not pre-created (honest).
- B2 protection for finance paths not proven (must not claim BACKED UP).
- Accountant person identity not invented.
- Parent pack engineering pass does **not** equal storage-canon pass.
