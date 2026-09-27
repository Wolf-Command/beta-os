# GROK REVIEW — GGV Finance Mobile Nota — 2026-09-24

**Run:** `BF-ggv-finance-mobile-nota-20260924`  
**Workspace:** `/Users/wolfterminal/beta-os` · branch `build/wolf-command-rebuild`  
**Serves:** Owner directive 2026-09-24 recorded in `docs/RULE-GGV-Finance-Mobile-Nota-2026-09-24.md`  
**Tests:** `scripts/tests/test_ggv_finance_mobile_nota.py` → **PASS=138 FAIL=0** · `EXIT: SUCCESS`  
**CAP:** SPECIFIED · **staff_ready=false** · **proven=false** · **ready=false** · **commissioned=false** · **telegram_retired=false**  
**Beta:** `:8788` restarted via `scripts/beta_restart.py` · new pid **34323** (was 26792)  
**Production:** `:8787` pid **15975** still `wolf-system/dashboards/serve.py` · not mutated

## What staff can do

GGV → Finance (`/ggv/finance`) is the live Finance slot. The other GGV grammar slots stay empty. AMG and BZG Finance stay empty.

Four tabs: **Overview | Notas / Bills | Vendors | History**.

Upload accepts a camera photo, a photo or PDF, and extra photos. The screen walks **Uploading → Reading document → Checking vendor → Ready for review → ✓ Saved**. If reading fails, the upload stays saved and the person retries reading. They do not start a new upload.

Readings are proposals. A photo with no readable text does not get an invented amount. Bank text captured from a document is stored as **OBSERVED**, never verified. Save and Submit do not pay anyone.

Vendor search offers **Use existing** or **+ Create new** on the same nota. A possible duplicate vendor or nota stops for a human choice and writes an audit row. Nothing is merged or rejected silently.

Overview counts come from saved notas only: needs review, waiting approval, payment not verified, vendor issues, recently added. There is no cash, profit, or aged-payables figure.

## Zayen boundary

This pack is nota and vendor evidence inside Wolf. It is not a second ledger.

| Here | Later, with Zayen |
|------|--------------------|
| Capture notas, vendors, files, review state, audit | Reconciliation, cash, profit, aged payables, payment, bank verification |
| Wolf nota id, vendor id, file, creator, time, confirmed amount and date | Canonical books and money movement |

The overview says: "Payment and full books live with Finance reconciliation later — here you capture notas and vendors."

## Permissions

Access is email → AuthIdentity → Person → Role → Assignment → Scope → Permission. The page does not name people.

Operating codes, granted to `ROLE-MATT` and `ROLE-CONTENT-MGMT` only:

- `finance.nota.read` / `create` / `edit`
- `vendor.read` / `create` / `edit`
- `evidence.create`

`evidence.create` is the gate this desk checks before it keeps a file. The evidence spine still requires `evidence.record.submit` before it writes an evidence row. They are different codes. Both seats already had `evidence.record.submit`.

These codes exist and are **not** granted to those two roles by this pack: `payment.approve`, `payment.execute`, `vendor.bank.change`, `finance.policy.admin`.

Pay, execute, and bank-change routes return **405**. Setting a nota to paid or payment-verified returns **405**.

## Permission matrix (in the 138)

| Caller | Page and API |
|--------|----------------|
| Matt (`ROLE-MATT`, GGV scope) | Allowed |
| Amanda (`ROLE-CONTENT-MGMT`, GGV scope) | Allowed |
| Haikal, Misa, Devi | 403 |
| Anonymous (no session) | 403 |
| Client fixture in GGV scope without these codes | 403 |
| Hidden URL `/ggv-finance.html` and `/dashboards/ggv-finance.html` | Same rule as the page |
| Body `person_id` that does not match the session | 400 |

Live `:8788` without a Cloudflare Access JWT: `GET /ggv/finance` → **403** `missing_auth`. That is the existing fail-closed mode. This pack did not switch Beta to development assertion.

## Telegram

No Wolf↔Telegram sync. No new Telegram vendor or nota rows. Telegram is not marked retired. Both humans still have to commission before that gate can move.

## What was not verified in a browser

`:8788` is `cloudflare_access`. An unsigned browser session cannot sign in as Matt or Amanda. The phone path (camera, tabs, save, duplicate warning, history) was exercised by the automated test under development assertion, including a 200 page that contains the four tabs and the Wolf shell. A real phone walkthrough is still the Matt + Amanda commissioning cards, which are not written yet.

`scripts/tests/test_wolf_ggv_nav.py` accepts the new Finance link. Its three soft checks of older nav suites still fail on pre-existing items (`no mgmt-cluster primary`, `serve legacy uma-blu redirect`). Those failures are outside this pack.

## Owner questions

1. Open Wolf, Goss Group, GGV, then **Finance**. Direct address: `/ggv/finance`.
2. **Notas / Bills** → **+ Upload Nota**. Take a photo, or choose a photo or PDF, and add more photos if you need them.
3. The list under the button shows Uploading, Reading document, Checking vendor, Ready for review, and Saved.
4. The review screen shows what was read. Correct it, then **Save**.
5. If a vendor matches, tap **Use existing** or **+ Create new**. Creating one returns you to the same nota.
6. A possible match stops you. Use the existing vendor, or create a separate one and say why.
7. A possible duplicate nota stops you. Open the existing one, or save a separate copy and say why.
8. **Submit** after vendor, date, and amount are confirmed. Find it under **History** by vendor, date, amount, status, invoice number, or category.
9. The banner says entering a nota is not paying it. Submit says waiting approval, and that this is not a payment. Bank details on the document are not verified.
10. Unrelated staff, a signed-out person, and a client are denied on the page and on the API, including a typed address.

## Locks held

`proven=false` · `ready=false` · `staff_ready=false` · `commissioned=false` · `telegram_retired=false`  
No production write. No second finance ledger. No ten empty finance pages.
