# Wolf Intelligence — Tomorrow Morning Handoff
**Generated:** 2026-09-14 ~22:49 WITA (UTC+8) / overnight read-only mission  
**Companion:** `/tmp/WOLF-INTELLIGENCE-MASTER-ARCHITECTURE.md`

## 1. Decisions already made (from mission)

- Read-only overnight; no Beta/Obsidian/agent/DB/CF/:8787 mutations  
- Wolf owns memory; models consume  
- Company-secret: no providers/agent names in Beta UI  
- Human creative authority; learn from deviations  
- Preserve AI proposal → human edit → approved → produced → published → Metricool → lessons as **separate** records  
- Memory governance types + PROPOSED→APPROVED + ACTIVE/SUPERSEDED/EXPIRED/REJECTED  
- Prefer DATA→TOOLS→REASONING→SYNTHESIS→HUMAN  
- Metricool is DATA not an agent  
- Learning Library = URL quarantine  
- MATCH/FILM asset statuses  
- `can_create_plan` permission (not hardcoded names)  
- Server-side gates for irreversible actions  
- Provider-independent router + benchmarking  
- Admin observability vs user-facing **Wolf Intelligence**

## 2. Architecture recommend

Beta OS Content Intelligence core: typed Wolf memory + composable skills + Build Next Plan orchestrator.  
Collapse Week2 Grok content personas (Muse/Indigo/Velvet/Frame/Reel/Scout-content) into **3–5 skills** behind one synthesizer. Keep Peaches + corporate/ops Grok army. Metricool connector. No new content agents.

## 3. First milestone

**Phase 1:** Schema for `memory_items` + `plan_revisions` + `can_create_plan`; Habitat brand memory import (approved); Build Next Plan dry-run Working Draft with Strategy+cards+FILM statuses; preserve proposal vs edit; user checklist labeled Wolf Intelligence.

## 4. Exact first tasks

1. Anvil/Cursor brief: ADD-only Beta schema migration for revisions/memory/permissions (do not touch :8787)  
2. Seed permission config for plan creators (Amanda/Haikal/Misa as data)  
3. Implement dry orchestrator checklist endpoint  
4. Wire card asset_status enum  
5. Hide provider strings from content-2.0.html (admin-only later)  
6. Draft Habitat memory candidates from `/tmp/wolf-content-plans-for-chatgpt/` for human approve  

## 5. Files/components affected (Phase 1)

- `beta-os/scripts/serve_beta.py`  
- `beta-os/scripts/llm_orchestrator.py` (router stub)  
- `beta-os/catalog/content_library.sqlite` (schema ADD)  
- `beta-os/dashboards/content-2.0.html`  
- New: `beta-os/scripts/skills/*` (dry)  
- **Not:** wolf-system serve.py :8787, Obsidian vault, Grok profile.json, Cloudflare  

## 6. Things NOT to touch

- Legacy **:8787** / wolf-system live boards apply  
- Grok agent create/delete/memory writes  
- Obsidian vault writes  
- Metricool **write**/schedule  
- Remotion (parallel track; not Phase 1 blocker)  
- Paid X API  
- Cloudflare Access seats/tokens  

## 7. Unresolved decisions

See Master §AL (Metricool READ timing, agent dormancy, auth model, Remotion vs ffmpeg, memory RULE approvers, Obsidian sync direction, X paid later).  
Supplied memory-engineering / grok-workflow files: **MISSING → UNKNOWN — NEEDS VERIFICATION**.

## 8. Acceptance criteria

- GET `/api/health` still ok; :8787 never called  
- Authorized subject with `can_create_plan` can generate Working Draft for Habitat  
- AI proposal row retained after human edit  
- UI shows Wolf Intelligence checklist; no provider/agent codenames in user HTML  
- Card can be FILM without attached media  
- No publish side effects  
- Memory RULE cannot become ACTIVE without approval state  

## Inventory snapshot

- Grok agents discovered: **37** (see Master §B)  
- After consolidation (Content Intelligence logical set): **Wolf Intelligence orchestrator + 3–5 skills**; Week2 personas REDEFINE; ops army KEEP  
- Biggest finding: Week2 content lane is agent sprawl over a missing Beta memory/skills substrate  
- Biggest risk: collapsing learning-loop records + unauthenticated mutate when keys go live  
- Confirmation: **no systems modified**; **:8787 untouched**
