# Daily Close staff surface — 4 Oct 2026

**Status:** IMPLEMENTATION_DONE

## Files changed

- `dashboards/uma-blu-close.html` — staff flow, single submit, three-source compare, morning behaviour surfaced
- `scripts/core/bzg_daily_close.py` — `staff_close_surface`, plain audit/reopen copy on `enrich_close`; `three_close_objects` uses passed conn
- `scripts/serve_beta.py` — plain-language `staff_message` for wrong-date rejection
- `scripts/tests/test_close_surface_staff_rules_20261004.py` — temp in-memory sqlite staff-rule test (new)

## What staff now see

1. **Nine-step flow** on the close tab: open → shift report photo → confirm figures → Mandiri / BNI / BRI → cash → Wolf compares three sources → resolve differences → submit once → unmistakable result.
2. **Three sources kept separate** in copy and on screen: live ESB, printed shift receipt, physical till. Cash differences are not labelled as shortages.
3. **One submit control** — recount and manager-review paths reuse the same Submit button with plain-language prompts; no second submit or Reconcile control.
4. **Mandiri / BNI / BRI** from outlet config; empty config shows **needs setup**, not zero.
5. **Missing bank amounts stay blank** (—), never displayed as zero; typed entry still available when photo reading fails.
6. **Reopen** — plain notice that the original stands and new approval is required.
7. **Repeat submit** — plain message that the same figures do not create a second close; a different amount is refused.
8. **Wrong date** — photo/submit for another date refused in plain language; today's close unchanged.
9. **Audit history** — plain “what happened on this close” list (no raw event names or person-id strings).
10. **Earlier receipts** labelled as earlier attempts; unknown lines shown as needs classification.

## Test

```bash
python3 -m py_compile scripts/core/bzg_daily_close.py scripts/serve_beta.py scripts/tests/test_close_surface_staff_rules_20261004.py
python3 scripts/tests/test_close_surface_staff_rules_20261004.py
```

**Result:** 11 passed, 0 failed

## What was not changed

- No new tables, route families, or second close product
- FCR-GGV-41 not started
- Protected closes VDC-470e741f… and VDC-87202768… not read or written
- Live `catalog/content_library.sqlite` not copied, vacuumed, or written
- Beta not reloaded; pids 93525, 15975, 63443 untouched
- No commit, push, or process command lines in any file
