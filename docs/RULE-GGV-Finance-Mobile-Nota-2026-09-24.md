# RULE — GGV Finance Mobile Nota + Vendor Workflow (2026-09-24)

**Owner lock:** Matthew Goss · **Commissioned directive:** 2026-09-24 Owner P0 · **Governor:** Peaches · **Executor:** Grok on Wolf Command  
**Surface:** Beta GGV Finance inside Wolf (`:8788`) · **Production :8787 sacred — do not mutate**  
**Run:** `BF-ggv-finance-mobile-nota-20260924`

## Intent
Matt + Amanda operate GGV notas / bills on phone (and desktop) inside Wolf:

**UPLOAD NOTA → read → identify/search vendor → use existing OR create → confirm → attach evidence → submit → status/history**

Once **both** commission Wolf: Telegram nota is **retired**. Until then Telegram stays operating historically — Wolf must still work **without** Telegram. No parallel TG. No copy TG↔Wolf.

## Nav (simple staff)
**OVERVIEW | NOTAS / BILLS | VENDORS | HISTORY**

Do **not** create ten empty finance pages. Zayen full Finance reserved for later reconciliation. This is bounded AP/evidence that must later plug into Zayen's canonical Finance model.

## Permissions (no hard-coded names)
Authorised via EMAIL → AuthIdentity → Person → Role → Assignment → Scope → Permission.

Operating:
- `finance.nota.read` / `create` / `edit`
- `vendor.read` / `create` / `edit`
- `evidence.create`

Separate from (do not grant via this pack's operating path):
- `payment.approve` / `payment.execute` / `vendor.bank.change` / `finance.policy.admin`

## Non-negotiables
- Mobile first; desktop too; minimum clicks; human language; no eng jargon
- Extraction = proposals unless deterministic; never invent amounts; low confidence visible
- One Vendor Master; duplicate vendor + duplicate nota warnings with user decision + audit
- BANK DETAILS OBSERVED ≠ VERIFIED; no money movement
- NOTA ENTERED ≠ APPROVED ≠ PAID ≠ PAYMENT VERIFIED
- Do not mark `staff_ready` / commissioned / Telegram RETIRED from engineering alone
- Soft head `f3ab8f7` — do not destroy uncommitted work
- Credit Conservation Owner exception: **this one pack only** — pack_veto still blocks other breadth

## Related
- Gate: `state/build-factory/GATE-ggv-finance-mobile-nota-20260924.json`
- SPEC: `docs/deliveries/SPEC-GGV-Finance-Mobile-Nota-2026-09-24.md`
- Audit: `docs/deliveries/AUDIT-GGV-Finance-Mobile-Nota-Reuse-2026-09-24.md`
- Commissioning: `state/commissioning/GGV-FINANCE-NOTA-MOBILE-2026-09-24.md`
- CR: `state/completion-register/ggv-finance-mobile-nota-20260924.json`

---

## ADDENDUM — Storage architecture + EXTERNAL ACCOUNTANT (Owner lock 2026-09-24 ~12:51 WITA)

**Status:** LOCKED by Owner before Matt/Amanda phone commissioning.  
**Governor:** Peaches · **Executor:** Grok on Wolf Command  
**Correction class:** Architecture correction to existing Finance pack only — NOT a broad finance rebuild.  
**Credit conservation:** ON — this Owner-named architectural correction is an allowed conservation exception (same spirit as BF-ggv-finance-mobile-nota-20260924). Unrelated breadth remains `PEACHES_VETO_CREDIT_CONSERVATION`.  
**Zayen Finance:** stays reserved. Do not invent a competing ledger.

### Canon (exact)

1. **Wolf DB** = finance workflow / index / metadata ONLY.
2. **Original nota evidence** = canonical **NAS** document storage.
3. **B2** = backup / DR.
4. Do **NOT** store source document blobs only inside the application database / local app state.
5. **Hierarchy:** `Finance/{ENTITY}/Notas/{YYYY}/{MM}/` — initially `Finance/GGV/Notas/YYYY/MM` under the existing NAS media library root (`/Volumes/01-Media-Library`). Do not invent a second NAS root.
6. **Preserve on each file:** original filename, canonical filename, file hash, size/type, Wolf nota ID, vendor ID, upload identity, upload timestamp, source/evidence provenance, backup state.
7. **Normal users do NOT browse filesystem paths** — Wolf search/library is the interface.
8. **NO automatic ZIP** of individual historical notas. PDF/JPG/PNG stay individually searchable / previewable / retrievable.
9. Future cold-storage / archive tiering OK **only if** Wolf can transparently retrieve individual evidence.
10. Logical **Year → Month → Nota** views; grouping must **NOT** mutate underlying individual evidence.
11. **MONTH EVIDENCE PACK** = generated export (manifest/index + referenced docs + audit/evidence state). Export ZIP allowed as product. Export ZIP is **NOT** canonical storage.
12. **RETENTION:** no automatic deletion of finance evidence. Until legal/accounting retention locked: **PRESERVE ALL FINANCIAL EVIDENCE**.
13. **EXTERNAL ACCOUNTANT** role: `GGV EXTERNAL ACCOUNTANT` via Person → Role → Assignment → Scope → Permission → Audience. Do **not** share Matt/Amanda credentials. Scope to **GGV Finance only**.
    - **CAN SEE:** notas/bills, vendor records, finance evidence, month/year history, approved exports.
    - **CAN ACT:** review / comment / request correction; download / export where authorised.
    - **DENY:** payment execution; bank-detail verification/change unless separately granted; Owner governance; Wolf admin; GGV CRM/content/internal intel unrelated to accounting; other entities unless separately assigned.
    - Direct URL / API / search must enforce the same scope.
14. **Accountant workspace** `GGV → Finance → Accountant` ONLY if low-cost / shared components allow: current month, missing evidence, unreviewed items, vendor issues, monthly packs, export. No fake accounting totals where books incomplete.
15. **Backup state** on every canonical nota file: `BACKED UP | PENDING | UNKNOWN | FAILED`. Never fake B2 protection.
16. Credit conservation. Architecture correction to existing Finance pack only.

### Known gap (confirmed)
`scripts/core/ggv_finance_nota.py` currently uses:
`STORE_DIR = BETA_ROOT / "state" / "ggv-finance-nota" / "blobs"`
— local Mac app state, **not** NAS. Must be corrected before human commissioning.

### Commissioning HOLD
Human commissioning cards `CMQ-GGV-FINANCE-NOTA-MATT` and `CMQ-GGV-FINANCE-NOTA-AMANDA` are **HOLD** until this storage architecture pack reaches `ENGINEERING_PASS` and Peaches verifies. Do **not** invent READY / staff_ready / commissioned / telegram_retired.

### Related (addendum)
- SPEC: `docs/deliveries/SPEC-ADDENDUM-GGV-Finance-Nota-Storage-Accountant-2026-09-24.md`
- AUDIT: `docs/deliveries/AUDIT-GGV-Finance-Nota-Storage-Gap-2026-09-24.md`
- Gate: `state/build-factory/GATE-ggv-finance-nota-storage-accountant-20260924.json`
- Run: `BF-ggv-finance-nota-storage-accountant-20260924`
