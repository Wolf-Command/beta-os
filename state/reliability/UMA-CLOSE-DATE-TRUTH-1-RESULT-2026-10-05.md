# UMA-CLOSE-DATE-TRUTH-1 result

2026-10-05 · Beta only · staff_ready **false** · human_commissioned **false**

## Verdict

29 Sep figures **CORRECT** — query not changed (`query_corrected: false`). Proof: [UMA-29SEP-ESB-PROOF-2026-10-05.md](./UMA-29SEP-ESB-PROOF-2026-10-05.md).

## UX repair

Phone-first close flow in `dashboards/uma-blu-close.html`:

1. **Date** — large masthead date; **HISTORICAL CLOSE** when not today  
2. **ESB sales** — staff-facing totals; “Sales loaded for …”  
3. **Shift report** — Take / Upload photo  
4. **Card terminals** — Mandiri, BNI, BRI; EDC and QRIS separate  
5. **Cash** — expected, counted, difference  
6. **Review** — sales vs shift report vs cash  
7. **Submit** — one result line  

Owner / supervisor actions moved behind collapsed **Manage close** (not mid-flow). Engineering strings removed from the main path (`payment lines, not settlement`, force re-capture audited messages, person id prompts, live vs dated snapshot copy).

Small server copy fix: `scripts/core/bzg_daily_close.py` staff submit messages use “sales / shift report / cash counted” instead of “live ESB”.

## Tests

| Test | Pass | Fail |
|------|-----:|-----:|
| `scripts/tests/test_uma_close_date_truth_1_20261005.py` | 32 | 0 |
| `scripts/tests/test_close_surface_staff_rules_20261004.py` | 11 | 0 |

Fixture ESB temp DB only — distinct cash + finished per date 28 Sep–4 Oct; 2 Oct and 4 Oct both 61 finished but different cash.

## Protected closes (re-read catalog mode=ro — unchanged)

| Close | State | Key fields |
|-------|-------|------------|
| VDC-470e741f… | EXCEPTION | declared 3225000 · variance −125000 · updated 2026-10-03T13:47:39Z |
| VDC-87202768… | CANCELLED | updated 2026-10-03T12:32:22Z |
| VDC-64f5f529… | DATA_CAPTURED | declared NULL · updated 2026-10-04T13:56:05Z |

## Listeners

- Beta `:8788` reloaded (Python change) — pid **17208** (was 11882)  
- Production `:8787` untouched — pid **1297**

Full JSON: [UMA-CLOSE-DATE-TRUTH-1-RESULT-2026-10-05.json](./UMA-CLOSE-DATE-TRUTH-1-RESULT-2026-10-05.json)
