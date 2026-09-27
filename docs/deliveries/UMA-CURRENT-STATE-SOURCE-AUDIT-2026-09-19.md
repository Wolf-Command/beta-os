# UMA CURRENT-STATE SOURCE AUDIT — 2026-09-19 (WITA)

**Lane:** READ-ONLY. No external writes. No bulk canonical import.
**Rule:** SOURCE FOUND ≠ AUTHORITATIVE ≠ CANONICAL.
**Live Mac verify:** 2026-09-19 ~11:40 WITA against `~/.openclaw/workspace/alchemist/data/alchemist.db` (mtime 2026-09-19 06:38 WITA).

## Live Alchemist reconfirm (AUTHORITATIVE for this audit)

| Table | Count | Date range |
|-------|------:|------------|
| `petty_cash` | **386** | entry_date 2026-01-09 → **2026-09-19** |
| `pr_orders` | **424** | order_date 2026-07-27 → 2026-09-15 |
| `pr_order_lines` | 1521 | |
| `ledger` | 377 | invoice_date 2026-08-02 → 2026-09-15 |
| `pr_receipt_lines` | 452 | |
| `cash_count` | **0** | (no opening float in Alchemist either) |

### PR status mix (live)

| Status | Count |
|--------|------:|
| Paid | 304 |
| Received | 73 |
| Awaiting Devi | **25** |
| Cancelled | 21 |
| Rejected | 1 |

### Ledger unpaid (live)

10 rows · ≈ Rp 7,276,000 (payment_status=unpaid, hold=0)

### Petty flow (live)

| Flow | Count | Sum Rp |
|------|------:|-------:|
| Cash Out (Spend) | 321 | 26,553,780 |
| Cash In (Top-up) | 64 | 25,359,780 |
| Reset / Adjustment | 1 | 1,671,000 |

Recent: 2026-09-19 top-up Rp 300k from Matt; 2026-09-18 staff meal / top-up.

**Correction:** Earlier box-executor claim that "petty≈386 is a mislabel" is **FALSE**. Live petty_cash is **386**. Box RO snapshot (258/200) was stale.

## Source classifications (summary)

| SOURCE | AUTHORITY | FRESHNESS | PROJECT? | IMPORT CANON? |
|--------|-----------|-----------|----------|---------------|
| Alchemist live SQLite | Authoritative Uma purchasing+tin until cutover | Live (petty today) | **YES read projection** | No (governed later) |
| Box `alchemist-live-ro.db` | Not authoritative | Stale | Dev only | No |
| Beta `bzg_ops_*` | New Wolf ops | Empty live (0 petty mov) | Target UI | N/A |
| Prod `:8787` `/api/alchemist*` | Proven RO adapter pattern | Live | Copy pattern into Beta | No |
| ESB | POS till/stock | Unread full | Later RO sales only | No writes |
| `cash_count` | Empty | N/A | Do **not** invent float | No |
| ClickUp Uma tasks | Ops tasks only | Optional Issues | Soft | Not money SSOT |

## Conflicts

- Beta Uma Today empty vs Alchemist full → Owner Release pain (this mission).
- Sum of petty in/out ≠ verified opening balance → keep **Opening cash balance needed**.
- Paid in Alchemist ≠ Wolf verified payment → display "Recorded as paid in Alchemist".

## CUTOVER_AT

`unset` — set only after Devi human commissioning + Matt accept.

## Recommended projection (P1)

See `docs/deliveries/GROK-PLAN-UMA-LEGACY-PROJECTION-2026-09-19.md`.
