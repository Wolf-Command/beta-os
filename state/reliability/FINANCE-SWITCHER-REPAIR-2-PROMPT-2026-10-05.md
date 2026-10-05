# FINANCE-SWITCHER-REPAIR-2 (P0 — OWNER 5 Oct 2026 12:49 WITA)

You are the single Beta writer for this slice. Workspace `/Users/wolfterminal/beta-os`. Today Monday 5 Oct 2026, Asia/Makassar (WITA, UTC+8).

Title: Unblock Zayen's Finance business switcher assets + Matt AMG CoA/journals/ledger read.

Bounded. staff_ready=false, human_commissioned=false, zayen_ready=false. No commit / push / merge / clean. No money movement.

## Evidence (re-prove 5 Oct 12:42–12:48 WITA)
`state/reliability/ZAYEN-FINANCE-SWITCHER-REPROVE-2026-10-05.json` after FINANCE-SWITCHER-REPAIR-1 (BF-09bc100e77ed):
1. `/api/finance/entities` for Zayen is already correct: GGV `selectable=false` (+ NO ACCESS), AMG/BZG selectable. Mount node `#entity-switch[data-wolf-finance-switcher]` is present on `/finance`, `/amg/finance`, `/amg-finance-ops`, `/bzg/finance`.
2. **Dropdown never mounts for Zayen** because `scripts/core/staff_access.officer_must_deny` returns True for `GET /shared/finance-switcher.js` and `GET /shared/finance-switcher.css` (403 "This account is limited to Atrium Finance"). Matt and Amanda can load the assets (not finance-only-only). Authentic empty mount: `#entity-switch` stays empty.
3. Matt still gets 403 on `/api/amg/finance/accounts`, `/api/amg/finance/journals`, `/api/amg/finance/ledger` (`atrium.board.read` on ENT-AMG missing for ROLE-MATT / his assignment chain). Desk/notas/bills already 200.

## Scope (do ONLY this)
### A. Narrow allowlist for switcher assets
In `scripts/core/staff_access.py` `officer_must_deny`, allow **only**:
- `/shared/finance-switcher.js`
- `/shared/finance-switcher.css`
(and the same paths with a trailing slash stripped / query-stripped via the existing `base` normalisation)

Do **NOT** open all of `/shared/`. Do **NOT** loosen any other path. Do **NOT** change ATRIUM_PAGE_PATHS or the finance-only seat classification. Prefer an exact `base in {...}` check next to the existing `/finance` / `/api/finance/entities` allow.

### B. Matt AMG CoA / journals / ledger read
Grant `atrium.board.read` (and whatever sibling read the CoA/journals/ledger `_require` calls need — check `scripts/core/atrium_finance_desk.py`: `atrium.coa.read`, `atrium.journal.draft`, `atrium.ledger.read`, `atrium.report.read` as used by those GET routes) to Matt on **ENT-AMG** via the Person→Assignment→Role→Scope→Permission model:
- Prefer attaching the missing permissions to an existing Matt role/assignment that already has SCOPE-AMG-FINANCE (e.g. ASG-MATT-OWNER-1 / ROLE-MATT), **or** ensure ROLE-MATT (or the role on the AMG-scoped assignment) receives those permission rows with effect ALLOW, scoped so `rbac.can(PERS-MATT, code, {entity_id: ENT-AMG})` is true.
- **No hardcoded person ids / emails in route code.** Migration/seed under `scripts/migrations/` or the existing org_* seed path used by prior finance packs; back up `catalog/content_library.sqlite` under `catalog/backups` with sha256 before any write.
- Do not invent a new person. Do not widen payment / approve / post / vendor.bank.change. Do not grant Zayen anything new. Do not change Amanda.

### C. Out of scope
Do not redesign the switcher. Do not touch Uma close / petty / protected closes. Do not edit the Atrium sidecar repo. Do not restart prod.

## Tests — `scripts/tests/test_finance_switcher_repair2_20261005.py`
In-process harness (`serve_beta.BetaHandler`, ephemeral port, `BETA_AUTH_MODE=development_assertion`, `X-Wolf-Subject`, `canonical_guard.isolate_runtime_catalog()`).
1. Zayen `GET /shared/finance-switcher.js` → 200 (JS body); `GET /shared/finance-switcher.css` → 200. Zayen `GET /shared/other-file-that-does-not-need-to-exist` (or a non-allowlisted path under `/shared/` if one exists) still denied OR 404 — prove the allowlist is narrow (if no other shared file, assert `officer_must_deny(PERS-ZAYEN, "/shared/secret", conn)` is still True).
2. Zayen rendered HTML on `/bzg/finance` and `/amg-finance-ops` includes the switcher script/link AND after a headless/eval mount (or HTML containing options from a server-rendered path if you add one) — minimum: fetch `/api/finance/entities` as Zayen still returns GGV disabled + AMG/BZG selectable, and the JS/CSS 200s so a real browser can mount. Prefer a small CDP/Chrome or jsdom-less check that the assets are not 403.
3. Amanda: `/api/finance/entities` unchanged (GGV selectable, AMG/BZG not); AMG/BZG pages still clean 403; `/shared/finance-switcher.js` still 200 for her.
4. Matt: `GET /api/amg/finance/accounts` → 200 with accounts list; `/api/amg/finance/journals` → 200; `/api/amg/finance/ledger` → 200. `/api/finance/entities` still three selectable. GGV/BZG still 200 for him.
5. Regression: Zayen GGV pages/APIs still clean 403; `/api/amg/finance/audit` still has zero ENT-GGV events for Zayen; protected closes / prod pid unchanged; re-run `test_finance_switcher_repair1_20261005.py` still green.

## Rules
- Production `127.0.0.1:8787` pid **1297** SACRED. Reload Beta only at the very end, only if Python/HTML/DB seed changed, only if exactly one listener on 8788, via existing beta restart path; else `RELOAD_HELD`.
- Do not commit/push/merge/clean. Do not kill other processes. Do not start another agent. Leave cursor-agent alone.
- Protected: VDC-470e741f, VDC-64f5f529 untouched; do not submit VDC-8fd544e2; PETTY-UMA-6D853EEAE0 stays Rp552,700.
- No fabricated finance rows. Live DB reads `mode=ro` unless the Matt grant seed requires a write (then backup first).
- Do not print process command lines. Do not message Matt/Zayen.

## Output
`state/reliability/FINANCE-SWITCHER-REPAIR-2-RESULT-2026-10-05.json`: pack, run_id (from ACTIVE), files_changed, allowlist_paths, matt_grant_path (role/permission/assignment ids touched), test_file, tests_pass, tests_fail, regression, beta_reloaded / reload_held, beta_listener_pid, prod_pid_unchanged, protected_closes_unchanged, staff_ready=false, human_commissioned=false, zayen_ready=false, status (IMPLEMENTATION_DONE or BLOCKED), exit_code.

Last printed line: `RESULT_JSON: state/reliability/FINANCE-SWITCHER-REPAIR-2-RESULT-2026-10-05.json` (do NOT print EXIT; launcher appends `EXIT:N`).
