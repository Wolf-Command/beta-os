# Wolf Command — Content Intelligence Master Architecture
**Classification:** Company-secret Wolf Command IP (internal). Do not expose providers/agent names in Beta UI.  
**Generated:** 2026-09-14 ~22:49 WITA (UTC+8) / overnight read-only mission  
**Mode:** READ-ONLY audit + design. **No systems modified.** **:8787 untouched.**  
**Evidence roots:** Box `/home/box/agent-data/`; Mac `beta-os/` GET-only; `/tmp/wolf-content-plans-for-chatgpt/`; prior `/tmp/WOLF-BETA-OS-AUDIT-2026-09-14.md`.  
**Supplied memory-engineering / grok-workflow docs:** **UNKNOWN — NEEDS VERIFICATION** (searched `/tmp`, workspace, attachments, agent-data — not found on disk). Design below uses principles stated in Matthew's mission prompt itself.

---

## A. Executive Recommendation

**Build Wolf Intelligence as a Beta OS–owned memory + skills + gated workflow system — not as another swarm of Grok agents.**

CURRENT STATE: 37 named Grok agents with overlapping Week-2 content roles (Muse→Indigo→Velvet→Frame→Reel→Ink) plus Peaches routing; Obsidian vault holds brand/plans; Beta `:8788` has planner/staging/LLM dry-run + server-side approval gates but **no Remotion**, empty media library, Metricool stub; durable memory is thin markdown profiles/logs, not governed typed memory.

TARGET STATE: One Content Intelligence loop in Beta OS: **DATA → TOOLS → 3–5 specialist reasoning skills → SYNTHESIS → HUMAN**, with Wolf-owned memory (typed, versioned, approved), separate records for AI proposal / human edit / approved / produced / published / Metricool / lessons, `can_create_plan` permission, Metricool as **data connector** (not an agent), Learning Library URL quarantine, MATCH/FILM asset statuses, provider-independent router + benchmarks, user-facing label **"Wolf Intelligence"** (admin sees providers).

WHY: Agent sprawl duplicates work already needed as tools/queries; models must consume Wolf memory they do not own; human creative authority on-site is the product; differences across the learning loop are proprietary IP.

DATA REQUIRED: Brand kits from Obsidian export; Metricool history once API wired; asset index (NAS/library_v2); decision log; prior fortnight plans; Learning Library (empty at start).

SYSTEM OWNER: Peaches (ops CoS) + Cursor/Anvil for Beta code; Matthew for irreversible go-live; Amanda/Haikal/Misa as plan creators (via permission, not hardcoded names).

AUTOMATIC OR HUMAN-GATED: Overnight prep AUTOMATIC (drafts only). Publish / spend / live automation / memory RULE promotion HUMAN-GATED server-side.

IMPLEMENTATION DEPENDENCIES: Beta schema extensions; memory store; Metricool read client; brand memory import; permission bits; no :8787 coupling.

RISKS: Collapsing proposal+approved into one row destroys learning; promoting chat noise into RULES; exposing providers in UI; hardcoding staff names; touching :8787.

ACCEPTANCE TEST: Authorized user clicks Build Next Plan for Habitat → status checklist shows Wolf Intelligence steps → Working Draft with Strategy + cards → edit preserved as separate revision → approve does not publish → no provider/agent names in UI HTML.

**First milestone (AH):** Memory schema + plan revision records + Build Next Plan skeleton (dry skills, no paid calls) on Beta — still no Remotion required for intelligence loop.

---

## B. Existing Grok Agent Inventory

**Source:** `ls /home/box/agent-data/agents/` + each `profile.json` (37 with profiles).  
**OpenClaw (Mac):** `~/.openclaw/agents/main/` only (session store). **No parallel named Muse/Velvet OpenClaw agents.** OpenClaw = infra/bots/workspace, not the Grok army.

| Name | ID | One-line job | Rec | Evidence |
|---|---|---|---|---|
| Peaches - Chief of Staff | 3e37ef74-…d1d2 | Route army, grill, enforce Standing Rules | **KEEP** | CoS charter; active routing |
| Muse - Content Strategy | 6a86834f-…d314 | DRAFT weekly briefs ≥14 days ahead | **REDEFINE**→ strategy skill | Week2 OWN briefs; activeAgentId was Muse |
| Scout - Research | cea40b1f-…dfb48 | Free-web research; SCOUT one-pagers | **REDEFINE**→ web/X research skills | Not content-only; overlaps trend lanes |
| Indigo - Library | 5e96b19c-…ad2eb | MATCH NAS clips to Muse briefs | **REDEFINE**→ library tool + matcher skill | MATCH SLA; no invent clips |
| Velvet - Production | 21f31fbc-…5c609 | DRAFT production packs from briefs+MATCH | **MERGE** w/ Reel → production skill | OFF; MATCH only; no Metricool write |
| Frame - Creative QC | 2fe1870c-…9fa46 | RED/AMBER/GREEN vs brand kits | **REDEFINE**→ brand QC skill/validator | QC reports to Muse/Velvet |
| Reel - Edit Brief | 31684f5f-…0b669 | Shot cards / Resolve notes from packs | **MERGE**→ production skill | Never publish |
| Ink - Graphic Kit | 7b6b7054-…aaeb8b | Steward Canva/visual kits | **KEEP** (narrow) or skill later | Kits ≠ planning; Amanda/Tisa on Canva |
| Rouge - Advertising | d9b2e540-…cdca9 | LEARN ads; never spend | **KEEP** (ops) | Not content planner |
| Prism - Demand | 5f88d598-…a60eb1 | LEARN CAC/LTV definitions | **KEEP** (ops) | Measurement ≠ creative |
| Echo - Reputation | 3b87e593-…c45 | Reviews/crisis prep drafts | **KEEP** (ops) | Separate from calendar |
| Gauge - Seat Prove | 44b1b49f-…5249b | Prove boards after live-apply | **KEEP** (Tier1) | Isolation prove scripts |
| Vesper - Devil's Advocate | 2a057c4f-…fc8e | RED scorecard / challenge | **KEEP** | Grill standing |
| Pulse - Self-Healing | 2f05b355-…4116 | Doctor :8787/pipe/NAS flags | **KEEP** | Note: Pulse watches :8787 — Content Intel must not |
| Link - Mac Reachability | 3c135af5-…0eb1 | Mac Studio pipe | **KEEP** | Infra |
| Anvil - Build Briefs | b0f2f4ee-…7321 | Cursor cloud briefs | **KEEP** | Code path |
| Cipher - Security | c6ccbf36-…c36 | CF Access LEARN | **KEEP** | Security |
| Breach - Red Team | 29f8d87f-…1815 | Adversarial probes | **KEEP** | Separate from Cipher |
| Phoenix - DR | ebb375c4-…d63e3 | Reimport package | **KEEP** | DR |
| Sterling - Finance | 96e48ce1-…8027 | LEARN money | **KEEP** | Finance |
| Sable - Shareholder Reports | 0c13c857-…e3b8 | DRAFT HTML packs | **KEEP** | Reports |
| Saffron - Procurement | 2eee6bb1-…56c36 | Alchemist payment diagnose | **KEEP** | Procurement |
| Onyx - Legal | 9acdfbaa-…a79d | LEARN legal drafts | **KEEP** | Legal |
| Willow - People | eddf21f5-…892a | LEARN HR read-only | **KEEP** | People |
| Helm - Business Cadence | d87337ad-…2a934 | 12WY coach packs | **KEEP** | Cadence |
| Vault - Exit Data Room | 2df38f1e-…b6ede | VDR trees | **KEEP** | Exit |
| Coral - Hotel Ops | d227b14f-…2fa86 | AMG ops LEARN | **KEEP** | Ops |
| Roux - Uma Blu Ops | 8ad95efd-…ac579a | BZG cafe LEARN | **KEEP** | Ops |
| Cascade - Hotel Revenue | eb9bab2d-…ddc45 | Yield LEARN | **KEEP** | Revenue |
| Haven - Guest Experience | 82299df5-…92b682 | Cross-co feel LEARN | **KEEP** | Experience |
| Meridian - Client Success | a81b69a7-…f5938 | GGV client cadence | **KEEP** | Client |
| Ivy - Leads | 73653793-…3710bc | CRM LEARN | **KEEP** | Leads |
| Flint - TTC Quant | 4dbfe6a0-…d7cc | Trading paper only | **KEEP** | Trading → Matthew |
| Codex - Playbooks | 67856eb1-…fbb9a | SOP standards | **KEEP** | Playbooks |
| Briar - Staff Training | 7dcdec66-…d12e | Desk micro-training | **KEEP** | Training |
| Inspect - Field Audit | 5e96c764-…42aa1 | Field SOP inspect | **KEEP** | Audit |
| dr eggbot | 2e16ace7-…a9ea | Design new Grok bots | **REDEFINE** | Hold new content bots; prefer skills |

**Count discovered:** 37 Grok agents with `profile.json`.  
**Content Week2 cluster:** Muse, Indigo, Velvet, Frame, Reel, Ink (+ Scout adjacent).

---

## C. Existing Memory Audit

| Store | Location | Durable? | Notes |
|---|---|---|---|
| Agent profile.md | `user-memory/by-agent/<id>/profile.md` | Semi-durable | Peaches/Willow/Flint sample; dated facts |
| Agent log | `…/log/YYYY-MM.md` | Chat-adjacent durable | Append-only dated lines |
| Project memory | `projects/wolf-command-master/memory/` | Durable themes | Constitution, Standing Rules, Week2 start, produce brands |
| Obsidian brand/plans | Export `/tmp/wolf-content-plans-for-chatgpt/` | Canonical Living Docs | Brand sheets, DRAFT plans, FILM lists |
| Grok chat context | Sessions/transcripts | Ephemeral | Must NOT be SoT |
| Beta SQLite | `beta-os/catalog/content_library.sqlite` | Durable but tiny | Smoke planner/assets; no typed memory |
| OpenClaw MEMORY.md | `~/.openclaw/workspace/MEMORY.md` | Mixed/legacy | Not Beta Content Intelligence SoT |

**Durable vs chat:** Standing Rules + brand kits + approved decisions should be durable Wolf memory. Chat threads = evidence sources only until promoted via governance.

**Gap:** No FACT/RULE/OBSERVATION/HYPOTHESIS typing; no PROPOSED→APPROVED; no SUPERSEDED/EXPIRED; no provenance/evidence fields in a shared store.

---

## D. Existing Skills Audit

**Workflows** (`/home/box/agent-data/workflows/`, 46 total). Content-related names:

- `content-calendar-draft`
- `four-blanks-before-brand-work`
- `grill-me`
- `research-deep-dive`
- `x-link-deep-learn`
- `x-signal-daily`
- `weekly-wolf-command-pack`
- `overnight-coder-queue`
- `dashboard-roles`, `dashboard-tile-chevrons`, `dashboard-upgrade-locks`, `standard-dashboard-access`
- `real-estate-scout` (adjacent Scout, not social content)

**Managed/plugin skills:** Platform connector skills (`add-connector`, `learn-from-demonstration`, etc.) — not Content Intelligence skills.

**Missing skills (needed):** Analyze Metricool; Analyze Previous Fortnight; Research Web/X Trends; Analyze Inspiration; Generate Fortnight Strategy/Cards; Check Brand/Claims/Assets; Compare Human Edit; Extract Learning — **none exist as Beta composable skills today.**

---

## E. Agent Dependency Map (Content path)

```
Matthew (gates: post/money/live)
    ↑
Peaches (route, grill, assign)
    ├── Muse (briefs) ──► Indigo (MATCH) ──► Velvet (packs) ──► Reel (edit briefs)
    │                         │                    └──► Frame (QC) ──► Muse/Velvet
    ├── Ink (kits) ─────────────────────────────────────────────► Frame
    ├── Scout (research) ──► specialists / Flint (non-content)
    ├── Rouge / Prism / Echo (ads/demand/reputation LEARN — parallel)
    └── Gauge/Vesper/Pulse/Anvil (system integrity — not creative)
```

Beta path today (separate from Grok handoffs):

```
content-2.0.html → serve_beta.py :8788
  → staging → assets → planner statuses
  → llm_orchestrator (dry_run UI) → llm_logs
  → render STUB; Metricool STUB/gate
```

**Handoff evidence (profiles):** Muse writes briefs → Velvet packs; Indigo MATCH within 24h; Velvet IDLE → Muse/Indigo same-day SLA; Frame flags → Muse/Velvet; Reel consumes Velvet+Muse; nobody posts/Metricool-writes.

---

## F. Duplication / Agent Sprawl

| Overlap | Agents | Better as |
|---|---|---|
| Strategy briefs | Muse + Peaches rewriting | Brand memory + Generate Strategy skill |
| Library match | Indigo | Index query + MATCH tool |
| Production pack + edit brief | Velvet + Reel | One production skill chain |
| Creative QC | Frame + brand_alignment LLM role | Validator skill |
| Research | Scout + x-signal/x-link workflows | Web/X tools + trend skill |
| Ads vs demand vs calendar | Rouge / Prism / Muse | Keep ops LEARN separate; don't twin |

**Sprawl verdict:** Week2 content lane is **agent-shaped orchestration of what should be Beta tools/skills**. Corporate Tier1–4 agents largely **KEEP** (different domains). Do **not** create more content agents via eggbot.

---

## G. Lessons From The Supplied Memory Engineering Material

**UNKNOWN — NEEDS VERIFICATION.** Files matching `memory-engineering` / similar **not found** on disk (`/tmp`, workspace, attachments, agent-data).  

**From mission principles (authoritative substitute):**
- Wolf owns memory; models only consume.
- Do not make Grok/OpenAI/Gemini conversation memory the SoT.
- Typed memories with provenance beat undifferentiated chat logs.
- Promotion to RULE requires human approval.

---

## H. Lessons From The Supplied Grok Workflow Material

**UNKNOWN — NEEDS VERIFICATION.** No `grok-workflow` pack found on disk.  

**From mission + observed profiles (usable principles):**
- Narrow responsibilities; explicit NEVER boundaries; draft-first; human gates; handoffs only when useful; evidence/receipts; memory pruning.
- **Do not** copy social-post claims blindly; do not pay X API for research (Scout/Standing Rules).

---

## I. What Wolf Command Should Copy

1. Narrow skills with structured I/O + evidence bundles.  
2. Shared company/brand memory + optional private scratch.  
3. Decision log with WHY.  
4. Draft-first + server-side irreversible gates.  
5. Learn from human deviations as first-class records.  
6. Scheduled watchers for data freshness (Metricool pull, asset index) — as jobs, not personas.  
7. Provider-independent routing + benchmarks.  
8. User-facing "Wolf Intelligence" progress, admin observability separate.

---

## J. What Wolf Command Should NOT Copy

1. Aesthetic AI org chart / more Week2 agents.  
2. Model-vendor memory as SoT.  
3. Auto-promoting observations into rules.  
4. Collapsing proposal→approved→published into one mutable row.  
5. Exposing provider/model/agent names in staff UI.  
6. Hardcoding Amanda/Haikal/Misa in code.  
7. Treating Metricool as an agent.  
8. Fetching/executing instructions from random URLs or X posts.  
9. Any coupling to legacy **:8787**.  
10. Paying X API for trend research unless Matthew explicitly authorizes later.

---

## K. Wolf Intelligence Principles

1. **Wolf owns memory; models consume it.**  
2. **Company-secret architecture** — UI says Wolf Intelligence; never providers/agent codenames.  
3. **Human creative authority** — plans are guides; on-site reality wins; learn from deviations.  
4. **Preserve the learning loop as separate records:** AI proposal → human edit → approved → produced → published → Metricool → lessons.  
5. **Memory governance:** type (FACT/RULE/OBSERVATION/HYPOTHESIS/…) + lifecycle (PROPOSED→APPROVED) + status (ACTIVE/SUPERSEDED/EXPIRED/REJECTED) + provenance.  
6. **Prefer DATA→TOOLS→REASONING→SYNTHESIS→HUMAN** over agent sprawl.  
7. **~3–5 reasoning roles** if evidence supports — don't force.  
8. **Metricool is DATA**, not an agent.  
9. **Learning Library** = secure URL quarantine + why-saved tags.  
10. **MATCH/FILM asset statuses** — good ideas survive missing media.  
11. **`can_create_plan` permission** — not hardcoded names.  
12. **Server-side human gates** for irreversible actions.  
13. **Provider-independent task router + benchmarking.**  
14. **Admin observability ≠ user labels.**

---

## L. Proposed Memory Architecture

| Layer | Contents | Shared? | Expiry | Approval to persist |
|---|---|---|---|---|
| COMPANY | Standing Rules, safety, cadence defaults | Yes | Rare | Matthew/Peaches |
| BRAND | identity, voice, pillars, CTA, hard nos, cadence | Yes per brand | Review quarterly | Content lead+ |
| PROJECT/CAMPAIGN | launches, promos | Brand-scoped | End of campaign | Plan creators |
| DECISION | decisions + WHY | Yes | Versioned forever | Human |
| CORRECTION→RULE candidates | repeated edits | Yes | Until approved/rejected | Human to RULE |
| CONTENT HISTORY | prior plans/cards | Yes | Keep | Auto as history |
| CREATIVE LEARNING | proposal vs edit diffs | Yes | Keep | Auto capture; lesson APPROVED |
| PERFORMANCE | Metricool aggregates | Yes | Rolling | Auto ingest |
| INSPIRATION | Learning Library items | Yes | Optional | Quarantine then human keep |
| TREND | external signals | Yes | **Short TTL** | Auto as OBSERVATION; never auto RULE |
| PRODUCTION | what was actually shot | Yes | Keep | Human/crew |
| AGENT PRIVATE | scratch only | Private | Short | Never promotes alone |

**Storage target:** Beta OS SQLite (or adjacent) tables — not Grok profile.md as SoT. Obsidian remains Living Docs source for brand prose; Beta holds structured operational memory + sync pointers.

CURRENT STATE: markdown agent memory + Obsidian + tiny Beta DB.  
TARGET STATE: typed Wolf memory store in Beta with provenance.  
WHY / DATA / OWNER / GATING / DEPS / RISKS / ACCEPTANCE: see §A pattern — acceptance = insert PROPOSED observation → cannot affect planner until APPROVED ACTIVE.

---

## M. Memory Governance / Drift Prevention

Every record fields: `id, type, scope, brand_id?, text, source, evidence_refs, confidence, status, approval_state, approved_by?, created_at, expires_at?, supersedes?, version`.

**Types:** FACT | RULE | OBSERVATION | HYPOTHESIS | DECISION | LESSON | INSPIRATION_NOTE | TREND_SIGNAL  

**Approval:** PROPOSED → APPROVED | REJECTED  

**Lifecycle status:** ACTIVE | SUPERSEDED | EXPIRED | REJECTED  

**Never auto-RULE:** single Metricool spike; one human edit; unverified trend; quarantined URL content; anything from untrusted web without evidence bundle.

**Poisoning controls:** require evidence; TTL on TREND; human gate on RULE; Vesper-style challenge on RULE promotions; immutable versions (supersede, don't edit in place).

---

## N. Decision Log Architecture

Table `decision_log`: decision, why, brand/scope, alternatives considered, decided_by, at, links to plan_id/memory_id, status ACTIVE/SUPERSEDED.

Used by Build Next Plan step 2. Human-gated create/edit. Acceptance: decision appears in next plan evidence panel without exposing internal agent names.

---

## O. Human-Edit Learning Architecture

Do **not** overwrite AI proposal.  

Records:
1. `plan_revision` role=`ai_proposal`  
2. `plan_revision` role=`human_edit` (diff JSON)  
3. `plan_revision` role=`human_approved`  
4. `production_record` (what was made)  
5. `publish_record` (what went out)  
6. `performance_record` (Metricool)  
7. `lesson_candidate` → PROPOSED lesson memory  

CURRENT STATE: single planner row mutates status; script_body overwritten.  
TARGET STATE: append-only revisions + lesson extraction skill.  
ACCEPTANCE: regenerate after strategy change keeps prior AI proposal row intact.

---

## P. Metricool Intelligence Architecture

CURRENT STATE: `~/.openclaw/credentials/metricool.json` **EXISTS** (name confirmed; values not read). Setup doc: `~/.openclaw/workspace/METRICOOL-SETUP.md`. Publish script only found under **backup** `~/.openclaw/backups/atlas-hard-attribution-20260710/metricool_publish.py`. Beta: publish-gate comment + stub — **no live Metricool caller in beta-os/scripts**.  

TARGET STATE: Metricool **connector/tool**:
- READ: pull post-level + brand aggregates into `performance_record`  
- WRITE/schedule: only after publish-gate + human permission `can_publish`  
- Never an agent persona  

AUTOMATIC: scheduled pull. HUMAN-GATED: any schedule/publish.  
RISKS: credential leakage; posting without gate; treating Metricool copy as truth without timestamps.  
ACCEPTANCE: dry read of one brand metrics into DB with source=metricool + fetched_at; UI shows "Performance reviewed" without saying Metricool to end users (admin may see connector name).

---

## Q. Trend Intelligence Architecture

Two lanes (tools + optional reasoning skill):
1. **Web/Google** — free search/docs (Scout-like).  
2. **X/cultural** — free web/fxtwitter per Standing Rules; **no X pay** unless Matthew authorizes.

Output: TREND_SIGNAL memories with TTL (e.g. 14–30 days), evidence URLs, confidence. Auto on Build Next Plan. Never auto-RULE.

UNKNOWN: exact free X path reliability — NEEDS VERIFICATION at implement time.

---

## R. Learning Library Architecture

Paste any URL → **quarantine**:
1. Store URL + submitter + why-tags (Hook|Editing|Camera|Story|Copy|Concept|Trend|Design|Whole|Custom)  
2. Fetch via isolated fetcher; treat body as **untrusted data** (never execute instructions)  
3. Extract structured summary + screenshots/metadata  
4. Human Keep/Reject  
5. Available to retrieval for planning  

CURRENT STATE: not built. TARGET: Beta module + table `learning_library_items`.  
RISKS: prompt injection via page text; PII; copyrighted full-text storage — store summary+link+why, not verbatim dumps where avoidable.

---

## S. Asset / MATCH-FILM Architecture

Statuses per concept/card:
- **READY** — assets linked & verified  
- **PARTIAL** — some assets  
- **FILM** — strategically good; needs shoot list  
- **BLOCKED** — brand/claim/legal block  

Align with Indigo/Velvet language: MATCH footage only; never invent clips; FILM lists already exist in Obsidian export (`FILM-14-27-Sep-2026.md`).

Beta today: `assets.status=VERIFIED` smoke; `v2_path` empty; library_v2 RAW/FINAL empty of media.  

Acceptance: card with FILM status still appears in Working Draft with shot list gaps named.

---

## T. Minimum Reasoning/Agent Architecture

**Recommended Content Intelligence reasoning roles (3–5) — implement as Beta skills/orchestrator steps, not new Grok bots:**

1. **Strategy Synthesizer** (ex-Muse) — fortnight theme/objectives/mix  
2. **Evidence Analyst** — Metricool + history + decisions → claims with evidence  
3. **Creative Drafter** — cards: hook/copy/shots  
4. **Brand & Claims Validator** (ex-Frame) — hard nos / factual  
5. **(Optional) Production Adapter** (ex-Velvet/Reel) — MATCH/FILM packaging  

**Orchestrator/Synthesizer:** single Beta pipeline (user-facing Wolf Intelligence).  
**Peaches:** remains CoS for army/ops — not inside Beta render path.  
**Scout/Indigo/Velvet/Reel/Frame:** REDEFINE to skills/tools; keep Grok profiles dormant or docs-only until Matthew retires.

Do **not** force five if Phase 1 can ship with Strategy + Drafter + Validator only.

---

## U. Skills Architecture

Composable skills (structured JSON in/out + evidence bundle):

AnalyzeMetricoolPerformance · AnalyzePreviousFortnight · ResearchWebTrends · ResearchXTrends · AnalyzeInspiration · GenerateFortnightStrategy · GenerateContentCard · GenerateStorySpine · GenerateShotList · GenerateCaption · GenerateHashtags · CheckBrandAlignment · CheckFactualClaims · CheckAssetAvailability · CompareHumanEdit · ExtractLearning · EvaluatePerformance · PrepareMemoryCandidates · QuarantineLearningURL

Each returns: `result, evidence, source, confidence, assumptions, missing_information`.

---

## V. Provider-Independent Model Router

CURRENT STATE: `llm_orchestrator.ROLE_ROUTING` hardcodes openai/anthropic/gemini per role; keys often empty; UI forces dry_run.

TARGET: task→capability router:
- `task_type` + `latency_class` + `cost_class` → provider/model  
- Benchmark scores influence routing  
- UI never shows provider; admin panel does  

Acceptance: change routing map without UI string changes; dry_run still default until LaunchAgent forces safe mode.

---

## W. Benchmarking Framework

Offline fixtures: brand kit + sample history + expected constraints.  
Metrics: brand-violation rate, unsupported-claim rate, edit-distance vs human, latency, cost.  
Store in `benchmark_runs`. Gate model upgrades on scores — human-gated cutover.

---

## X. Complete Two-Week Planning Workflow

Permission: `can_create_plan` (seed subjects: Amanda, Haikal, Misa — **config**, not code constants).

Flow:
1. CONTENT PLANNER → BRAND → BUILD NEXT PLAN  
2. Auto: load brand memory, decisions, prior plans, Metricool, Learning Library, web trends, X trends, media, campaigns  
3. Build Fortnight Strategy + full Working Draft cards (no separate strategy approval gate)  
4. Show Strategy top; cards editable  
5. If Strategy edited → regenerate affected cards; keep revision history  
6. Controls per card: EDIT | GIVE DIRECTION | REGENERATE PARTIAL | MARK FILM | ATTACH ASSET  
7. Approve plan (human) → still **not** publish  
8. Production updates production_record  
9. Publish path separate + publish-gate + Metricool write permission  

Cadence default ~3 feed + ~14 stories — **per-brand config**.

---

## Y. Beta Dashboard UX

User-facing:
```
Wolf Intelligence
✓ Performance reviewed
✓ Previous content reviewed
✓ Current opportunities researched
✓ Inspiration reviewed
✓ Available media checked
✓ Strategy prepared
✓ Working plan ready
```

Fortnight Strategy block: Primary Theme, Why Now, Objectives, Recommended Mix, Production Priorities, Relevant Inspiration, Important Learnings.

Cards: Date, Theme, Objective, Pillar, Format, Concept, Hook, Copy, Hashtags, CTA, Shot List, Production Notes, Inspiration, Trend Rationale, Performance Rationale, Asset Status (READY/PARTIAL/FILM/BLOCKED).

**Never show:** OpenAI/Anthropic/Gemini/Grok, Muse/Velvet/etc.

Admin: provider, model, latency, cost, skill traces, memory IDs.

---

## Z. Permission / Approval Architecture

| Permission | Effect |
|---|---|
| `can_create_plan` | Start Build Next Plan |
| `can_edit_plan` | Edit drafts |
| `can_approve_plan` | Mark human_approved revision |
| `can_publish` | Metricool schedule/publish |
| `can_approve_memory_rule` | PROPOSED→APPROVED RULE |
| `can_admin_observability` | See providers/traces |

Server-side enforcement in `serve_beta.py` (extend existing status gates). No localhost-auth today — **P0 gap** (prior audit); add shared secret / Access-aware auth before non-dry LLM spend or publish.

---

## AA. Security / Prompt-Injection Defenses

- All Learning Library / trend fetches = untrusted; strip instruction-like content from model context or wrap in data fences.  
- Never execute fetched HTML/JS.  
- Secrets only in credential files; never in UI or memory text.  
- Publish/render/memory-RULE: server gates.  
- Beta isolated from :8787 (already: separate process; serve_beta refuses 8787).  
- Quarantine before retrieval.

---

## AB. Observability / Admin Architecture

Admin views: skill run timeline, router choice, token/cost, memory hits, gate denials, Metricool sync health.  
User views: Wolf Intelligence checklist only.  
Logs: extend `llm_logs` → `skill_runs` with evidence hashes.

---

## AC. Failure / Fallback Architecture

| Failure | Behavior |
|---|---|
| Metricool down | Plan continues; checklist item warns; no fake metrics |
| No assets | Cards FILM/PARTIAL; do not drop ideas |
| LLM provider down | Failover via router; else dry template + MISSING INFORMATION |
| Trend fetch fail | Empty trend lane + noted missing |
| Brand memory missing | Block Build or proceed with UNKNOWN loud |

Never invent Metricool numbers (Muse/Standing Rules aligned).

---

## AD. Proposed Data Model (minimum)

- `brands` (id, cadence_json, …)  
- `memory_items` (typed governance fields)  
- `decision_log`  
- `content_plans` (fortnight header)  
- `plan_revisions` (role, diff, full_json, actor)  
- `content_cards` + `card_revisions`  
- `assets` + `asset_links` + `asset_status`  
- `learning_library_items`  
- `performance_records`  
- `publish_records` / `production_records`  
- `lesson_candidates`  
- `skill_runs` / `benchmark_runs`  
- `permissions` (subject → bits)  

Reuse/extend `content_planner` carefully — prefer new tables over overloading smoke schema.

---

## AE. What Happens Overnight vs Human Approval

**Overnight AUTOMATIC (drafts only):** Metricool pull, asset index refresh, trend OBSERVATIONS (TTL), memory candidate proposals, optional draft fortnight for brands with `can_create_plan` owners — all PROPOSED.  

**HUMAN-GATED:** approve plan, approve RULE memories, publish/schedule, spend ads, guest/client mail, merge PR #1, go-live automation, Cloudflare seats.

---

## AF. Current → Target Migration

1. **Freeze** new content Grok agents (eggbot HOLD for content).  
2. Import Obsidian brand essentials → `memory_items` BRAND FACT/RULE (human review).  
3. Extend Beta schema (revisions, memory, permissions).  
4. Implement skills as Python modules behind orchestrator (dry_run first).  
5. Wire Metricool READ.  
6. Build Next Plan UX.  
7. Redefine Muse/Indigo/Velvet/Frame/Reel as skills; keep profiles for history.  
8. Remotion/ffmpeg remains **parallel** media milestone (prior audit M1) — not blocker for intelligence drafts.  
9. Never migrate onto :8787.

---

## AG. What Existing Agents To KEEP / MERGE / REDEFINE / REMOVE

**Content Intelligence set after consolidation (recommended):**
- **Beta skills/tools** (primary): Strategy, Evidence, Drafter, Validator, (+ Production adapter)  
- **Grok KEEP as ops:** Peaches + Tier1 infra (Pulse/Link/Gauge/Cipher/Breach/Phoenix/Anvil/Vesper) + corporate/ops specialists  
- **REDEFINE→skills:** Muse, Indigo, Velvet, Reel, Frame, Scout (content/trend parts)  
- **KEEP narrow:** Ink (kits) until Canva tooling exists  
- **REMOVE:** none forcibly overnight — **no deletes this mission**. Recommend eventual dormancy of duplicate content personas after skills ship  
- **eggbot:** REDEFINE — no new content bots without Matthew

**Recommended consolidated Content Intelligence "agents" (logical):** Wolf Intelligence Orchestrator + 3–5 skills above — **not** 6 Week2 Grok names in UI.

---

## AH. Exact Phase 1 Build (first implementation milestone)

1. Schema: `plan_revisions`, `memory_items`, `permissions` (`can_create_plan`).  
2. Import Habitat brand FACTS from export (human-approved batch).  
3. Build Next Plan endpoint: dry skills, checklist UX, one Working Draft.  
4. Preserve AI proposal vs human edit revisions.  
5. Asset status enum READY/PARTIAL/FILM/BLOCKED on cards.  
6. LaunchAgent ensure LLM dry_run safe.  
7. Document admin vs user labels.  

**Out of Phase 1:** Remotion, Metricool write, Learning Library fetch at scale, retiring Grok agents.

---

## AI. Exact Phase 2 Build

- Metricool READ sync + performance rationale  
- Learning Library quarantine MVP  
- Web + X trend lanes with TTL OBSERVATIONS  
- Brand validator skill wired to kits  
- Router + first benchmark fixture  
- Auth on mutating Beta routes  

---

## AJ. Exact Phase 3 Build

- Lesson extraction from diffs + performance  
- RULE promotion workflow (Vesper grill optional)  
- Production/publish records + Metricool write behind `can_publish`  
- MATCH tool against real NAS/library index  
- Dormant Week2 Grok content personas; Peaches routes content asks to Beta  
- Full observability admin  

---

## AK. Risks / Unknowns

| Item | Severity | Notes |
|---|---|---|
| Learning destroyed by single-row overwrite | HIGH | Fix in Phase 1 |
| Unauthenticated localhost mutate + future live keys | HIGH | Prior audit P0 |
| Memory poisoning via trends/URLs | HIGH | Quarantine + types |
| Agent sprawl continues (eggbot) | MED | Policy HOLD |
| Supplied memory-engineering docs missing | MED | UNKNOWN |
| Metricool API shape/live brands | MED | Creds exist; integration unverified |
| Empty media library | MED | FILM path required |
| Brand key pollution (`bzg`) | MED | Prior audit |
| Pulse/:8787 confusion | LOW if Content stays on 8788 | Never touch 8787 |
| Remotion missing | MED for video ship; LOW for plan intelligence | Parallel track |

---

## AL. Questions Requiring Matt's Decision

1. Retire/dormant Week2 Grok content agents once Beta skills ship — when?  
2. Authorize Metricool READ now vs wait for Advanced workspace confirmation?  
3. Learning Library: store summaries only vs cached media?  
4. Auth model for :8788 mutating routes (CF Access only vs app secret)?  
5. Default cadence per brand overrides?  
6. Who holds `can_approve_memory_rule` besides Matthew?  
7. Is ffmpeg acceptable interim vs Remotion for FINAL?  
8. X research: stay free-only forever or paid API later?  
9. Obsidian sync direction: vault→Beta one-way or bidirectional?  
10. UI name lock: always "Wolf Intelligence"?  

---

## AM. Tomorrow Morning Checklist

- [ ] Read `/tmp/WOLF-INTELLIGENCE-TOMORROW.md`  
- [ ] Confirm no changes to beta-os/Obsidian/agents/DBs/:8787 overnight  
- [ ] Decide Phase 1 go / adjust AL questions  
- [ ] Open Beta `:8788` health (GET only) — expect ok  
- [ ] Skim agent inventory §B / consolidation §AG  
- [ ] Do **not** create agents; do **not** paste provider names into content-2.0.html  
- [ ] First engineering task: `plan_revisions` + `memory_items` design PR via Anvil/Cursor  
- [ ] Keep Metricool write and Remotion off Phase 1  
- [ ] Schedule human review of Habitat brand memory import candidates  

---

## Appendix — Beta OS verification (2026-09-14 overnight)

- GET `http://127.0.0.1:8788/api/health` → `{"ok": true, "root": "beta-os", "planner": "sqlite"}`  
- Files exist: `scripts/serve_beta.py`, `llm_orchestrator.py`, `stage_inspector.py`  
- Capabilities: planner CRUD gates, staging, assets, upload, llm/generate, render **stub**, publish-gate  
- Remotion: **NOT present** (no package.json)  
- Metricool creds file: **EXISTS** `~/.openclaw/credentials/metricool.json`  
- :8787 LISTEN (wolf-system) — **not contacted**  
- :8788 LISTEN (`serve_beta`) — GET-only used  

## Appendix — Content agent handoffs (summary)

- **Muse:** briefs ≥14d; never invent Metricool; SLA if Velvet IDLE  
- **Scout:** free-web; cited links; no X pay  
- **Indigo:** real clip IDs; MATCH rollups; rematch if Velvet IDLE  
- **Velvet:** DRAFT packs; MATCH only; no posts/schedule/Metricool write  
- **Frame:** brand kit QC; RED/AMBER/GREEN  
- **Reel:** editor shot cards from Velvet+Muse; never publish  

## Appendix — Confirmation

- **No systems modified** (writes only `/tmp/` reports).  
- **:8787 untouched.**  
- **No agents created/deleted.**  
- **No paid API calls.**  
- **No secrets printed.**
