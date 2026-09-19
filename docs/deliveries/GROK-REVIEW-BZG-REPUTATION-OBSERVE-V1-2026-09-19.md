# GROK REVIEW — CAP-BZG-07 Reputation observe v1 — 2026-09-19

## Verdict
**PASS**

## Scope check
- Working tree for this slice: `scripts/core/bzg_reputation_observe.py` (new), `scripts/migrations/migrate_bzg_reputation_permissions.py` (new), `scripts/tests/test_bzg_reputation_observe.py` (new), `dashboards/bzg-reputation.html` (new), `scripts/serve_beta.py` (+BZG reputation routes/handlers only), plan, Cursor mission, this review, build-claim row.
- WIP four not in commit (`migrate_phase2_6_team_readiness.py`, `phase26_team.py`, `skills/__init__.py`, `wolf_intelligence.py`). Digests locked by tests. No Alchemist write. No Model C ledger / score / credits edit. `CAP-BZG-07` stays **SPECIFIED**. Ceiling is **BUILT**. No PROVEN/READY invented.
- Class NEW CAPABILITY (`beta-bzg-ops-safe`). `CR-d1aacda59180eba7` stays **OPEN** — observe skeleton landed; review-source ingest not claimed resolved.

## Prove
- `python3 scripts/tests/test_bzg_reputation_observe.py` → **PASS=112 FAIL=0** (re-run 2026-09-19 ~23:42 WITA)
- Live `:8788` anon `GET /api/bzg/reputation` → **403**; page path gated the same way in handler
- Production `:8787` listening True (pid 20807); Beta `:8788` listening True (pid 53359)
- Live Owner 200 not curled (no Cf-Access JWT in this shell); same handler proved under `BETA_AUTH_MODE=development_assertion` in tests
- Ledger `CAP-BZG-07` = SPECIFIED; 77 rows; CR OPEN; credits unchanged

## Red team
| Attack | Result |
| --- | --- |
| Invent PROVEN / raise CAP-BZG-07 | PASS — ledger not written; CAP stays SPECIFIED |
| Invent 5-star summary when no source | PASS — summary_rating null; five_star_invented false |
| Fake scrape / guest auto-reply | PASS — 405 scrape/reply refused; raises in core |
| Mutate via PUT | PASS — 405 append_only |
| Grant staff roles quietly | PASS — migration role_grants=0 |
| Production :8787 mutate | PASS — Beta routes only; prod pid unchanged |
| Resolve CR without product exit | PASS — CR stays OPEN; no mark_resolved |
| Touch WIP four | PASS — digests green; not staged for this commit |
| Anon open reputation | PASS — 403 fail-closed |
| Score / credits / ledger write | PASS — unchanged |

## Completion Register
Do not false-resolve `CR-d1aacda59180eba7`. Delivery evidence is the completion commit + this review. CAP-BZG-07 remains SPECIFIED (skeleton only). Re-seed factory mission evidence after lane COMPLETED.

## Out of scope (unchanged)
Production, CAP PROVEN promotions, invent review feed complete, Devi human retest (PARKED), Alchemist writes, finance/HR money paths, score gaming, Metricool/guest writes.

## Mission
Lane `bzg-reputation-observe-v1` → COMPLETED at completion commit (this review). Then close_slice → next eligible `ggv-social-derive-views`.
