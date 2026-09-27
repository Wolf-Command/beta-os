# GROK REVIEW — GGV Finance Nota Storage + External Accountant — 2026-09-24

**Run:** `BF-ggv-finance-nota-storage-accountant-20260924`  
**Serves:** Owner lock 2026-09-24 ~12:51 WITA in `docs/RULE-GGV-Finance-Mobile-Nota-2026-09-24.md` (ADDENDUM)  
**Workspace:** `/Users/wolfterminal/beta-os` · branch `build/wolf-command-rebuild` · soft head `f3ab8f7` still in place  
**Parent:** `BF-ggv-finance-mobile-nota-20260924`  
**Tests:** `scripts/tests/test_ggv_finance_nota_storage_accountant.py` → **PASS=100 FAIL=0**  
**Parent regression:** `scripts/tests/test_ggv_finance_mobile_nota.py` → **PASS=138 FAIL=0**  
**Combined:** **PASS=238 FAIL=0**  
**CAP:** SPECIFIED · **staff_ready=false** · **proven=false** · **ready=false** · **commissioned=false** · **telegram_retired=false**  
**Beta:** `:8788` restarted via `scripts/beta_restart.py` · pid **44728** (was 35474)  
**Production:** `:8787` pid **15975** still `wolf-system/dashboards/serve.py` · `GET /` returned 200 · not mutated  
**Peaches verify:** PASS independent 2026-09-24 13:12 WITA — storage PASS=100 FAIL=0 + parent PASS=138 FAIL=0 · **Matt/Amanda CMQ HOLD released** → READY_TO_TEST

## What changed

Original nota files are no longer kept as the copy of record under `state/ggv-finance-nota/blobs`.

| Role | Where |
|------|--------|
| Wolf DB | Workflow, index, and file metadata in `catalog/content_library.sqlite` |
| Canonical file | `/Volumes/01-Media-Library/Finance/GGV/Notas/YYYY/MM/<canonical name>` |
| Key stored on the row | Relative to the media library, for example `Finance/GGV/Notas/2026/09/...` |
| Backup | `backup_state` is `PENDING` after a successful place. `B2_FINANCE_PROVEN` is false. `BACKED_UP` is refused |

The media library root is the existing `MEDIA_LIBRARY` in `scripts/core/nas_library.py`. There is no second root. The content upload jail under `_Imports/Wolf-Library` is unchanged. Finance writes only under `Finance/GGV/Notas`.

On this Mac at review time, `media_library_connected()` was true. `Finance/GGV/Notas` did not exist yet. The folder is created on the first real file, not as an empty show folder. Legacy blob count was 0. Migration of a fixture file copied, checked the hash, then removed the local source. A bad hash left the source in place and set `backup_state` to `FAILED`.

If the media library is not mounted, an upload stops with `nas_unmounted` and does not write a canonical file under `state/.../blobs`.

Each file row keeps original filename, canonical filename, sha256, size, content type, nota id, vendor id (once the nota is saved), upload id, upload time, provenance, `backup_state`, `nas_rel_path`, and `storage_root_id` `01-Media-Library`. API payloads use the relative key. They do not send `/Volumes/...`.

## Year, month, and the month pack

History can filter by year and month. The screen groups Year → Month → Nota. Changing a nota date does not rename or move the file. A file stored in `2026/09` stayed there after the nota date was changed to October.

**Download month evidence pack** builds a ZIP in memory: `manifest.json`, `evidence-state.json`, and copies of the individual files. The ZIP is the download. It is not written onto the NAS, and the manifest says it is not canonical storage. There is no accounting total in the pack.

## External accountant

`ROLE-GGV-EXTERNAL-ACCOUNTANT` is seeded with position `POS-GGV-EXT-ACCT` and scope `SCOPE-GGV-FINANCE` → entity `ENT-GGV`.

No person is assigned. The live catalog assignment count for that role is 0. Tests use a fixture person only inside a copied database.

Allowed on that role: `finance.nota.read`, `vendor.read`, `finance.nota.review`, `finance.evidence.export`.

Not granted: create/edit nota, create/edit vendor, `evidence.create`, `payment.approve`, `payment.execute`, `vendor.bank.change`, `finance.policy.admin`.

A person who holds only that role can open GGV Finance, search it, review/comment, and download a month pack. The same person is denied on content, GGV ops, BZG, a hidden content URL, another entity’s search, another entity’s export, upload, pay (405), and bank change (405). Matt is unchanged on finance and on content. Haikal is still denied.

The Finance page has a thin **Accountant** tab: this month, missing evidence, unreviewed, vendor issues, and the same month download. It states that there is no accounting total because the books are not complete here.

## Zayen boundary

This is still nota and vendor evidence. It does not pay, write bank details, or keep a second ledger.

## What was not verified in a browser

`:8788` is `cloudflare_access`. `GET /ggv/finance` without a Cloudflare JWT returned **403** `missing_auth`. A signed phone session was not opened. The authorised page, year/month grouping, export ZIP, and deny matrix were exercised by the automated test under development assertion, including a 200 finance page for the fixture accountant and a 200 finance page for Matt.

## Locks held

`proven=false` · `ready=false` · `staff_ready=false` · `commissioned=false` · `telegram_retired=false`  
`CMQ-GGV-FINANCE-NOTA-MATT` and `CMQ-GGV-FINANCE-NOTA-AMANDA` remain `BLOCKED_EXTERNAL` / `STORAGE_ARCH_PENDING`.  
No production write. No Telegram retire. No fake backed-up state. No real accountant identity.

## Peaches verify (2026-09-24 13:12 WITA)
Independent re-run by Peaches executor (Grok on Wolf Command):
- `scripts/tests/test_ggv_finance_nota_storage_accountant.py` → PASS=100 FAIL=0 EXIT:SUCCESS
- `scripts/tests/test_ggv_finance_mobile_nota.py` → PASS=138 FAIL=0 EXIT:SUCCESS
- Prod :8787 pid 15975 untouched · soft head f3ab8f7 preserved · staff_ready/commissioned/telegram_retired false
- CMQ HOLD released after verify; phone commissioning is the next human gate
- Executor did **not** message Matt
