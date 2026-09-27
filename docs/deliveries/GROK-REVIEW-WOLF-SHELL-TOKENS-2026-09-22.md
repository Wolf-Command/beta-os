# GROK REVIEW — Wolf Shell + Tokens (Wave 1) — 2026-09-22

**Run:** `BF-wolf-shell-tokens-20260922`  
**Stage outcome:** **DONE PASS** (Peaches Mac-routed verify)  
**Head:** `f3ab8f7` (commit deferred — shared dirty `serve_beta` WIP)  
**Production:** `:8787` untouched (LISTEN; shell routes **404**)

## Evidence (re-run)

| Check | Result |
|-------|--------|
| Cursor EXIT | SUCCESS (log EXIT:0; PASS=94 claimed) |
| Peaches re-run `test_wolf_shell_tokens.py` | **PASS=94 FAIL=0** EXIT: SUCCESS |
| Live `:8788` `/progress.html` | **200**; one `#wolfnav`; one `#wolfnav-t`; tokens + `wolf-shell.css` + `sidenav.js` injected |
| Live anon `:8788` `/owner-empire-pack` | **403** |
| Live anon `:8788` `/bzg/uma-blu` | **403** |
| Live anon `:8788` `/api/owner/empire-pack` | **403** |
| Live anon `:8788` `/api/bzg/uma-blu/today` | **403** |
| Live anon `:8788` `/api/ggv/ops-pack` | **403** |
| Live anon `:8788` `/api/wolf/shell-whoami` | **200**; `pages=[]`; `proven:false` `ready:false`; `second_boards_menu:false` |
| Prod `:8787` `/progress.html` `/owner-empire-pack` `/bzg/uma-blu` `/api/wolf/shell-whoami` | **404** |
| Listeners | `:8787` up · `:8788` up |

## Scope isolation (vs shared dirty tree)

**In-pack (Wave 1):**
- `dashboards/wolf-tokens.css` (new)
- `dashboards/assets/wolf-shell.css` + `dashboards/assets/sidenav.js` (new)
- `scripts/core/wolf_shell.py` + `scripts/tests/test_wolf_shell_tokens.py` (new)
- Surgical `serve_beta` adds: `wolf_shell` import, `GET /api/wolf/shell-whoami`, HTML inject hook
- Sample attrs only: `data-wolf-page-type` / `data-wolf-shell="global"` on progress / owner-empire-pack / bzg-uma-blu

**Not claimed as this pack:** prior untracked `*-mgmt-cluster.html`, large pre-existing `serve_beta` WIP, progress “Factory now” UI (mtime/attrs only attributable for shell).

## Prove criteria

- One `#wolfnav` on ≥3 samples (progress live; empire/uma via auth tests) — **PASS**
- Phone toggle `#wolfnav-t` — **PASS**
- IA **HOME / BUSINESSES / INTELLIGENCE / SYSTEM** with existing hrefs only — **PASS** (no mgmt-cluster promotion)
- Never second Boards menu — **PASS**
- whoami visibility filter (Owner sees Progress; Devi hides Progress/Empire/GGV) — **PASS** (suite)
- No new dashboard HTML surfaces from this pack — **PASS**
- Do not invent PROVEN/READY — **PASS** (honesty flags + refuse helpers)

## Honesty

- CAP-CORE-11 stays **SPECIFIED** (Global Nav CR remains OPEN through later waves)
- CR `wolf-global-nav-design-system-20260922` stays **OPEN** / Wave-1 evidence only — **not** RESOLVED
- Permissions CR `wolf-permissions-audience-architecture-20260922` stays **OPEN**
- No invent PROVEN/READY / SYSTEM%
- Claim `bf-wolf-shell-tokens-20260922` accepted as Wave-1 shell evidence only

## Shipped (Cursor)

- Tokens + shell CSS + one `#wolfnav` chrome owner
- `scripts/core/wolf_shell.py` IA + whoami filter + inject
- Additive Beta wire in `serve_beta` (uncommitted with shared WIP)

## Next (factory gate)

**Wave 2 — Owner / Empire HOME** per `GROK-PLAN-WOLF-NAV-MIGRATION-ORDER-2026-09-22.md`.  
Route merge/retire stays later (needs Mac inventory). `forbid_new_dashboard_surfaces` softens only for shell-driven HOME landing — no sprawl.
