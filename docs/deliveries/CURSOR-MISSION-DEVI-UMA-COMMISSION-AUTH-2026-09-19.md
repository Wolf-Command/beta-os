# CURSOR MISSION — Devi Uma commission auth gate + ops-lead RBAC

**Date:** 2026-09-19 (WITA)  
**Author:** Grok (Peaches executor) — governance brief; **Cursor writes app code**  
**Lane:** Mac Beta `/Users/wolfterminal/beta-os/` on **:8788** only  
**Branch:** `build/wolf-command-rebuild`  
**machineId:** `36d8fa4b-2d58-4983-b227-e5bfa5495e78`  
**Factory run:** `BF-devi-uma-commission-auth-20260919`  
**Class:** NEW CAPABILITY  
**Remote / Production:** **NO** push · **NO** `:8787` · **NO** wolf-system · **NO** CF Include edits · **NO** `--trust` · **NO** HUMAN COMMISSIONED mark

---

## Already resolved (do not reinvent)

- Person `PERS-DEVI` ACTIVE
- AuthIdentity `AUTH-DEVI-EMAIL` email=`deviputu236@gmail.com` (HR-authorised)
- Assignment `ASG-DEVI-HFB-UMA-1` ACTIVE on `ROLE-BZG-HFB` / `POS-BZG-HFB-UMA-1`
- Scopes: `SCOPE-BZG-UMA` ACTIVE; `SCOPE-BZG-ENTITY` **must already be ENDED** (or end it first via `scripts/fix_end_devi_entity_scope.py --apply` if proof file says not applied)
- `ROLE-BZG-CLOSER` has 0 people — keep that
- Progress = Owner-only — Devi must never get it

## Read first (live Mac tree)

- `docs/BUILD-READ-ME-FIRST.md` (if present)
- `docs/RULE-Local-Cursor-Build-Path-2026-09-17.md`
- `docs/RULE-Beta-Construction-Production-Sacred-2026-09-16.md`
- `docs/deliveries/GROK-PLAN-DEVI-UMA-COMMISSION-AUTH-2026-09-19.md`
- `docs/deliveries/DEVI-SCOPE-NARROW-PROOF-2026-09-19.md`
- Live `scripts/serve_beta.py`: find `/api/bzg/uma-blu/*`, `_resolve_identity`, `_require_permission`, Progress gates
- Core RBAC helpers for roles/scopes/permissions

## Phase 0 — Preflight (STOP if any fail)

```bash
cd /Users/wolfterminal/beta-os
export PATH="/Users/wolfterminal/.local/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"
hostname   # expect Wolfs-Mac-Studio.local
git status -sb
# NEVER stage these WIP files:
git status --short -- scripts/migrations/migrate_phase2_6_team_readiness.py scripts/phase26_team.py scripts/skills/__init__.py scripts/wolf_intelligence.py
git branch --show-current
```

Prove Uma scope narrow:

```bash
sqlite3 catalog/content_library.sqlite "
SELECT assignment_id, scope_id, status, end_at
FROM org_assignment_scopes
WHERE assignment_id='ASG-DEVI-HFB-UMA-1' AND status='ACTIVE';
"
# must be ONLY SCOPE-BZG-UMA
```

## Implement

1. Gate **all** `/api/bzg/uma-blu/*` GET/POST with `_resolve_identity` + `_require_permission` fail-closed.
2. Prefer existing codes: `work.read` and/or `venue.close.read` (+ `evidence.*` if already used). Do **not** invent `bzg.pr.payment_approve`.
3. Payment / closer submit / float invent endpoints: remain fail-closed; no Devi grants.
4. RBAC: keep `ROLE-BZG-HFB` + Uma scope **or** add `ROLE-BZG-UMA-OPS-LEAD` display **"UMA BLU OPS LEAD"** with same non-monetary ops perms only.
5. Tests: deny (no identity / no Uma scope → 403), allow (Devi + Uma scope → 200 on allowed reads).
6. Mobile: only fix if viewport/phone layout broken (max-width 480 already).
7. **No** Progress access paths for Devi.
8. Beta only. One clean commit if changes land — **never `git add .`**; never stage the four WIP files.

## Commit message (if you commit)

`feat(uma): fail-closed auth on Uma Blu APIs for Devi ops-lead commissioning`

## Exit convention

Print exactly one of:

- `EXIT: DONE` — gates + tests + Beta-only constraints met; HUMAN_COMMISSIONING still NOT_DONE
- `EXIT: BLOCKED` — followed by one short reason

Do not mark HUMAN COMMISSIONED. Do not edit Cloudflare Access Includes.
