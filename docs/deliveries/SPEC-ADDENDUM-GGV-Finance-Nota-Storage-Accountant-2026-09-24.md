# SPEC ADDENDUM — GGV Finance Nota Storage + EXTERNAL ACCOUNTANT
**Date:** 2026-09-24 · **Owner lock:** ~12:51 WITA · **Governor:** Peaches · **Executor:** Grok on Wolf Command  
**Run:** `BF-ggv-finance-nota-storage-accountant-20260924`  
**Parent pack:** `BF-ggv-finance-mobile-nota-20260924` (ENGINEERING_PASS PASS=138 FAIL=0; staff_ready/proven/ready/commissioned/telegram_retired all false)  
**Class:** Architecture correction to existing Finance pack ONLY. Credit conservation exception (Owner-named). Zayen Finance reserved.

## 1. Intent
Correct canonical evidence storage so original nota documents live on NAS (not Mac local `state/.../blobs`), keep Wolf DB as index/metadata, add honest backup state, Year→Month→Nota views, MONTH EVIDENCE PACK export (non-canonical), and seed `GGV EXTERNAL ACCOUNTANT` role+permissions with scope enforcement. Hold Matt/Amanda phone commissioning until this pack ENGINEERING_PASS + Peaches verify.

## 2. NAS root (reuse — do not invent a second root)
| Fact | Value |
|------|-------|
| Canonical NAS media library | `/Volumes/01-Media-Library` (`scripts/core/nas_library.py` → `MEDIA_LIBRARY`) |
| Mount evidence (this Mac, 2026-09-24 ~12:53 WITA) | `media_library_connected() == True` |
| Existing Wolf upload jail (content library) | `/Volumes/01-Media-Library/_Imports/Wolf-Library` (`ALLOWED_WRITE_PREFIX`) |
| **Finance evidence path contract** | `/Volumes/01-Media-Library/Finance/{ENTITY}/Notas/{YYYY}/{MM}/` |
| Initial entity | `Finance/GGV/Notas/{YYYY}/{MM}/` |
| Finance folder today | **Does not yet exist** on NAS — create on first write / migration; do not invent alternate roots |
| B2 | Backup/DR observe-only until real proof — never fake `BACKED UP` |

Relative storage keys stored in Wolf DB must be relative to `MEDIA_LIBRARY` (or an explicit finance root constant that resolves under it), never absolute `/Volumes/...` in client payloads.

## 3. Storage roles
1. **Wolf DB** (`catalog/content_library.sqlite` finance tables) = workflow + index + metadata ONLY. No source-document blob columns as sole storage.
2. **NAS** = canonical original evidence files (PDF/JPG/PNG individually).
3. **B2** = backup/DR. `backup_state` honesty required.
4. **Local `state/ggv-finance-nota/blobs`** = **FORBIDDEN as canonical** after migration. May exist transiently as staging only if cleared into NAS before commit; migrate any existing blobs (count at audit time was 0).

## 4. Per-file metadata (required)
Preserve / store for every canonical nota file:
- `original_filename`
- `canonical_filename` (NAS-safe unique name; never silent overwrite)
- `file_hash` (sha256 — already `ggv_nota_files.sha256`)
- `size_bytes`, `content_type` / type
- `nota_id` (Wolf)
- `vendor_id` (nullable until linked)
- `upload_id` / upload identity
- `upload_timestamp` / `created_at`
- `source_provenance` / evidence provenance (upload actor, evidence_id if any, capture method)
- `backup_state` ∈ {`BACKED_UP`, `PENDING`, `UNKNOWN`, `FAILED`} — default `UNKNOWN` or `PENDING` until real B2 proof
- `nas_rel_path` (relative to MEDIA_LIBRARY) — replaces blob-only `rel_path` under local STORE_DIR
- `storage_root_id` = `01-Media-Library` (or equivalent constant)

## 5. Hierarchy + views
- Physical: `Finance/GGV/Notas/YYYY/MM/<canonical_filename>`
- Logical Wolf UI: **Year → Month → Nota** (filter/group). Grouping MUST NOT move/rename/mutate underlying individual evidence.
- Staff interface remains Wolf search/library — users do **not** browse raw filesystem paths.
- No automatic ZIP of individual historical notas for storage.
- Cold-storage/archive later OK only with transparent individual retrieve via Wolf.

## 6. MONTH EVIDENCE PACK (export product)
- Generated on demand (authorised): manifest/index JSON + referenced individual docs + audit/evidence state snapshot.
- May produce a **ZIP as download product**.
- ZIP is **NOT** canonical storage. Canonical remains individual NAS files + Wolf index.
- Do not auto-generate ZIPs into NAS as the storage form.

## 7. Retention
- **No automatic deletion** of finance evidence.
- Until legal/accounting retention policy locked: **PRESERVE ALL FINANCIAL EVIDENCE**.
- Migration must copy/move existing blobs with hash verify; never drop on failure (leave PENDING/FAILED + alert).

## 8. RBAC — GGV EXTERNAL ACCOUNTANT
Chain: Person → Role → Assignment → Scope → Permission → Audience.

### Seed (do not invent a real person)
- Role id suggestion: `ROLE-GGV-EXTERNAL-ACCOUNTANT` (or existing naming convention).
- Scope: **GGV Finance only** (`ENT-GGV` finance surfaces).
- Do **not** share Matt/Amanda credentials.

### Permissions (seed ALLOW for role; wire deny elsewhere)
**CAN SEE**
- notas/bills, vendor records, finance evidence, month/year history, approved exports.

**CAN ACT**
- review / comment / request correction
- download / export where authorised

**DENY (must stay denied unless separately granted)**
- `payment.execute` / payment approval execute path
- bank-detail verification/change (`vendor.bank.change`) unless separately granted
- Owner governance
- Wolf admin
- GGV CRM / content / internal intel unrelated to accounting
- other entities unless separately assigned

### Enforcement
Page, API, search, direct URL, export — **same scope**. Hidden URL must 403. Tests: accountant deny matrix.

## 9. Optional Accountant workspace
Route/nav: `GGV → Finance → Accountant` **only if** cheap reuse of existing tabs/components:
- current month
- missing evidence
- unreviewed items
- vendor issues
- monthly packs / export
**Forbidden:** fake accounting totals when books incomplete.

## 10. Backup state honesty
Enum on every canonical nota file row / API projection:
`BACKED_UP | PENDING | UNKNOWN | FAILED`

Rules:
- Never claim `BACKED_UP` without real B2 (or approved backup) proof.
- Until B2 wiring proven for finance paths: use `UNKNOWN` or `PENDING`.
- Surface honestly in UI (staff + accountant).

## 11. Migration (bounded)
1. Introduce NAS path resolver under `MEDIA_LIBRARY / "Finance" / "GGV" / "Notas" / YYYY / MM`.
2. On upload: stage → hash → place on NAS → index metadata in Wolf DB → set `backup_state=UNKNOWN|PENDING`.
3. Migrate any files under `state/ggv-finance-nota/blobs` (if present) with hash verify; update `ggv_nota_files` paths; do not delete source until verify OK.
4. Keep DB workflow fields; extend schema for new metadata columns as needed (additive migrations).
5. Extend or parallel a **finance write jail** under `Finance/` (do not force finance blobs through content `_Imports/Wolf-Library` if that confuses media library semantics — but still under same MEDIA_LIBRARY root).
6. Beta `:8788` only. Prod `:8787` untouched.

## 12. UI / API deltas (bounded)
- History: Year / Month / Nota filters (logical).
- File serve/preview/download: from NAS via Wolf, not local STORE_DIR.
- Export: MONTH EVIDENCE PACK endpoint (authorised).
- Optional Accountant tab if cheap.
- No payment UI. No Telegram retire. No fake totals.

## 13. Non-goals
- Broad Finance rebuild / full books / GL
- Zayen Finance implementation
- Payment execution / bank write
- Auto ZIP storage of historical notas
- Auto delete / retention purge
- Inventing a second NAS root
- Fake B2 `BACKED_UP`
- Inventing a real accountant person identity
- staff_ready / commissioned / telegram_retired claims
- Prod mutation
- New agents / Telegram sync
- Ping Matt FINISHED before ENGINEERING_PASS + Peaches verify on this arch pack

## 14. Zayen boundary
This pack remains bounded AP/evidence + Vendor Master ops. Payment and full books stay with later Finance reconciliation (Zayen). Do not create a competing ledger or ten empty finance pages.

## 15. Tests (minimum)
- Storage path resolves under NAS Finance/GGV/Notas/YYYY/MM (or honest BLOCKED when NAS unmounted — no silent local-canonical fallback after cutover)
- Metadata fields present on file records
- No blob-only-in-DB / no canonical STORE_DIR under `state/.../blobs`
- Accountant deny matrix (page/API/search/export)
- `backup_state` honesty (never auto BACKED_UP without proof)
- Year/Month views do not mutate evidence paths
- MONTH EVIDENCE PACK export ZIP is non-canonical (NAS individuals remain)
- Existing finance mobile nota regression suite still green (or extended)
- Prod :8787 pid sacred; soft head preserved

## 16. Exit criteria
- Docs + gate + CR addendum status consistent
- Implementation on Beta with tests FAIL=0
- Peaches independent verify
- Then — and only then — release Matt/Amanda commissioning HOLD
- Do **not** mark commissioned/staff_ready/telegram_retired from engineering

## Related
- RULE addendum: `docs/RULE-GGV-Finance-Mobile-Nota-2026-09-24.md`
- AUDIT: `docs/deliveries/AUDIT-GGV-Finance-Nota-Storage-Gap-2026-09-24.md`
- Gate: `state/build-factory/GATE-ggv-finance-nota-storage-accountant-20260924.json`
- Parent SPEC: `docs/deliveries/SPEC-GGV-Finance-Mobile-Nota-2026-09-24.md`
- NAS RULE: `docs/RULE-Wolf-Connection-Commissioning-NAS-GoLive-2026-09-22.md`
