# GROK REVIEW — Content Engine Staff UX Redesign — 2026-09-24

- Run: `BF-content-engine-staff-ux-20260924`
- Spec: `docs/deliveries/SPEC-Content-Engine-Staff-UX-Redesign-2026-09-24.md`
- Rule: `docs/RULE-Content-Engine-Staff-UX-2026-09-24.md`
- Audit: `docs/deliveries/AUDIT-Content-Engine-Staff-Jargon-Leak-2026-09-24.md`
- Workspace: `/Users/wolfterminal/beta-os` · branch `build/wolf-command-rebuild`
- Bound: Beta `:8788` only. Production `:8787` not mutated.
- Reviewed: 2026-09-24 ~09:32 WITA
- Verdict: **ENGINEERING_PASS** (pack **PASS=48 FAIL=0**). **staff_ready=false**. Haikal retest still required.

## Decision served

Owner P0 Content Engine Staff UX Redesign, recorded 2026-09-24 in `docs/RULE-Content-Engine-Staff-UX-2026-09-24.md` and the SPEC. Human commissioning exception under Credit Conservation. One UX pack. No new agent. No PROVEN / READY / STAFF READY.

## What landed

- `dashboards/content-2.0.html` — staff desk. Primary tabs are **CONTENT PLAN | LIBRARY | UPLOAD | WOLF INTELLIGENCE**. Brand selector stays in the top bar. The old dashboard tab is not primary; the plan view opens by default (fortnight, posts, stories, status). Global nav is marked secondary via `staff-content-desk`.
- Library: large search, existing metadata under **More filters**, thumbnail grid, Select all / Deselect / live count, **Download (ZIP)** with a visible preparing-download bar. Empty library tells the person to open Upload. Preview shows the media plus name, original file, subject, and shoot date.
- Upload: lifecycle **Uploading → Processing → Saving to Library → Complete**. Statuses map from the existing pipeline. An unknown status stays **In progress**. Failed stays Failed. Complete is only used when the pipeline status is READY, LIBRARY_READY, or COMPLETE.
- Engineering library blocks (operator depth and the index panel) sit in `<!--STAFF_OMIT_ENG-->`. `scripts/core/wolf_shell.py` strips that block for every audience except OWNER and SYSTEM, and `intel_grammar_for_audience` drops Decision Memory and AKR on the Content desk for that same staff path. Owner grammar and the on-disk engineering block remain.
- `dashboards/assets/wolf-shell.css` — on the Content desk, `#wolfnav` is smaller and quieter so it does not compete with the four tabs.
- `scripts/tests/test_content_engine_staff_ux.py` — pack prove.
- Adjusted `scripts/tests/test_haikal_content_ux_wave1.py` for More filters and the lifecycle labels. Adjusted `scripts/tests/test_ggv_content_ops_depth.py` so Haikal’s served page is expected to hide the operator-depth heading. The API routes are unchanged.
- CR `state/completion-register/content-engine-staff-ux-20260924.json` stays OPEN, **SPECIFIED**, `staff_ready=false`, `proven=false`, `ready=false`.

## Evidence

| Check | Result |
|---|---|
| Pack test | `python3 scripts/tests/test_content_engine_staff_ux.py` → **PASS=48 FAIL=0** · `EXIT: SUCCESS` |
| Wave 1 markers | `python3 scripts/tests/test_haikal_content_ux_wave1.py` → **PASS=21 FAIL=0** |
| Four tabs | Present in `#primaryNav`. Dashboard is not a primary button. |
| Staff jargon | `apply_content_staff_desk` for `PERS-HAIKAL` removes the engineering block. Visible markup has no Operator depth, `staff_ready`, Decision Memory, or AKR. |
| Owner block | Same function for `PERS-MATT` keeps `Operator depth` in the file. |
| Upload labels | Uploading, Processing, Saving to Library, Complete are in the page. Unknown status returns `In progress`. |
| CR | `cap_state=SPECIFIED`, `staff_ready=false`, `proven=false`, `ready=false` |
| Shell honesty | `honesty_flags()["staff_ready"]` is false |
| Board JS | `node --check` on the page script passed |
| Production | Listener pid **15975** on `:8787` before and after the Beta restart |
| Beta restart | `scripts/beta_restart.py` only. Old pid 93591 → new pid **26792** on `:8788`. Production still listening. |

## Live desk

`:8788` auth mode is `cloudflare_access` (`development_assertion_allowed=false`). Unsigned `GET /content-2.0.html`, including `X-Wolf-Subject: haikalqilbari123@gmail.com`, returns **403** `Content workspace is not in authorised scope.` That is the existing seat gate. This pack did not switch Beta into development assertion and did not open the page in a browser as Haikal.

The HTML is read from disk on each request, and Beta was restarted so the staff strip in `wolf_shell.py` is loaded. A signed-in Content seat is what Peaches and Haikal still need to click through.

## Nine staff questions (engineering candidate)

1. Content plan — **CONTENT PLAN** tab (opens by default).
2. Upload — **UPLOAD** tab.
3. Find — Library search.
4. Preview — open a thumbnail.
5. Select — checkbox, Select all, Deselect, live count.
6. Download — **Download (ZIP)**; the bar shows while the file is prepared.
7. Upload progress — Uploading, Processing, Saving to Library, Complete.
8. Brand — Brand menu in the top bar.
9. Help — **WOLF INTELLIGENCE** tab. No AKR or Decision Memory on this staff surface.

## Not claimed

- `staff_ready` stays **false**. No Haikal human PASS.
- CAP stays **SPECIFIED**. Not PROVEN. Not READY.
- Smart Upload core was not rewritten. Only the staff progress labels and chrome.
- No new metadata filters. No new dashboard. No Production edit. No PR merge.
- Gate file `state/build-factory/GATE-content-engine-staff-ux-20260924.json` was not on disk. It was not invented.

## Next humans

Peaches verify on a signed-in Beta session → **Haikal RETEST REQUIRED**.

## Peaches independent verify (2026-09-24 09:43 WITA)

- Re-ran `scripts/tests/test_content_engine_staff_ux.py` → **PASS=48 FAIL=0**.
- Re-ran `scripts/tests/test_haikal_content_ux_wave1.py` → **PASS=21 FAIL=0**.
- Confirmed banned jargon lives only inside `<!--STAFF_OMIT_ENG-->` and is stripped for staff audience.
- Production `:8787` pid **15975** unchanged. Beta `:8788` pid **26792**.
- Gate file present: `state/build-factory/GATE-content-engine-staff-ux-20260924.json`.
- Verdict stands: **ENGINEERING_PASS**. **staff_ready=false**. **Haikal RETEST REQUIRED**.
- Credit Conservation: ACTIVE cleared; next_armed=null; breadth veto held.
