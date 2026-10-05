# FINANCE CONTROL REPAIR — CHECKPOINT 2026-10-03

**Pack:** `state/reliability/FINANCE-CONTROL-REPAIR-2026-10-03.md`  
**Decision:** 2026-09-17 Uma Blu Daily Close (extend) + Owner Finance Control Repair brief 2026-10-03  
**Branch:** `build/wolf-command-rebuild` · Beta only · Prod `:8787` untouched (pid 15975)  
**Stamps:** `staff_ready=false` · `eng_proved=false` · **not** ENG_PROVED · **not** READY FOR MATT TEST

## Last proved checkpoint (do not restart)

| Item | Status | Evidence |
| --- | --- | --- |
| EDC bank cards (MANDIRI/BNI/BRI) | CODE_COMPLETE_AWAITING_PEACHES_VISUAL | `PEACHES-VERIFY-EDC-BANK-CARDS-1.json` |
| Vision capability / model_router | CODE COMPLETE / LIVE PATH PROVED awaiting Peaches | `BZG-CLOSE-VISION-CAPABILITY-1-RESULT.md` · STATUS tip 0b0e50d |
| Preserved close | **INTACT** | `VDC-87202768-55af-4c8e-abc3-382a5496b8c6` · biz date 2026-10-02 · outlet BZG-UMA · state DATA_CAPTURED · holder PERS-MATT |
| Receipt photos | **INTACT** | `EVD-CLOSE-ESB-*` (3) + `EVD-CLOSE-EDC-*` (2) under `state/bzg-daily-close/receipts/` |
| Bank cards live | Mandiri RECEIPT_REQUIRED · BNI MATCH (1 SUPERSEDED) · BRI NOT_USED_TODAY | Beta `/api/venue-close/…/bank-cards` |

## This run (continued — not a wipe)

### WHAT CHANGED
- `scripts/core/venue_close.py`: `list_closes` date_from/date_to/outlet_id filters; `closing_history()` consolidated totals from **saved** rows only (`live_esb_used=false`); `cancel_unfinished_close()` for unfinished drafts (OPEN / DATA_CAPTURED / EVIDENCE_SUBMITTED) with evidence retained.
- `scripts/serve_beta.py`: list query params + `history=1`; POST `/api/venue-close/cancel-unfinished`.
- `dashboards/uma-blu-close.html`: Closing History filters + range totals; Cancel Closing on unfinished draft.
- Tests: `scripts/tests/test_finance_control_history_cancel_20261003.py` (manual runner PASS; pytest module not installed in default python).

### WHAT WAS REUSED
- Existing venue_daily_closes / EDC bank cards / owner control / vision packs.
- No second GGV receipt pipeline built.

### WHAT WAS FIXED
- History could not filter by day range / outlet / status; now can (saved data only).
- Staff cancel unfinished was Owner-only; holder cancel unfinished path added (does not rewrite VERIFIED_CLOSED).

### WHAT WAS TESTED
- Preserved close + photos still present after changes.
- History filters return VDC-87202768 for 2026-10-02 / BZG-UMA.
- Throwaway OPEN close cancel → CANCELLED; VDC state unchanged DATA_CAPTURED.
- Beta `:8788` restarted via LaunchAgent; Prod `:8787` pid unchanged.

### TEST RESULTS
- Manual prove: PASS (preserved / filters / history / throwaway cancel).
- Peaches visual verify for EDC bank cards: **still required** (not done this run).
- External integration ENG_PROVED bar: **not claimed**.

### REMAINING LIMITATIONS
- Mandiri still RECEIPT_REQUIRED on preserved close (needs human terminal photo — not invented).
- GGV Accounting / Peaches `receipt ggv` reuse / bank statement import: **not started** this slice.
- Snapshot freeze vs live ESB mutating open draft: existing fingerprint_stale path; full three-state product polish still open.
- History detail still thinner than amendment L (bank-by-bank on history card — use Today detail / bank-cards for now).
- Cancel Closing is enabled for DATA_CAPTURED unfinished states — **do not cancel** VDC-87202768; Peaches/Matt continue that close.

### EXACT URLS (Beta)
- Daily Close UI: `http://127.0.0.1:8788/uma-blu-close`
- History API: `GET /api/venue-close/list?history=1&date_from=&date_to=&outlet_id=&state=`
- Cancel unfinished: `POST /api/venue-close/cancel-unfinished`
- Bank cards: `GET /api/venue-close/VDC-87202768-55af-4c8e-abc3-382a5496b8c6/bank-cards`

### Classification
**CODE COMPLETE / INTEGRATION UNPROVED** for this history+cancel slice (unit/local prove only; Peaches independent verify not run).  
EDC + Vision prior stamps unchanged — still awaiting Peaches; not Matt-ready.

---

## This run (continued — three-object + history detail + GGV intake RO)

**Tip still dirty on purpose** (last noted 0b0e50d). Do not declare PASS from git status.  
**Stamps:** `staff_ready=false` · `eng_proved=false` · **not** READY FOR MATT TEST · **not** ENG_PROVED

### WHAT CHANGED
- `scripts/core/venue_close.py`: `three_close_objects()`; freeze dated snapshot on re-capture (`mutated=false` — live side-read only); Owner `force_recapture`+reason gated; `closing_history` enriched with three-object labels + range totals exclude CANCELLED/OPEN and note SUPERSEDED EDC excluded.
- `scripts/core/bzg_daily_close.py`: `history_detail()` — source snapshot, API vs receipt (both retained; cause not invented), bank cards, cash/EDC/QRIS CURRENT, non-sales, superseded audit, evidence.
- `scripts/serve_beta.py` + `uma_devi_p0.close_detail` + `dashboards/uma-blu-close.html`: history card paints detail; capture returns freeze flags.
- Part B increment (reuse, not second pipeline): `scripts/core/ggv_receipt_intake_ro.py` + `GET /api/ggv/finance/receipts` — lists existing identity-vault inbox/processed/archive; Peaches caption parser `receipt ggv`; bridge helper calls existing `receipt-from-telegram.py`.
- Prove: `state/reliability/prove_finance_control_three_object_20261003.py` + test file `scripts/tests/test_finance_control_three_object_history_20261003.py`.

### WHAT WAS REUSED
- Prior history+cancel slice; EDC bank cards; dual_source board; wolf-system `receipt-from-telegram.py` / `receipt-ingest.py` / `identity-vault/receipts-*`.
- No second GGV receipt pipeline. No Xero revive.

### WHAT WAS FIXED
- Open/dated snapshot could be overwritten by `/api/venue-close/capture` re-pull — now frozen after first fingerprint.
- History detail was thin — now shows snapshot + API vs receipt + banks + non-sales + superseded counts.
- GGV Accounting Receipts had no Beta RO surface over the existing vault — now lists via finance API.

### WHAT WAS TESTED
- Local prove PASS: preserved intact; freeze no overwrite (API cash stays 2,855,000 vs receipt 2,735,000); history_detail; range totals; throwaway cancel; VDC still DATA_CAPTURED / PERS-MATT.
- Mandiri still RECEIPT_REQUIRED (no invented photo). BNI MATCH. BRI NOT_USED_TODAY.
- GGV intake RO: 496 processed GGV receipts listed; bridge+ingest scripts present; `second_pipeline=false`.
- Beta `:8788` restarted via `net.wolfcommand.serve-beta`. Prod `:8787` pid **15975** still listening.

### TEST RESULTS
- `prove_finance_control_three_object_20261003.py`: PASS (all steps).
- `ggv_receipt_intake_ro` local: PASS (caption parse + list).
- Peaches visual EDC: **still required**.
- External ENG_PROVED: **not claimed**.

### REMAINING LIMITATIONS
- Mandiri RECEIPT_REQUIRED on preserved close (needs real terminal photo).
- EDC bank cards: still `CODE_COMPLETE_AWAITING_PEACHES_VISUAL`.
- GGV Part B left: Peaches live chat hook → `file_via_existing_bridge`; Accounting UI queues (Needs coding / review / unmatched…); human confirm vs extraction retention UI; bank statement import; Xero-replacement ledger (ingest still fail-closed).
- Force-recapture Owner path not UI-wired (API only).
- Tree remains dirty; do not treat Cursor exit as PASS.

### EXACT URLS (Beta)
- Daily Close UI: `http://127.0.0.1:8788/uma-blu-close`
- History API: `GET /api/venue-close/list?history=1&…`
- Close + history detail: `GET /api/venue-close/VDC-87202768-55af-4c8e-abc3-382a5496b8c6`
- Capture (freeze-safe): `POST /api/venue-close/capture`
- GGV receipts (vault RO): `GET /api/ggv/finance/receipts`
- Bank cards: `GET /api/venue-close/VDC-87202768-55af-4c8e-abc3-382a5496b8c6/bank-cards`

### Classification
**CODE COMPLETE / INTEGRATION UNPROVED** for three-object freeze + history detail + GGV intake RO increment.  
Prior history+cancel and EDC/Vision stamps unchanged — not Matt-ready.


## Continuation armed

- 2026-10-03 13:48 WITA: one Beta cursor-agent print session started, pid 55387, from the proved history/cancel slice. Private worker pid 63443 left untouched. Prod pid 15975 not restarted. Next instructed slice: three-object close immutability, then history detail. Preserved close VDC-87202768 not cancelled. Not PASS.

- 2026-10-03 16:41 WITA: continuation 2 started, pid 74191. Previous slice left CODE COMPLETE / INTEGRATION UNPROVED. Not a duplicate. Prod 15975 not restarted. P2P still queued.

---

## This run (continued — restart/reopen/missing close/GGV bank + HTTP)

**Tip still dirty on purpose.**  
**Stamps:** `staff_ready=false` · `eng_proved=false` · **not** READY FOR MATT TEST · **not** ENG_PROVED  
**Decision served:** 2026-09-17 Uma Blu Daily Close (extend) + Finance Control Repair 2026-10-03 Part A/B + 2026-08-02 bank FILE_IMPORT_ONLY truth.

### WHAT CHANGED
- `scripts/core/venue_close.py`:
  - Partial unique index `ux_venue_daily_closes_current` (table rebuild) so CANCELLED history can coexist; `get_close(business_date=…)` skips CANCELLED; `open_or_get` creates a clean restart after cancel (`restarted_after_cancel`).
  - `venue_close_final_history` freeze on Owner reopen of VERIFIED_CLOSED (original immutable); `three_close_objects` surfaces freeze.
  - Guard: cannot revive CANCELLED if a current close already exists for that date.
- `dashboards/uma-blu-close.html`: Owner **Force re-capture ESB** control (audited `force_recapture` + reason).
- `dashboards/ggv-finance.html`: **Receipts** tab (vault via `/api/ggv/finance/receipts`) + **Banking** tab (import + missing-evidence txns).
- `scripts/core/ggv_bank_statement1.py`: FILE_IMPORT_ONLY — keep original under `state/ggv-bank-statements/originals/`, write normalised `ggv_bank_transactions`, propose-only match, never auto-reconcile; ENT-GGV scoped.
- `scripts/core/ggv_finance_nota.py`: GET/POST bank-statements routes.
- Prove: `state/reliability/prove_finance_control_continuation_20261003.py`.

### WHAT WAS REUSED
- Prior freeze / history detail / cancel unfinished / EDC bank cards / GGV vault RO list + receipt-from-telegram bridge.
- Mandiri/BRI CSV shapes from wolf-system `bzg_bank_ingest` (minimal parsers copied — no second receipt pipeline, no Xero).
- Existing Owner Control / takeover / reassign APIs and Uma close UI panels.

### WHAT WAS FIXED
- Restart after cancel was blocked by table-level UNIQUE — now works; cancelled row stays in history.
- Reopen of VERIFIED_CLOSED mutated the only copy — now freezes final history first.
- GGV Accounting had vault API but no Receipts/Banking UI — wired.
- Bank statement import was stub-only — real originals + normalised rows + missing-evidence visibility for GGV.

### WHAT WAS TESTED (Beta catalog + running :8788)
Local prove PASS (same DB as Beta):
`preserved_intact restart_schema history_range history_detail_dual_source add_missing_historical_esb:VDC-4046a805-8c76-4439-8019-f879f3b49513 cancel_restart single_holder_lock takeover_reassign reopen_immutable bank_cards_not_used ggv_vault_receipts bank_statement_import zayen_ggv_deny freeze_still_holds`

HTTP against running Beta (temporary `BETA_AUTH_MODE=development_assertion`, then restored to `cloudflare_access`):
- History 200 · live_esb_used=false · preserved DATA_CAPTURED / PERS-MATT
- Missing close `VDC-4046a805-…` business_date 2026-09-28 · ESB cash **2460000.0** (that date, not today)
- GGV receipts `second_pipeline=false` · bank-statements entity ENT-GGV · Zayen 403
- Pages `/uma-blu-close`, `/ggv/finance`, `/ggv/finance/receipts` 200

### TEST RESULTS
- `prove_finance_control_continuation_20261003.py`: **PASS**
- HTTP prove window: **PASS** then auth restored to CF fail-closed
- Prod `:8787` pid **15975** unchanged throughout
- Preserved close unchanged: DATA_CAPTURED / PERS-MATT / API cash 2,855,000 vs receipt 2,735,000 retained
- Mandiri on preserved still RECEIPT_REQUIRED (no invented photo)
- Peaches visual EDC: **still required**
- `eng_proved=false` (CF-mode staff session / Peaches independent verify not done)

### REMAINING LIMITATIONS
- Peaches live chat → bridge hook still not wired in the Peaches process (bridge helper exists).
- Human confirm vs AI extraction retention UI on GGV receipts still thin.
- Full accountant queue taxonomy (Needs coding / unmatched / duplicates) partial.
- EDC bank cards still awaiting Peaches visual.
- Vision ENG_PROVED bar unchanged (prior pack).
- Do not cancel/reopen/force-recapture preserved VDC-87202768.

### EXACT URLS (Beta)
- Daily Close: `http://127.0.0.1:8788/uma-blu-close`
- History: `GET /api/venue-close/list?history=1&date_from=&date_to=&outlet_id=`
- Missing historical (proved): `VDC-4046a805-8c76-4439-8019-f879f3b49513` · 2026-09-28
- GGV Receipts UI: `http://127.0.0.1:8788/ggv/finance/receipts`
- GGV vault API: `GET /api/ggv/finance/receipts`
- GGV bank: `GET /api/ggv/finance/bank-statements` · `POST /api/ggv/finance/bank-statements/import`
- Owner force recapture: `POST /api/venue-close/capture` `{force_recapture:true, force_reason}`

### Classification
**CODE COMPLETE / INTEGRATION PARTIAL** — behaviours proved on running Beta DB + HTTP under a temporary development_assertion window; production CF path restored. Not Matt-ready. P2P not started.

### Continuation note
- 2026-10-03 ~16:50 WITA: continuation 2 finished this slice. Beta pid rotated (LaunchAgent restart for code+auth). Prod 15975 sacred. Tree dirty. staff_ready=false eng_proved=false.

---

## This run (continued — GGV accounting queues)

**Resumed from:** `state/reliability/FINANCE-CHECKPOINT-FREEZE-2026-10-03.json` (continuation-3 died before edits).  
**Stamps:** `staff_ready=false` · `eng_proved=false` · **not** READY FOR MATT TEST · **not** ENG_PROVED  
**Decision served:** 2026-09-17 Uma Blu Daily Close (extend) + Finance Control Repair 2026-10-03 Part B (GGV accounting surface only).

### WHAT CHANGED
- `scripts/core/ggv_receipt_accounting1.py` (new): persisted `ggv_receipt_accounting` rows synced from vault; queues **needs_coding / needs_review / unmatched / duplicate**; human confirm keeps `extraction_json` beside `human_confirmed_json`; receipt image route; audited confirm.
- `scripts/core/ggv_receipt_intake_ro.py`: `_is_ggv_receipt()` entity isolation — meta tenant authoritative; `_bzg_receipt_` / `_amg_receipt_` excluded (was leaking 12 rows).
- `scripts/core/ggv_finance_nota.py`: `GET /api/ggv/finance/accounting/queues`, receipt detail/image/confirm routes.
- `dashboards/ggv-finance.html`: Receipts tab → accounting queue filters, counts, detail panel with image + extraction + confirm-beside-extraction; bank unmatched + missing evidence visible.

### WHAT WAS REUSED
- Prior vault list, bank statement import, nota accountant desk, receipt-from-telegram bridge — no second pipeline, no P2P, no Xero.

### WHAT WAS FIXED
- AMG/BZG receipts could appear in GGV list when filename/meta disagreed — now 0 leak (`484` GGV rows synced; `amg_bzg_leak_count=0`).
- Receipts UI showed vault folder names only — now human accounting queues with persisted state.
- Human confirm path did not exist — confirm retains extraction; missing evidence and bank-unmatched stay visible.

### WHAT WAS TESTED
- Local prove against Beta catalog DB (same DB as `:8788`): preserved close, entity isolation, persisted queue rows, image evidence, confirm beside extraction, duplicate detection (`10`), Zayen deny, freeze hold.
- HTTP prove on running `:8788` (temporary `development_assertion`, then restored `cloudflare_access`): accounting queues API, Zayen 403, `/ggv/finance/receipts` page 200.
- Prod `:8787` pid **15975** unchanged. Preserved `VDC-87202768` still `DATA_CAPTURED` / `PERS-MATT`. Mandiri not invented.

### TEST RESULTS
- `prove_finance_control_ggv_accounting_20261003.py`: **PASS**  
  `preserved_intact amg_bzg_vault_isolated accounting_queues_persisted extraction_visible image_evidence_attached human_confirm_keeps_extraction duplicate_queue:10 zayen_ggv_deny freeze_still_holds http_accounting_queues http_zayen_deny http_receipts_page`
- Persisted queue counts: needs_review **474** · duplicate **10** · needs_coding **0** · unmatched **0** · bank_unmatched_txns **6** · missing_evidence_receipts **0**
- `staff_ready=false` · `eng_proved=false`

### REMAINING LIMITATIONS
- Peaches live chat → bridge hook still not wired in Peaches process.
- Most vault receipts lack structured extraction amounts (meta-only stub) — queue skews to needs_review until ingest/OCR enriches meta.
- EDC bank cards still awaiting Peaches visual on preserved close.
- Do not cancel/reopen/force-recapture preserved VDC-87202768.

### EXACT URLS (Beta)
- Receipts UI: `http://127.0.0.1:8788/ggv/finance/receipts`
- Accounting queues: `GET /api/ggv/finance/accounting/queues?queue=needs_review`
- Receipt detail: `GET /api/ggv/finance/accounting/receipts/{receipt_key}`
- Receipt image: `GET /api/ggv/finance/accounting/receipts/{receipt_key}/image`
- Human confirm: `POST /api/ggv/finance/accounting/receipts/{receipt_key}/confirm`
- Vault list (legacy): `GET /api/ggv/finance/receipts`

### Classification
**CODE COMPLETE / INTEGRATION PARTIAL** — GGV accounting queues proved on persisted catalog rows + HTTP under temporary development_assertion; CF auth restored. Not Matt-ready. P2P not started.

### Continuation note
- 2026-10-03 ~17:35 WITA: continuation 3 completed GGV accounting queues slice. Beta restarted for code load; CF auth restored after HTTP prove. Prod 15975 sacred.
