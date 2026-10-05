# FINANCE-SWITCHER-REPAIR-1 (P0 — OWNER 5 Oct 2026 12:02 WITA)

You are the single Beta writer for this slice. Workspace `/Users/wolfterminal/beta-os`. Today Monday 5 Oct 2026, Asia/Makassar (WITA, UTC+8).

Title: ONE shared Finance business switcher (GGV / AMG / BZG) driven by Person → Assignment → Role → Entity scope → Permission, with greyed **NO ACCESS** entries, entity-scoped server guards, and refresh persistence.

Bounded slice. Shared component, not per-entity copies. staff_ready=false, human_commissioned=false, zayen_ready=false. No commit / push / merge / clean. No money movement.

## Evidence (isolated PROVE run 5 Oct 12:16–12:19 WITA on a snapshot of the tree AFTER FINANCE-CORE-STATEMENTS-1, FINANCE-CORE-BZG-PROVE-1 and BZG-ZAYEN-FINANCE-PROVE-1)
Full results: `state/reliability/ZAYEN-FINANCE-SWITCHER-PROVE-2026-10-05.json`. Summary of what is still wrong:
1. **No greyed entities anywhere.** `finance_entities()` in `scripts/core/ggv_finance_invoice.py` returns only AUTHORISED entities, so Zayen sees `AMG · BZG` (GGV absent) and Amanda sees `Finance · GGV` (AMG/BZG absent). The string "NO ACCESS" exists nowhere in the code. Owner spec: unauthorised businesses are VISIBLE but disabled with simple help text **NO ACCESS**.
2. **Not one component.** Three different renderers: `dashboards/ggv-finance.html` `renderEntities` (old inline "Finance · GGV · AMG · BZG" links), `dashboards/amg-finance-ops.html` and `dashboards/bzg-finance.html` (new "Current entity:" chips from BZG-ZAYEN-FINANCE-PROVE-1). Chips, not a dropdown.
3. **AMG chip leads to a page with no switcher.** The AMG chip href is `/amg/finance`, which `serve_beta._atrium_product_dispatch` / `scripts/core/atrium_full_mount.py` proxies to the Atrium Finance product (sidecar 127.0.0.1:8790). That page has no Wolf chrome and no switcher, so Zayen cannot switch AMG → BZG from his main AMG entry. Every `/amg/finance/*` sub-path also lands in the product (`/amg/finance/banking` → 403 "This seat cannot approve, post, pay, change a bank…").
4. **Cross-entity leak:** `GET /api/amg/finance/audit` returns 5 audit events, all `entity_id = ENT-GGV` (`ggv_receipt_accounting.confirm` ×4, `ggv.invoice.sequence.seed` ×1), to Zayen (and Matt) in the AMG context. Must filter to the AMG entity only.
5. **Crash instead of clean 403:** for a person with no AMG access (Amanda), `GET /amg-finance-ops`, `/amg-finance-ops.html` and `/api/amg/finance` raise uncaught `AmgFinanceDeskError` → connection dropped (browser `ERR_EMPTY_RESPONSE`). Same class of defect STATEMENTS-1 fixed for GGV desk/recon/audit.
6. **Zayen (AMG Financial Controller) gets 403 on `/api/amg/finance/notas`, `/bills`, `/reconciliation`** with the wrong text "You do not have access to GGV notas." (he holds `atrium.board.read` on ENT-AMG but not `finance.nota.read`). The AMG Finance Core Receipts/Notas, Bills and Reconciliation tabs therefore fail for him. Use the same read-only dual guard BZG-PROVE-1 used for BZG (`finance.nota.read OR atrium.board.read`, entity-scoped) for AMG READ endpoints only. Do NOT add role grants; do not widen any write permission.
7. Wording/label bugs on AMG pages: AMG Receipts summary prints `ENT-GGV · persisted accounting rows`; the AMG books line says `atrium-ggv.sqlite … COA 0 accounts` while `/api/amg/finance/accounts` returns 190 accounts. Make the AMG page label truthful (AMG; show the real CoA count from the AMG books the desk API uses, or say the books slot is a different store — never "0" when 190 exist).
Already PASS (keep green, do not rework): every GGV page (18) and GGV API (16, incl. desk/reconciliation/audit, statement detail/original with guessed ids) returns a clean 403 for Zayen; BZG data loads for Zayen and Matt; Amanda GGV allowed; refresh keeps the entity because the URL carries it.

## Product spec (Owner)
A. **One shared switcher component** (one JS/CSS file under `dashboards/` served by Beta, e.g. `dashboards/shared/finance-switcher.js`, plus one server payload) used by `ggv-finance.html`, `amg-finance-ops.html`, `bzg-finance.html` — remove the three ad-hoc renderers. It is a **dropdown** (native `<select>` or accessible listbox button) labelled `BUSINESS`, showing **GGV, AMG / ATRIUM, BZG** in a stable order.
B. Server payload (extend `finance_entities` or add `GET /api/finance/entities`): every Finance entity from the entity catalogue (`org_entities` / existing `ENTITY_FINANCE_CHIP`), each `{id, label, href, selectable: bool, help}`; `selectable` computed ONLY from the RBAC chain (PERSON → ASSIGNMENT → ROLE → ENTITY SCOPE → PERMISSION) — no person ids/names in code. Non-selectable entries carry `help: "NO ACCESS"` and **no href**. No permission codes, scope ids or technical words in anything the user sees.
C. Rendering: selectable options navigate to that entity's Finance home; non-selectable options are greyed and disabled (cannot navigate, not focus-activatable), with hover `title="NO ACCESS"` AND a tap/click help line "NO ACCESS" for phones (390px). Current entity shown as the selected value.
D. **Server independently denies** every GGV/AMG/BZG Finance page and API for a person without that entity — clean 403 (HTML "Access denied" page for browser navigation, JSON `{ok:false,error:"forbidden"}` for APIs), never a crash, never data. Greyed UI is UX only.
E. **AMG entry with switcher:** the switcher must be reachable on Zayen's AMG Finance. Preferred: Beta-side injection of the shared switcher bar into the proxied Atrium product HTML document response only (`text/html` index response in `_atrium_product_dispatch`; small `<script src>` + mount node; no change to API/asset proxying). Do NOT edit `/Users/wolfterminal/atrium-finance` or restart the sidecar. If injection is unsafe, point the AMG option at `/amg-finance-ops` (which has the switcher and an obvious OPEN ATRIUM FINANCE link) and report the choice in the result.
F. **Refresh / persistence:** the URL path is the source of truth (refresh keeps the selected business). Add canonical entry `GET /finance` that redirects to the person's last selected AUTHORISED Finance entity (client `localStorage` key `wolf.finance.entity`, validated server-side via a query param or by re-checking the payload) or else the first authorised one; it must NEVER land on or restore an entity the person cannot access (GGV for Zayen). `/finance` must pass the Atrium-only seat wall in `scripts/core/staff_access.py` for finance seats (today Zayen gets "This account is limited to Atrium Finance" on `/finance`).
G. Fix items 4–7 above (AMG audit entity filter; clean 403 on AMG desk deny paths; AMG read dual guard; AMG labels).

## Expected per person (from the RBAC chain, not hardcoded)
- Matt: GGV, AMG, BZG all selectable.
- Zayen (PERS-ZAYEN, laluzayen@gmail.com): AMG and BZG selectable; GGV visible, greyed, NO ACCESS; all GGV Finance pages + APIs 403 by direct URL.
- Amanda: GGV selectable; AMG and BZG greyed NO ACCESS; AMG/BZG pages + APIs clean 403 (no dropped connections).

## Rules
- Production `127.0.0.1:8787` pid **1297** SACRED. Reload Beta only at the very end, only if Python changed, only if exactly one listener remains on 8788, via the existing beta restart path; else `RELOAD_HELD`.
- Do not commit/push/merge/clean. Do not kill other processes. Do not start another agent. Leave cursor-agent pid 2627 alone. Do not touch the Atrium sidecar process or repo.
- Protected: closes VDC-470e741f, VDC-64f5f529 untouched; do not submit VDC-8fd544e2; do not touch PETTY-UMA-6D853EEAE0 (Rp552,700). Do not edit Uma Blu close or petty capture code.
- No RBAC grant changes, no fabricated rows. Live DB `catalog/content_library.sqlite` read with sqlite3 `mode=ro`; back up under `catalog/backups` (sha256) before ANY write (none expected).
- No payment.execute / payment.approve / vendor.bank.change. Do not print process command lines or environment. Do not message Matt or Zayen.

## Tests (required) — `scripts/tests/test_finance_switcher_repair1_20261005.py`
Use the existing in-process harness (`serve_beta.BetaHandler` on an ephemeral port, `BETA_AUTH_MODE=development_assertion`, `X-Wolf-Subject`, `canonical_guard.isolate_runtime_catalog()`); temp dirs for any originals. For Zayen:
1. Switcher payload + rendered HTML on `/bzg/finance`, `/amg-finance-ops` and the AMG entry from spec E list AMG and BZG selectable.
2. GGV present, `selectable=false`, `help="NO ACCESS"`, no href; rendered option disabled with NO ACCESS text; no permission codes/scope ids in the payload's user-facing fields or HTML.
3. Switch AMG → BZG: the BZG option href opens `/bzg/finance`; `/api/bzg/finance/counts` returns BZG counts (PO 543 / suppliers 103 / supplier bills 473 on the current DB) and only ENT-BZG rows.
4. Switch BZG → AMG: the AMG option opens the AMG entry; AMG CoA (`/api/amg/finance/accounts`, 190 today) and journals load; AMG notas/bills/reconciliation reads return 200 for Zayen.
5. No cross-entity leakage: AMG responses (incl. `/api/amg/finance/audit`, statements library, desk) contain only ENT-AMG records; BZG responses only ENT-BZG; GGV ids guessed into AMG/BZG routes → 403/404.
6. Every GGV Finance page and API (enumerate `ggv_finance_nota.PAGE_PATHS` + all `/api/ggv/finance/*` routes incl. statement detail/original with real GGV ids) → clean 403, never a dropped connection.
7. `/finance` redirects to the last authorised entity; a stored `GGV` preference is ignored for Zayen (lands on AMG or BZG); refresh of `/bzg/finance` stays BZG.
Regression: Matt → three selectable, BZG + AMG + GGV pages 200; Amanda → GGV selectable, AMG/BZG greyed, `/amg-finance-ops`, `/api/amg/finance`, `/bzg/finance` → clean 403 (status 403, not a connection error).
Re-run and keep green: `test_finance_core_statements1_20261005.py`, `test_finance_core_ggv1_20261005.py`, `test_finance_core_amg_prove1_20261005.py`, `test_finance_core_bzg_prove1_20261005.py`, `test_bzg_finance_usability1_20261005.py`, and the BZG-ZAYEN-FINANCE-PROVE-1 tests.
Optional but wanted: headless Chrome screenshots (desktop 1024 + phone 390) of Zayen's dropdown opened with GGV greyed, saved under `docs/wolf/ops/shots/finance-switcher-repair1-*.png` (pattern: `scripts/audit/coreent1_shots.py`).

## Output
`state/reliability/FINANCE-SWITCHER-REPAIR-1-RESULT-2026-10-05.json`: pack, run_id (from ACTIVE), files_changed, switcher_component path, amg_entry_choice (injection or /amg-finance-ops), routes_added, test_file, tests_pass, tests_fail, regression_tests, per_person_matrix (Matt/Zayen/Amanda × GGV/AMG/BZG: selectable + server status), screenshots, beta_reloaded / reload_held, beta_listener_pid, prod_pid_unchanged, protected_closes_unchanged, staff_ready=false, human_commissioned=false, zayen_ready=false, status (IMPLEMENTATION_DONE or BLOCKED + reason), exit_code.
Best Zayen link to record in the result: `https://beta.wolfcommand.net/finance` (if spec F lands) else `https://beta.wolfcommand.net/bzg/finance`.

Last printed line: `RESULT_JSON: state/reliability/FINANCE-SWITCHER-REPAIR-1-RESULT-2026-10-05.json` (do NOT print an EXIT line; the launcher appends `EXIT:N`).
