# WOLF Phase 2.6 — BOARD INCIDENT REPORT
**For:** Peaches → Matthew  
**When:** 2026-09-15 16:45:38 WITA  
**Lane:** Beta OS `/Users/wolfterminal/beta-os/` on **:8788 ONLY**  
**URL:** https://beta.wolfcommand.net/content-2.0.html (proved via local `http://127.0.0.1:8788/content-2.0.html` same static file)  
**Machine:** Wolfs-Mac-Studio.local (`36d8fa4b-2d58-4983-b227-e5bfa5495e78`)  
**Status:** **SMOKE PASS** after minimal repair (do NOT call Phase 2.6 PASS on suite alone)

---

## Hard confirms

| Guard | Status |
|---|---|
| NO :8787 CHANGE | **CONFIRMED** — PID **32884** before and after |
| NO OPERATIONAL PLAN TEST MUTATION (browser smoke) | **CONFIRMED** — Post/Story opened, Edit scrolled, Cancel/Close only — **no Save** |
| NO OPERATIONAL LIBRARY TEST POLLUTION | **CONFIRMED** — search/filter/preview/selection only; ops asset count still **5** |
| NO METRICOOL WRITE | **CONFIRMED** |
| NO PUBLISH | **CONFIRMED** |
| NO LIVE AI | **CONFIRMED** — WI honest unavailable shell |
| NO NEW FEATURES | **CONFIRMED** — repair only |

**Note on automated suite:** Re-running `test_phase2_6_team_readiness.py` (required) exercises review-state transitions on Habitat plan #9 by design. After suite, plan left **APPROVED**. Browser smoke itself did not Save/edit card content. Ops Library unchanged (5).

---

## 1. What Matt experienced

On https://beta.wolfcommand.net/content-2.0.html the Content Engine looked like a shell that **never came alive**: Dashboard stuck on “Loading current fortnight…”, nav appeared not to switch views, Content Plan empty, Library/Upload/WI inert. Health could still be green. “Nothing works.”

## 2. Reproduced?

**YES** on local `:8788` serving the same `dashboards/content-2.0.html` (symlink at beta-os root).  
Playwright as Matt (`mrwolf@wolfcommand.net` via `X-Wolf-Subject` / localStorage):

- Before fix: **zero** `/api/*` boot calls; Dashboard forever Loading; plan click did nothing useful.
- Root throw prevented `init()` and all Phase 2.6 overrides from running.

## 3. Exact root cause

**Primary (first runtime failure):** Phase 2.6 HTML rewrite removed `#wiOpenPlan`, `#wiRefreshContext`, and `#wiPrefill` from the Wolf Intelligence view, but Wire UI still did:

```js
$("wiOpenPlan").addEventListener(...)
```

→ `TypeError` on `null` → **aborts the rest of the IIFE** → `init()` never runs → no capabilities, no dashboard load, nav handlers after the throw never attached (and Phase 2.6 overrides never applied). Also missing `</script></body></html>` (browsers auto-recover; not the killer).

**Secondary (exposed after primary fix):** `setView("plan")` calls `loadPlanView()`, which still read **`ux.counts.posts`**, but Phase 2.6 API returns **`ux.progress`** only (`counts` removed). Toast: `Cannot read properties of undefined (reading 'posts')` → empty plan body.

**Tertiary:** Phase 2.6 overrode `renderBriefView` / `renderBriefEdit`, but the live board calls **`renderBrief` / `viewBriefHtml`** — team brief fields never shown until `renderBrief` was routed.

## 4. Why 42/42 missed it

Suite hits **HTTP APIs** with `X-Wolf-Subject` headers and greps HTML strings. It never **boots the served page in a real browser**, never executes Wire UI, never catches a mid-script DOM null throw that prevents `init()`. Health green ≠ board works.

## 5. Files changed

| File | Action |
|---|---|
| `/Users/wolfterminal/beta-os/dashboards/content-2.0.html` | Minimal repair |
| `/Users/wolfterminal/beta-os/scripts/tests/test_phase2_6_board_smoke_regression.py` | **NEW** regression |
| Baks under `archive/baks/content-2.0.html.bak-incident-2.6-board-*` | Pre-change copies |

**Not changed:** `serve_beta.py`, wolf-system, :8787, Metricool, Library DB rows (no ops pollution), no new features.

## 6. Exact repair

1. Restore `#wiOpenPlan`, `#wiRefreshContext`, `#wiPrefill` into WI shell (keep Phase 2.6 chat UI).
2. Null-guard WI listeners + `wiPrefill` access (defense in depth).
3. Append missing `</script></body></html>`.
4. Phase 2.6 `loadDashboard` now sets `dashSub` / `state.planId`.
5. Override `loadPlanView` → `openPlan` (progress labels; no `ux.counts`).
6. Override `renderBrief` to call Phase 2.6 `renderBriefView` / `renderBriefEdit` + Cancel/Save wiring.
7. Regression test: DOM presence, guarded wire, closed HTML, JS syntax, **Playwright boot** (dashboard leaves Loading, plan renders cards).

Static HTML only — **no :8788 process restart** required; PID unchanged.

## 7. Browser smoke result

**PASS** — Dashboard → Content Plan (plan #9, 3 posts / 14 stories) → Post modal Edit/scroll/Cancel/Close (**no Save**) → Story modal Edit/Cancel/Close → Library search `workers` / preview video / selection → Upload wizard step1→step2 (**no commit**) → WI honest unavailable + dry chat → Dashboard.

Evidence: `/tmp/beta-board-smoke.json`, `/tmp/smoke-0*.png`, `/tmp/WOLF-PHASE2-6-BOARD-REGRESSION-OUT.txt`

## 8. Console after repair

- No uncaught JS / pageerrors.
- Benign: favicon `404` only (filtered).

## 9. Failed network after repair

- No failed `/api/*` in smoke.
- Favicon 404 only (unrelated).

## 10. Automated regression result

- **NEW** `test_phase2_6_board_smoke_regression.py` → **PASS=13 FAIL=0**
- Existing `test_phase2_6_team_readiness.py` → **PASS=42 FAIL=0**
- Log: `/tmp/WOLF-PHASE2-6-BOARD-REGRESSION-OUT.txt`, `/tmp/WOLF-PHASE2-6-TEST-OUT-AFTER-INCIDENT.txt`

## 11. Matt identity / capability

Dev/server identity path: **`X-Wolf-Subject` / `?subject=`** (documented DEVELOPMENT ONLY; CF Access JWT not wired in `resolve_authenticated_subject`).

Live `/api/me/capabilities` as Matt:

```json
{
  "ok": true,
  "subject": "mrwolf@wolfcommand.net",
  "can_create_plan": true,
  "can_edit_plan": true,
  "can_approve_plan": true,
  "can_view_plan": true,
  "can_update_production": true,
  "can_upload": true,
  "can_use_wolf_intelligence": true
}
```

Gates **not** weakened.

## 12. :8787 PID before / after

- **Before:** 32884  
- **After:** 32884  
- **Untouched.**

## 13. :8788 PID before / after

- **Before:** 42992  
- **After:** 42992  
- (Static HTML fix; process not restarted.)

## 14. Habitat plan #9 / operational Library

| Item | Result |
|---|---|
| Browser smoke Save on plan #9 cards | **None** |
| Ops Library pollution | **None** (count **5**) |
| Automated suite review-state exercise on #9 | Occurred (suite design); left **APPROVED** |
| Plan regenerated? | **No** |

---

## One-liner root cause

Phase 2.6 FE shipped incomplete: missing WI DOM nodes crashed boot before `init()`, and plan view still depended on removed `ux.counts`.

## STOP

Feature work remains stopped. Board smoke is the acceptance bar — not 42/42 alone.
