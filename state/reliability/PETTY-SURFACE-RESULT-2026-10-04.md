# PETTY-SURFACE-2026-10-04 — Result

**Status:** `IMPLEMENTATION_DONE`  
**Date:** 2026-10-04  
**Scope:** Uma Blu petty cash staff page — one real OUT path. No HUMAN PASS claimed.

## Files changed

| File | Change |
|------|--------|
| `dashboards/bzg-uma-blu-petty.html` | OUT-only form; business date/time; payee; accounting mapping dropdown; read-only business + person; optional receipt with evidence-exception messaging; gated on `petty_record`; no In control |
| `scripts/core/uma_ops_console.py` | `list_petty_accounting_mappings()` from ENT-BZG entity books (+ prior movement codes); staff-safe `_public_petty_movement`; `list_petty` returns `accounting_mappings` + `business_label`; `record_petty_ops` validates mapping against stored codes; missing receipt allowed without fake photo/evidence id |
| `scripts/tests/test_petty_surface_20261004.py` | New — temp-sqlite schema bootstrap (no live catalog copy); page + recorder + close math checks |

## What staff now see

- **Petty cash out only** — no In button or top-up path on this page.
- **Business** shown as “Uma Blu / BZG”; **outlet** by name; **business date** and **time**; **amount**, **category**, **reason**, optional **payee**.
- **Person** is the signed-in assignment name (read-only); form hidden without `petty_cash.record_out`.
- **Accounting mapping** chosen from real expense accounts stored for BZG (labels are account names, not raw codes). If none exist, a banner says it cannot be saved yet.
- **Receipt** optional: with photo → attached; without → plain-language evidence exception (not a fake photo or invented evidence id).
- **Movements list** shows amount, reason, category, outlet, date, time, payee, person, receipt attached/missing — no movement ids, evidence ids, or accounting keys on screen.

## Tests run

```text
python3 -m py_compile scripts/core/uma_ops_console.py scripts/tests/test_petty_surface_20261004.py
→ exit 0

python3 scripts/tests/test_petty_surface_20261004.py
→ PASS=24 FAIL=0
```

Covers: page cannot post IN; missing/invalid accounting code refused; real code `5210` accepted; missing receipt → `EVIDENCE_EXCEPTION` / `INCOMPLETE` without fake receipt path; same-day OUT counted once in `cash_reconciliation_with_petty` expected closing cash.

## Deliberately not changed

- Petty cash **IN** recording (server still rejects IN; page no longer offers it)
- `record_petty_ops` audit path, `cash_reconciliation_with_petty` formula, or a second ledger/movement table
- Close `VDC-470e741f-d889-437a-9a40-1ec9c083fb95` (not read or written)
- Live `catalog/content_library.sqlite`, Beta/production process reload, commit/push
- `BETA_AUTH_MODE` on the page
- `scripts/tests/test_petty_cash_record_out_20261004.py` (still copies live catalog; not re-run this slice)
