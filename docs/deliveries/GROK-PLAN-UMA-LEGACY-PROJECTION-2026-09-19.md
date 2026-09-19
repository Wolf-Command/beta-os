# GROK PLAN — Uma legacy / current-state projection — 2026-09-19

## Goal

Beta `/bzg/uma-blu` must feel like an upgrade of Uma Blu operations that already exist in Alchemist — not Day 1 empty — without bulk-copying into canonical Wolf ops tables and without inventing float/closer/payment verification.

## Non-goals

- No Production mutation
- No Alchemist / ESB / ClickUp / Telegram / email writes
- No invent opening float from movement sums
- No truth-launder: Alchemist Paid ≠ Wolf verified payment
- No set `cutover_at` (prepare mechanism only)
- Preserve dirty WIP files listed in factory canon

## Design

```
Alchemist.db (PRESERVE IN PLACE, RO)
  → scripts/core/uma_alchemist_ro.py  (bounded adapter)
  → normalised projection dicts with provenance
  → merge in uma_ops_console list_* / today_cards / list_history
  → dashboards HTML (human labels; LEGACY vs WOLF soft chip)
```

Canonical post-cutover Wolf rows remain in `bzg_ops_*` / venue_close / issues.
Legacy rows are **never** inserted as non-example Wolf ops in this slice.

### Adapter (`uma_alchemist_ro.py`)

- Path: env `WOLF_ALCHEMIST_DB` or default `~/.openclaw/workspace/alchemist/data/alchemist.db`
- Fail soft if missing: empty list + `source_status=INACCESSIBLE` (do not crash Today)
- Read-only SQLite (`mode=ro` URI)
- Functions:
  - `project_prs(limit, attention_only=False) -> list[dict]`
  - `project_petty_movements(limit) -> list[dict]`
  - `project_history_events(limit) -> list[dict]`
  - `project_attention_summary() -> dict` (Awaiting Devi count, Received count, recent petty, unpaid ledger count/sum)
- Every row includes: `record_origin: "alchemist"`, `provenance: {source, table, source_id}`, `legacy: true`
- Map Alchemist PR status → display:
  - `Awaiting Devi` → waiting approval (attention)
  - `Received` → received / bill path (attention context)
  - `Paid` → "Recorded as paid in Alchemist" (not Wolf verified)
  - Cancelled/Rejected → closed-ish
- Petty: map flow/category/amount/date/logged_by; **never** set opening_float from aggregates
- History sentences human: `{date} · Purchase request recorded · Alchemist`

### Merge rules (`uma_ops_console.py`)

- `list_prs`: Wolf non-example first, then legacy projection (dedupe by provenance id if ever dual)
- `list_petty`: same; float_status stays NOT_FOUND unless a real Wolf day float exists
- `list_history`: merge Wolf audit + legacy chronology, sort by when desc
- `today_cards`:
  - Prefer live attention from Alchemist: Awaiting Devi, Received needing follow-up, recent unpaid ledger headline
  - Keep Daily Close Wolf state truthful
  - Keep opening-balance blocker; add why that history still shows underneath
  - Hide example fixtures when live legacy exists (`fixture_notice` false if live legacy present)

### Cutover prep (P6)

- `catalog` or `state/uma/cutover.json`: `{ "cutover_at": null, "sources": ["alchemist"] }`
- Helper `cutover_at()` returns None
- After cutover (future): new writes go Wolf-only; legacy adapter remains for pre-cut history
- **Do not set cutover_at in this slice**

### UI (bounded)

- Bills/Petty/Today/History: soft chip "Existing" for legacy; no raw Alchemist integer ids in primary UI (show `pr_num` like PR-1422)
- Petty empty copy replaced when movements exist
- History never "No history yet" when legacy events exist
- Keep prior Devi UX human language (no NOT_FOUND in staff copy)

### Tests

- Unit: adapter maps fixtures from a temp sqlite copy of schema+few rows
- Integration: when live DB readable in test env, count > 0 OR skip with mark
- Prove: `GET` Today/Bills/Petty/History payloads include legacy provenance; float still NOT_FOUND; no example leakage dominating
- Phone screenshots after deploy (Peaches P7)

### Success criteria

1. Today shows Awaiting Devi / real attention from Alchemist when present
2. Bills lists real PRs with Existing chip
3. Petty lists real movements; opening balance still needed
4. History has real chronology
5. cutover_at unset
6. SYSTEM score unchanged unless evidence bar met (do not chase %)

## Factory slice id

`BF-uma-legacy-projection-20260919`
