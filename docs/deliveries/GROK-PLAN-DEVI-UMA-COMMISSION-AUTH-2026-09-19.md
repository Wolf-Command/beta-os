# GROK PLAN — Devi Uma commission auth gate + ops-lead RBAC

- **Date:** 2026-09-19 (WITA / Asia/Makassar UTC+8)
- **Author:** Grok (Peaches executor) — plan + Cursor mission only; **Cursor writes app code**
- **Class:** **NEW CAPABILITY**
- **Lane:** Mac Beta `/Users/wolfterminal/beta-os` on **:8788** only
- **Branch:** `build/wolf-command-rebuild` (verify live)
- **machineId:** `36d8fa4b-2d58-4983-b227-e5bfa5495e78` (Wolfs-Mac-Studio)
- **Factory run / slice:** `BF-devi-uma-commission-auth-20260919`
- **Cursor mission / prompt:** `docs/deliveries/CURSOR-MISSION-DEVI-UMA-COMMISSION-AUTH-2026-09-19.md`  
  also mirrored at `state/build-factory/cursor-devi-uma-commission-auth.prompt.txt`
- **Related (done separately):** end `SCOPE-BZG-ENTITY` on `ASG-DEVI-HFB-UMA-1` — see `DEVI-SCOPE-NARROW-PROOF-2026-09-19.md`

---

## Why

Devi (PERS-DEVI / AUTH-DEVI-EMAIL `deviputu236@gmail.com`) is assigned ACTIVE on ROLE-BZG-HFB / POS-BZG-HFB-UMA-1 with Uma scope. Uma Today / Issues / History / Petty APIs under `/api/bzg/uma-blu/*` currently have **no** `_resolve_identity` / `_require_permission` once past Cloudflare — open. Progress is Owner-only — Devi must never get it. Payment / closer / float invent must stay fail-closed. Entity-wide scope is being ended separately; this slice gates APIs + optional ops-lead display alias.

## Approved scope (bounded)

1. Gate **ALL** `/api/bzg/uma-blu/*` GET/POST with identity + permission **fail-closed** (reuse `_require_permission` / prefer existing codes `venue.close.read` or `work.read` as appropriate — **do NOT invent** `bzg.pr.payment_approve` live).
2. Ensure payment / closer / float invent stay fail-closed (no new grants to Devi).
3. Prefer Core RBAC: either keep `ROLE-BZG-HFB` with Uma scope only **OR** add `ROLE-BZG-UMA-OPS-LEAD` as alias display **"UMA BLU OPS LEAD"** with same non-monetary ops perms (`work.read`, `venue.close.read`, `evidence.*`) — **NO** `payment_approve`, **NO** closer submit grants to Devi. Keep `ROLE-BZG-CLOSER` at 0 people.
4. Scope isolation prove: person without `SCOPE-BZG-UMA` → 403 on Uma APIs; Devi with Uma scope → 200 for allowed reads.
5. Mobile: viewport already max-width 480 — only fix if broken; phone layout smoke on deployed Beta.
6. Tests for auth deny/allow.
7. **Beta only.** No Production. No Progress access for Devi.
8. Do **NOT** mark HUMAN COMMISSIONED.

## Out of scope (hard)

- Cloudflare Access Include edits (Matt adds email himself; Peaches MUST NOT widen Includes)
- Production / `:8787` / wolf-system
- Payment approve / closer submit / float invent grants
- Progress board/API access for Devi
- Alchemist → Beta history import as canonical
- ESB / ClickUp / Telegram / email writes
- `--trust` on cursor-agent
- Remote push
- Staging the four WIP files: `scripts/migrations/migrate_phase2_6_team_readiness.py`, `scripts/phase26_team.py`, `scripts/skills/__init__.py`, `scripts/wolf_intelligence.py` — **never git add these**
- Never `git add .`

## Success

- All `/api/bzg/uma-blu/*` fail-closed without identity/permission.
- Devi + SCOPE-BZG-UMA can read allowed Uma ops endpoints; without Uma scope → 403.
- Payment/closer/float invent remain denied for Devi.
- Progress remains Owner-only.
- Tests green for deny/allow.
- Factory stage advances only to WAITING_CURSOR / CURSOR_IMPLEMENTING as appropriate; **HUMAN_COMMISSIONING_STATUS stays NOT_DONE**.
- EXIT: DONE or EXIT: BLOCKED with reason.

## Risks / notes

- Live `serve_beta.py` on Mac may differ from box snapshots — Cursor must read **live** tree.
- Prefer existing permission codes; do not invent monetary codes.
- If ops-lead role is created, wire Devi assignment carefully without widening scopes beyond SCOPE-BZG-UMA.
