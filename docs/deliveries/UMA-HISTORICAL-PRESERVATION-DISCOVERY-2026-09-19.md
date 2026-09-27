# UMA HISTORICAL PRESERVATION DISCOVERY — 2026-09-19 (WITA)

**Lane:** READ-ONLY discovery. **No import as canonical.** No ESB / ClickUp / Telegram / email writes. No destructive migration.

**Executor note:** This discovery was run on the box against a **read-only snapshot** at `/workspace/alchemist-live-ro.db` (mtime ~2026-09-17 19:18 WITA, 401408 bytes). Canonical live path on Wolfs-Mac-Studio remains:

`~/.openclaw/workspace/alchemist/data/alchemist.db`

Mac apply MUST re-verify counts/ranges against that live path before any future governed import. Snapshot ≠ live proof.

---

## 1. Sources found

| Source | Path | Notes |
|--------|------|-------|
| Alchemist SQLite (authoritative history until governed import) | `~/.openclaw/workspace/alchemist/data/alchemist.db` (live Mac) | PRESERVE IN PLACE |
| Box RO snapshot used for this doc | `/workspace/alchemist-live-ro.db` | Staging only; may lag live |

### Key tables (snapshot inventory)

| Table | Row count (snapshot) | Date range notes |
|-------|---------------------:|------------------|
| `petty_cash` | 258 | `entry_date` 2026-07-13 → 2026-08-27; `created_at` 2026-07-20T15:22:36+08:00 → 2026-08-18T07:20:55+08:00 |
| `pr_orders` | 200 | `order_date` 2026-07-27 → 2026-08-18; `created_at` 2026-07-27T15:31:19+08:00 → 2026-08-18T07:00:06+08:00; `approved_at` max 2026-08-17T20:31:10+08:00 |
| `pr_order_lines` | 674 | lines for PRs |
| `pr_receipt_lines` | 206 | receipt OCR/typed lines |
| `ledger` | 174 | `invoice_date` / `delivery_date` 2026-08-02 → 2026-08-17; `payment_date` 2026-08-04 → 2026-08-18 |
| `pr_vendors` | 31 | |
| `pr_vendor_items` | 495 | |
| `pr_leadtime` | 641 | |
| `suppliers` | 80 | |
| `staff` | 4 | includes Devi (tg admin) |
| `locations` | 1 | |
| `deliveries` / `delivery_lines` | 0 / 0 | empty in snapshot |
| `cash_count` | 0 | empty |
| `purchase_requests` | 2 | legacy |
| `esb_id_map` | 3 | mapping only |
| `par_levels` | 9 | |
| `variances` | 0 | |
| `item_prices` / `supplier_items` / `unit_map` | 0 | empty |

Full inventory (all tables in snapshot): cash_count 0, deliveries 0, delivery_lines 0, esb_id_map 3, item_prices 0, ledger 174, locations 1, par_levels 9, petty_cash 258, pr_leadtime 641, pr_lines 9, pr_order_lines 674, pr_orders 200, pr_receipt_lines 206, pr_staff 5, pr_vendor_dept 44, pr_vendor_items 495, pr_vendors 31, purchase_requests 2, sqlite_sequence 16, staff 4, supplier_items 0, suppliers 80, unit_map 0, variances 0.

---

## 2. What is PRESERVED IN PLACE

- **Alchemist DB remains authoritative** for Uma Blu historical petty cash, PRs, ledger, receipts until a **governed** import with provenance.
- Do **not** delete, rewrite, or “clean” Alchemist rows as part of Devi commissioning.
- Telegram / Drive photo links referenced from `petty_cash.photo_link` and receipt URLs stay where they are.

---

## 3. What is NOT imported into Wolf Beta Uma console (and why)

| Claim | Status | Why |
|-------|--------|-----|
| Alchemist history is complete / verified for commissioning | **CLAIMED ≠ VERIFIED** | Snapshot only on box; live Mac path not opened by this executor |
| Uma Today / Issues / History / Petty on Beta already mirror Alchemist | **NOT IMPORTED AS CANONICAL** | Beta Uma APIs are ops surfaces; history must not silently become Core truth |
| Cutover date known | **CUTOVER_AT = unset** | Cut line = **commissioning event time** — do not invent a date |

**Rule:** PRESERVE HISTORY ≠ DECLARE CANONICAL.

Any future import MUST be:

- append-only (or explicit versioned projection),
- with provenance (source path, row ids, import correlation id, importer person),
- fail-closed review before marking Core/canonical,
- **no** ESB / ClickUp / Telegram / email side writes as part of import.

---

## 4. Recommended cut line

```
CUTOVER_AT = unset
```

Cut line = **human commissioning event time** (when Matt unlocks CF + Devi successfully uses Uma Today on Beta under gate).  
Do **not** invent `2026-09-19` or Alchemist max(`created_at`) as cutover.

Until CUTOVER_AT is set by Peaches/Matt after human test:

- Pre-cutover history → Alchemist authoritative.
- Post-cutover ops → Beta Uma console (gated) for new work.
- Overlap / dual-write → OUT OF SCOPE for this discovery.

---

## 5. Explicit non-actions

- No ESB writes
- No ClickUp writes
- No Telegram writes
- No email writes
- No destructive migration
- No Production touch
- No marking HUMAN COMMISSIONED

---

## 6. Mac re-verify checklist (before any import design)

```bash
# on Wolfs-Mac-Studio
DB="$HOME/.openclaw/workspace/alchemist/data/alchemist.db"
sqlite3 "$DB" "SELECT COUNT(*) FROM petty_cash;"
sqlite3 "$DB" "SELECT MIN(entry_date), MAX(entry_date), MIN(created_at), MAX(created_at) FROM petty_cash;"
sqlite3 "$DB" "SELECT COUNT(*) FROM pr_orders;"
sqlite3 "$DB" "SELECT MIN(order_date), MAX(order_date), MIN(created_at), MAX(created_at) FROM pr_orders;"
sqlite3 "$DB" ".tables"
```

Paste live counts into an addendum if they differ from this snapshot.

---

## LIVE Mac re-verify (2026-09-19 ~08:14 WITA)

Canonical path opened: `~/.openclaw/workspace/alchemist/data/alchemist.db`

| Table | Live count | Date range |
|-------|----------:|------------|
| petty_cash | 386 | 2026-01-09 → 2026-09-19 |
| pr_orders | 424 | 2026-07-27 → 2026-09-15 |
| pr_receipt_lines | 452 | |
| pr_order_lines | 1521 | |
| ledger | 377 | |

Snapshot counts above remain staging-only. Live numbers supersede for inventory. Still: PRESERVE IN PLACE; CUTOVER_AT = unset; no canonical import.

