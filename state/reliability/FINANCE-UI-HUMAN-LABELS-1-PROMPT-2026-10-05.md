# FINANCE-UI-HUMAN-LABELS-1 (OWNER 5 Oct 2026 13:07 WITA)

You are the single Beta writer for this slice. Workspace `/Users/wolfterminal/beta-os`. Today Monday 5 Oct 2026, Asia/Makassar (WITA, UTC+8).

Title: Finance pages speak human — remove internal ids / engineering flags from staff + Owner UI.

Bounded. staff_ready=false, human_commissioned=false, zayen_ready=false. No commit / push / merge / clean. No money movement. No data changes.

## Owner rule
Internal IDs and engineering language (scope codes, `ENT-*`, `SCOPE-*`, `ROLE-*`, `*_ready=…`, `human_commissioned`, `FC-SHELL-*`, "template shell", etc.) NEVER appear in staff/Owner UI. They may remain only in audit/debug surfaces (audit JSON, `/api/*/audit`, logs, data-* attributes not rendered as text, hidden debug panels).

## Evidence
`state/reliability/ZAYEN-FINANCE-SWITCHER-REPROVE-V3-2026-10-05.json` (12:59 WITA, after FINANCE-SWITCHER-REPAIR-2 BF-2731e55ad30e): all 7 switcher behaviours PASS + Matt/Amanda regressions PASS — but the rendered pages on `/finance`, `/amg/finance`, `/amg-finance-ops`, `/bzg/finance`, `/ggv/finance` show engineering text:
1. **SEAT selector** reads `Atrium Financial Controller · SCOPE-AMG-FINANCE`.
2. **Chips / notes** like `staff_ready=false`, `zayen_ready=false`, and text like `COA template shell (zero journals)… Not staff_ready. Not human_commissioned.`
3. **Red `NO ACCESS` help line** under the Business dropdown shows as a page-level warning even when BZG (an allowed business) is selected.

## Scope (do ONLY this)
### A. Seat selector — plain role / business
Show e.g. `Financial Controller — Atrium` / `Financial Controller — Blu Zone Group` (role + human business name). Drop scope codes (`SCOPE-…`) and any other ids from the visible label. Option `value` / data-* may keep ids. Find where the seat label is composed (rendered HTML in `scripts/serve_beta.py`, `scripts/core/atrium_full_mount.py`, `scripts/core/atrium_finance_desk.py`, `scripts/core/atrium_fc_authority.py`, `scripts/core/staff_access.py`, or `dashboards/…`). If the label is composed inside the Atrium sidecar repo, do NOT edit the sidecar: apply a narrow Beta-side render/label mapping, or report BLOCKED with the exact source.

### B. Remove engineering chips / notes — replace with plain wording
- Remove visible chips such as `staff_ready=false`, `zayen_ready=false`, `human_commissioned=false`.
- Replace notes like `COA template shell (zero journals)… Not staff_ready. Not human_commissioned.` with plain wording, e.g. `No journals posted yet`, `Chart of accounts set up — no journals posted yet`.
- Likely sources (check, do not assume): `scripts/core/entity_books.py` (ENT-BZG / ENT-GGV labels "COA template shell (zero journals)"), `scripts/core/fin_cash_truth1.py`, `fin_tax_shell1.py`, `fin_ap_ar_shell1.py`, `bzg_inventory_truth1.py` (`note:` strings), plus whatever page renders the chips. Change only **display** text on finance pages. If an API field is consumed by tests/audit as a machine flag, keep the field and stop rendering it; do not rename JSON keys that other code reads.
- The queue / API flags `staff_ready=false`, `human_commissioned=false` stay **false** in data — only their UI rendering goes away.

### C. NO ACCESS only on the greyed GGV option
- The `NO ACCESS` marker belongs only on the disabled GGV option in the Business dropdown (option text/title, e.g. `GGV — no access`, greyed).
- Remove the red page-level help line under the dropdown when the selected business is allowed (AMG/BZG for Zayen; GGV for Amanda). Do not show a page-level warning at all for a merely-disabled option.
- Sources: `dashboards/shared/finance-switcher.js` / `.css` (help line render), `scripts/core/ggv_finance_invoice.py` ~L476 (`row["help"] = "NO ACCESS"` in `/api/finance/entities`). Keep the API's `selectable=false` for GGV; the per-row `help` may stay in the API but must not render as a page-level line.

### D. Out of scope
Do not redesign the switcher or change its behaviour. Do not change RBAC / grants / `officer_must_deny` / ATRIUM_PAGE_PATHS. Do not touch Uma close / petty / protected closes. Do not edit the Atrium sidecar repo. Do not restart prod. No DB writes.

## Must stay intact (all 7 switcher behaviours + server-side GGV deny)
1. Zayen: AMG + BZG selectable. 2. GGV visible but disabled (greyed, no access). 3. Switch AMG→BZG navigates to `/bzg/finance`. 4. Switch BZG→AMG → `/amg-finance-ops`. 5. No cross-entity leak (`/api/amg/finance/audit` zero ENT-GGV events for Zayen). 6. Direct `/ggv/finance` + GGV desk/recon/audit APIs → 403 for Zayen (server-side). 7. Refresh persistence (BZG pref sticks; GGV pref ignored → AMG).

## Tests — `scripts/tests/test_finance_ui_human_labels1_20261005.py`
In-process harness (`serve_beta.BetaHandler`, ephemeral port, `BETA_AUTH_MODE=development_assertion`, `X-Wolf-Subject`, `canonical_guard.isolate_runtime_catalog()`).
1. For Zayen, Matt, Amanda: rendered HTML of each finance page they can open (`/finance`, `/amg/finance`, `/amg-finance-ops`, `/bzg/finance`, `/ggv/finance`) contains NO visible-text match for `SCOPE-`, `ENT-`, `ROLE-`, `staff_ready`, `zayen_ready`, `human_commissioned`, `template shell`, `FC-SHELL` (strip `<script>`, attributes and HTML comments before checking visible text; data-* attributes allowed).
2. Seat selector label for Zayen/Matt reads role + business in plain words (assert e.g. `Financial Controller` present and `SCOPE-` absent).
3. Pages with no journals show plain wording (e.g. `No journals posted yet`) instead of the shell note.
4. `finance-switcher.js` no longer renders a page-level NO ACCESS help line when the selected business is selectable; the disabled GGV option still carries the no-access marker (static JS/DOM-string check is acceptable; prefer a real-browser/CDP check if available).
5. Regression: re-run `scripts/tests/test_finance_switcher_repair1_20261005.py`, `scripts/tests/test_finance_switcher_repair2_20261005.py`, `scripts/tests/test_bzg_zayen_finance_prove1_20261005.py` — all green (update only assertions that pinned the old engineering strings, and say which). Amanda: `/api/finance/entities` unchanged (GGV selectable, AMG/BZG not), AMG/BZG pages/APIs clean 403. Matt: three selectable; `/api/amg/finance/accounts|journals|ledger` 200. Zayen GGV pages/APIs clean 403. Protected closes / prod pid unchanged.

## Rules
- Production `127.0.0.1:8787` pid **1297** SACRED. Reload Beta only at the very end, only if Python/HTML/JS changed, only if exactly one listener on 8788, via existing beta restart path; else `RELOAD_HELD`.
- Do not commit/push/merge/clean. Do not kill other processes. Do not start another agent. Leave cursor-agent alone.
- Protected: VDC-470e741f, VDC-64f5f529 untouched; do not submit VDC-8fd544e2; PETTY-UMA-6D853EEAE0 stays Rp552,700.
- No data changes; live DB reads `mode=ro` only. No fabricated finance rows.
- Do not print process command lines. Do not message Matt/Zayen/Amanda.

## Output
`state/reliability/FINANCE-UI-HUMAN-LABELS-1-RESULT-2026-10-05.json`: pack, run_id (from ACTIVE), files_changed, strings_replaced (old → new, per page), seat_label_source, no_access_render_change, test_file, tests_pass, tests_fail, regression (switcher repair1/repair2/zayen prove1, Amanda, Matt), beta_reloaded / reload_held, beta_listener_pid, prod_pid_unchanged, protected_closes_unchanged, data_changes=none, staff_ready=false, human_commissioned=false, zayen_ready=false, status (IMPLEMENTATION_DONE or BLOCKED), exit_code.

Last printed line: `RESULT_JSON: state/reliability/FINANCE-UI-HUMAN-LABELS-1-RESULT-2026-10-05.json` (do NOT print EXIT; launcher appends `EXIT:N`).
