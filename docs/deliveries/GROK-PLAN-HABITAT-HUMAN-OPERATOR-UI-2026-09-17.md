# GROK PLAN — Habitat human operator UI (Core publish gate)

- **Date:** 2026-09-17 (WITA / Asia/Makassar UTC+8)
- **Author:** Grok (Peaches executor) — plan + Cursor mission only; **no app code**
- **Lane:** Mac Beta `/Users/wolfterminal/beta-os` on **:8788** only
- **Branch:** `build/wolf-command-rebuild`
- **machineId:** `36d8fa4b-2d58-4983-b227-e5bfa5495e78` (Wolfs-Mac-Studio)
- **Factory run:** `BF-habitat-human-ui-20260917`
- **Cursor mission:** `docs/deliveries/CURSOR-MISSION-HABITAT-HUMAN-OPERATOR-UI-2026-09-17.md`
- **Commit (exact):** `feat(content): habitat human operator UI for core publish gate`

---

## Why

Habitat Core publish gate already shipped (`f833f37` / review `2887397`). APIs exist. **No HTML calls `submit-for-approval`**, so real staff cannot commission the flow without curl/API. This slice is a **minimal human operator UI** only.

## In scope

1. New page `habitat-operator.html` (path: match live serve pattern — see mission; root has `content-2.0.html` and may also have `dashboards/content-2.0.html`).
2. Producer view: pick Habitat item → see content → edit caption/script if needed → evidence requirement → **Submit for approval** → clear waiting state.
3. Approver view: list needing approval → show producer + content/evidence → **Approve** / **Reject** → show recorded decision.
4. After approve: **Run publish gate** → show `READY_TO_PUBLISH` + **Metricool WRITE DISABLED**.
5. Auth: existing CF Access cookie path; who-am-I from `/api/core/me/permissions` (or live equivalent).
6. Mobile-first; big buttons; human titles (not cryptic IDs as primary label).
7. Optional tiny smoke test; **do not break** `test_habitat_publish_gate.py`.
8. Optional thin `POST /api/planner/reject {id, reason?}` **only if** UX needs slot status reset after Core reject (calls existing Core reject + returns Draft/Pending).

## Out of scope (hard)

- Wire Core gate into `content-2.0.html` / fortnight **plans** (different system)
- Metricool write enable / Production / `.env` Metricool flags
- wolf-system / `:8787`
- New Core primitives / Decision Ledger
- Spoof identity fields (identity = CF Access JWT → real Person only)
- `--trust` on cursor-agent
- Remote push

## Existing APIs (do not reinvent)

| Method | Path | Role |
|--------|------|------|
| GET | `/api/planner?brand=habitat` | Week slots |
| POST | `/api/planner/save` | Edit caption/script fields |
| POST | `/api/planner/submit-for-approval` `{id}` | Producer submit |
| POST | `/api/planner/approve` `{id, approve:true}` | Approver approve |
| GET | `/api/planner/publish-gate?id=` | Gate check after approve |
| POST | `/api/core/approvals/{id}/reject` | Reject (existing) |
| GET | `/api/core/me/permissions` (or live equiv.) | Who-am-I |

## Success

- Staff can run full Habitat Core publish-gate path in browser on Beta `:8788` without curl.
- Metricool remains WRITE DISABLED; gate surfaces that clearly.
- One clean commit with exact message; EXIT:0.

## Risks / notes

- Live tree may place HTML at root and/or `dashboards/` — Cursor must match **serve** path, not guess.
- Reject UX: prefer existing Core reject; add thin planner reject wrapper only if slot status otherwise stuck for humans.
- Stale box snapshots of `serve_beta.py` predate `submit-for-approval` — Cursor must read **live** Mac tree after `f833f37`.
