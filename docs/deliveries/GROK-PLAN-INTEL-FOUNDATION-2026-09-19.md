# GROK PLAN — Intelligence foundation (CAP-INTEL-01 v1) — 2026-09-19

## Class
NEW CAPABILITY (bounded) — CAP-INTEL-01 Orchestration / Reasoning Surface **BUILT** bar only.
Not PROVEN. No ledger credit invent beyond honest SPECIFIED→BUILT with evidence. No score gaming.

## Defect / gap
CAP-INTEL-01 remains SPECIFIED: “agent army exists but not one institutional WI.”
Primitives already exist and are PROVEN/live: Authorised Knowledge Resolver, Decision Memory, Knowledge Resolution Path, blocker_explain on Needs You / Uma Issues.
Missing: one thin orchestration entry that composes DATA→TOOLS→REASONING→SYNTHESIS→HUMAN without a new agent zoo.

## Lane / bound
- Mission: `owner-autonomous-20260919`
- Lane: `intel-foundation`
- Bound: `beta-intelligence-foundation`
- CR track: `CR-85ef88d8e1da110c` (CAP-INTEL-01 SPECIFIED → resolve only when BUILT evidenced)

## Build (Beta only)

### 1) Core primitive `scripts/core/intel_orchestration.py`
Single function (name flexible):

`orchestrate_institutional_question(question, scope, actor_context=None, work_item_id=None) -> dict`

Pipeline (deterministic; no LLM-as-evidence; no chain-of-thought):
1. **DATA** — normalise scope; optional Work Item load via `work_items.get_work_item` if id given (fail-closed if missing).
2. **TOOLS** — call existing `knowledge_resolution.resolve_question` (which already composes AKR + Decision Memory). Optional `blocker_explain.explain_operating_blocker` when `kind` present in context.
3. **REASONING** — map resolution status to a fixed enum outcome (AUTHORISED / OWNER_DECISION / CONFLICTED / NOT_FOUND / UNKNOWN / NEEDS_HUMAN). No free-text model rationale.
4. **SYNTHESIS** — one human sentence `summary` + structured `steps[]` naming which tools ran + provenance labels only.
5. **HUMAN** — `next_human_action` one of: NONE | NEEDS_MATT | NEEDS_STAFF | NEEDS_POLICY | NEEDS_EXTERNAL_ACCESS | REVIEW_CONFLICT (from blocker classification or CONFLICTED).

Honesty flags required (never claim Cloudflare JWT auth; never invent authority).

### 2) Read-only Beta API
Add GET (or POST JSON) under Beta serve `:8788` only, e.g. `/api/intel/orchestrate` (Owner/dev subject). Returns the orchestration dict. Anon → 403. No Production `:8787` mutation.

### 3) Thin Owner surface
Minimal panel on `/progress` **or** a small delivery page under `/deliveries/` showing one live orchestration sample (fixed demo question scoped BZG/Uma or Owner). Prefer extending progress if cheap; else delivery HTML is fine. Must show: summary, status, provenance labels, next_human_action. No agent chat UI.

### 4) Evidence + CR
- Tests: new `scripts/tests/test_intel_orchestration.py` (happy path, NOT_FOUND, CONFLICTED fixture if available, anon 403, WIP untouched).
- Keep existing intel/blocker/knowledge tests green.
- On prove: update Model C assessment for CAP-INTEL-01 to **BUILT** with evidence bind doc (commit + tests). Do **not** write PROVEN. Do **not** change SYSTEM numeric credits table. Do **not** hard-code dashboard %.
- Resolve Completion Register `CR-85ef88d8e1da110c` only with resolution_evidence = commit + test file. Leave other CR rows alone.
- Add build-claim row like prior factory claims.

### 5) Preserve / refuse
- Preserve WIP four: `migrate_phase2_6_team_readiness.py`, `phase26_team.py`, `skills/__init__.py`, `wolf_intelligence.py` — leave dirty, never stage.
- Do **not** edit `wolf_intelligence.py` (WIP). New module only.
- No Production. No finance/HR lanes. No Alchemist writes. No new helper agents.

## Prove bar
- Unit/API tests PASS with FAIL=0 for new suite; prior knowledge/blocker suites still green.
- Anon orchestrate → 403; authorised sample → 200 with required keys.
- CAP-INTEL-01 ledger state BUILT (not PROVEN); CR-85ef88d8e1da110c RESOLVED with evidence.
- WIP four still unstaged.

## Out of scope
CAP-INTEL-05 learning loop, chat agents, PROVEN promotion, Production, Cloudflare JWT, score gaming, Devi commissioning, finance/HR.
