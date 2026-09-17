# CURSOR MISSION — Habitat human operator UI (Core publish gate)

**Date:** 2026-09-17 (WITA)  
**Author:** Grok (Peaches executor) — governance brief only; **Cursor writes app code**  
**Lane:** Mac Beta `/Users/wolfterminal/beta-os/` on **:8788** only  
**Branch:** `build/wolf-command-rebuild`  
**machineId:** `36d8fa4b-2d58-4983-b227-e5bfa5495e78`  
**Factory run:** `BF-habitat-human-ui-20260917`  
**Commit message (exact, single):** `feat(content): habitat human operator UI for core publish gate`  
**Remote / Production:** **NO** push · **NO** `:8787` · **NO** wolf-system · **NO** `.env` Metricool flag changes · **NO** `--trust`

---

## Authority / role split

| Who | May |
|-----|-----|
| Peaches / Grok | Plan + this mission under `docs/deliveries/` only |
| **Cursor (this agent)** | `habitat-operator.html` (+ minimal JS/CSS if needed), optional thin `POST /api/planner/reject`, optional tiny smoke test, one commit |
| Peaches / Grok | Must **not** write application code |

Read first (live Mac tree):

- `docs/BUILD-READ-ME-FIRST.md` (if present)
- `docs/RULE-Local-Cursor-Build-Path-2026-09-17.md`
- `docs/RULE-Beta-Construction-Production-Sacred-2026-09-16.md`
- Prior Core publish gate: commit `f833f37` / review `2887397`
- Live handlers for planner submit/approve/publish-gate + `serve_beta.py` static HTML serving
- Existing Beta HTML auth/cookie patterns (same as other Beta pages)
- `tests/test_habitat_publish_gate.py` — **do not break**

Also: `docs/deliveries/GROK-PLAN-HABITAT-HUMAN-OPERATOR-UI-2026-09-17.md`

---

## Phase 0 — Preflight (STOP if any fail)

```bash
cd /Users/wolfterminal/beta-os
export PATH="/Users/wolfterminal/.local/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"
git status -sb                    # prefer CLEAN; if dirty, document + do not clobber unrelated work
git branch --show-current         # must be build/wolf-command-rebuild
git log -1 --oneline
git log --oneline -5 | head -5    # confirm publish-gate lineage near f833f37
```

### Path discovery (required)

```bash
# Where does content-2.0.html live, and how is it served on :8788?
ls -la content-2.0.html dashboards/content-2.0.html 2>/dev/null || true
rg -n "content-2.0|habitat-operator|\.html" serve_beta.py | head -40
# Place habitat-operator.html on the SAME serve path staff already use for Beta HTML.
# If both root and dashboards/ copies exist, follow the path that :8788 actually serves
# (snapshot historically remapped / → /content-2.0.html at ROOT — verify live).
```

### API discovery (required)

```bash
rg -n "submit-for-approval|publish-gate|/api/planner/approve|/api/planner/reject|me/permissions|core/approvals" \
  serve_beta.py scripts/ tests/ 2>/dev/null | head -80
```

Confirm live shapes for:

| Method | Path |
|--------|------|
| GET | `/api/planner?brand=habitat` |
| POST | `/api/planner/save` |
| POST | `/api/planner/submit-for-approval` `{id}` |
| POST | `/api/planner/approve` `{id, approve:true}` |
| GET | `/api/planner/publish-gate?id=` |
| POST | `/api/core/approvals/{id}/reject` (or live reject path) |
| GET | `/api/core/me/permissions` (or live who-am-I) |

**Identity:** Cloudflare Access JWT → real Person. **No spoof fields.** Reuse existing CF Access cookie path used by other Beta pages.

---

## Goal (bounded)

Ship a **minimal Habitat human operator UI** so real staff can run the Core publish-gate flow **without API/curl**.

### Must ship

1. **Page:** `habitat-operator.html` at the correct serve path for Beta `:8788`.
2. **Mobile-first:** readable on phone; big **Submit** / **Approve** / **Reject** buttons; no horizontal-scroll disaster; **human titles** as primary labels (IDs secondary/small).
3. **Producer view**
   - Pick a Habitat planner item (from `GET /api/planner?brand=habitat`)
   - See what it is (title/caption/script/status/evidence requirement)
   - Edit caption/script if needed via `POST /api/planner/save`
   - **Submit for approval** via `POST /api/planner/submit-for-approval`
   - Clear waiting / “submitted” state after success
4. **Approver view**
   - List items needing approval
   - Show producer, content, evidence
   - **Approve** via `POST /api/planner/approve` `{id, approve:true}`
   - **Reject** via existing Core approvals reject (and optional thin planner reject — below)
   - Show recorded decision after action
5. **After approve**
   - Button **Run publish gate** → `GET /api/planner/publish-gate?id=`
   - Display result including **`READY_TO_PUBLISH`** when ready
   - Display clearly: **Metricool WRITE DISABLED** (do not enable write)
6. **Who-am-I** banner from `/api/core/me/permissions` or live equivalent
7. **EXIT:0** on success with exact commit message; **EXIT:1** on failure (print reason)

### Optional (only if needed)

- **Thin** `POST /api/planner/reject {id, reason?}` that calls existing Core reject **and** returns slot to Draft/Pending — **only if** reject via Core alone leaves slot status unusable for humans. Do not invent new Core primitives.
- Tiny smoke test file (HTML or py) that does not break `test_habitat_publish_gate.py`.

### Must NOT

- Wire Core gate into `content-2.0.html` / fortnight **plans** (different system)
- Touch Production, wolf-system, `:8787`
- Change Metricool write flags / `.env`
- Add Decision Ledger or new Core primitives beyond optional thin planner reject wrapper
- Spoof person/identity query params
- Use `cursor-agent --trust`
- Push remote

---

## UX sketch (implement, not decorate)

```
[ Habitat Operator · Beta ]
[ You: <name/email from /api/core/me/...> ]

[ Producer | Approver ]   ← simple tabs or two sections

Producer:
  [ Habitat item picker — human title ]
  Status: …
  Caption / script: [editable]
  Evidence: …
  [ Submit for approval ]   ← large
  Waiting: … / Submitted ✓

Approver:
  Items needing approval: …
  Producer: …
  Content + evidence: …
  [ Approve ]  [ Reject ]   ← large
  Decision recorded: …

After Human_Approved (or live approved status):
  [ Run publish gate ]
  Gate: READY_TO_PUBLISH | …
  Metricool: WRITE DISABLED
```

Use credentials/cookies already present for Beta pages (`fetch` with `credentials: 'same-origin'` or established pattern). Surface API errors in plain language.

---

## Implementation notes

- Prefer one self-contained HTML page with modest inline JS (match existing Beta style if thin CSS helpers exist — do not rebuild design system).
- Brand filter fixed to Habitat for this page (`brand=habitat`).
- Status strings: use **live** enum from gate commit (`f833f37`); do not invent from stale snapshots.
- After submit/approve/reject/gate: refetch slot or use response body so UI state matches server.
- Reject reason: optional text field if Core/planner reject accepts `reason`.

---

## Tests

```bash
# Do not break existing gate tests
python3 -m pytest tests/test_habitat_publish_gate.py -q   # or project’s established runner path
# If you add a tiny smoke test, name it clearly (e.g. tests/test_habitat_operator_smoke.py)
# and keep it optional / non-flaky without CF Access in CI if needed.
```

---

## Commit + EXIT

```bash
cd /Users/wolfterminal/beta-os
git add habitat-operator.html dashboards/habitat-operator.html \
  serve_beta.py scripts/ tests/ docs/ 2>/dev/null || true
# Stage only files you actually changed for this slice
git status -sb
git commit -m "feat(content): habitat human operator UI for core publish gate"
git status -sb   # CLEAN of this slice
echo "EXIT:0"
```

On any hard failure after attempting the work: print actionable reason and `EXIT:1`.

Append a short `## Build record` to this mission file (or `state/build-factory/`) with: HEAD after commit, files touched, whether thin reject was added, serve URL path (e.g. `http://localhost:8788/habitat-operator.html`).

---

## Done criteria checklist

- [x] Page served on Beta `:8788` at discovered path
- [x] Producer can submit-for-approval without curl
- [x] Approver can approve/reject and see decision
- [x] Publish gate button shows READY_TO_PUBLISH + Metricool WRITE DISABLED
- [x] Who-am-I works via CF Access cookie path
- [x] `test_habitat_publish_gate.py` still passes
- [x] Exact commit message; no Production / Metricool write / plans wiring
- [x] EXIT:0

---

## Build record

- **Factory run:** `BF-habitat-human-ui-20260917`
- **HEAD:** `feat(content): habitat human operator UI for core publish gate` on `build/wolf-command-rebuild` (see `git log -1 --oneline` after pull of this commit)
- **Files touched:**
  - `dashboards/habitat-operator.html` (new)
  - `scripts/tests/test_habitat_operator_smoke.py` (new)
  - `state/build-claims/2026-09-17.json` (claim `habitat-operator-ui-021`)
  - `docs/deliveries/CURSOR-MISSION-HABITAT-HUMAN-OPERATOR-UI-2026-09-17.md` (this record)
- **Thin `POST /api/planner/reject`:** **not added** — Core `POST /api/core/approvals/{id}/reject` leaves slot usable (submit does not stick status; re-submit works)
- **Serve URL:** `http://localhost:8788/habitat-operator.html` (static from `dashboards/` via `serve_beta` `directory=DASHBOARDS`)
- **Tests:** `test_habitat_operator_smoke.py` 14/0; `test_habitat_publish_gate.py` 51/0
- **Not touched:** `serve_beta.py` (Haikal dirty hunks left unstaged), Metricool write / `.env`, Production, plans / `content-2.0.html`
