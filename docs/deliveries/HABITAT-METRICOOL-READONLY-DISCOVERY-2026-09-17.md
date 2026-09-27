# Habitat Metricool Read-Only Intelligence + Target Verification — 17 Sep 2026

**Lane:** Beta read-only · **Human commissioning:** untouched · **Writes:** none · **`.env`:** unchanged (`BETA_METRICOOL_ENABLED=false`, `BETA_METRICOOL_WRITE_ENABLED=false`) · **Production:** none · **Secrets:** not recorded

## Identity map (deterministic)

| Layer | Value | Certainty |
|---|---|---|
| Wolf Entity | `ENT-GGV` | VERIFIED (`org_entities`) |
| Wolf Brand | `habitat` / org_brands Habitat CLIENT_BRAND | VERIFIED |
| External system | `metricool` | VERIFIED (`brand_external_ids`) |
| Metricool blogId | **`6260634`** | **VERIFIED** — live Metricool brand list label **The Habitat** / title The Habitat Lombok; matches `brand_external_ids.external_id`; ownerUsername present (account-level, not pasted); hash present (fingerprint only) |
| Wrong-brand check | Distinct from Atrium `6260617`, Uma Blu `6260631`, Selo `6260635`, Tropik `6260638`, Goss Group `6260628` | VERIFIED separation by blogId |

Not name-similarity alone — **numeric blogId** + live Metricool settings + Beta mapping row.

### External network targets (from Metricool brand settings READ)

| Network | Identifier (public) | Class | Stored performance in Beta |
|---|---|---|---|
| Instagram | `habitat.lombok` | **VERIFIED** (settings + permalinks in `performance_records`) | YES — only network with rows |
| Facebook | page id `665769143297319` | **PARTIAL** — settings present; no FB rows in `performance_records` | NO |
| TikTok | `habitat.lombok` | **PARTIAL** — settings present; no TikTok rows stored | NO |
| LinkedIn | org URN present | **PARTIAL** | NO |
| YouTube | channel id present | **PARTIAL** | NO |
| Google Business | location path present | **PARTIAL** | NO |
| Website | `https://www.thehabitatlombok.com` | **PARTIAL** (settings webData) | N/A |

**Ambiguous / unknown:** which network a future Wolf `content_planner.platform` value maps to for **write** payload (no publish adapter yet). Platform string on slots ≠ Metricool provider binding table.

## Target safety (wrong-client prevention)

| Question | Answer |
|---|---|
| Can Wolf prove Habitat → blogId 6260634? | **YES** via `brand_external_ids` |
| Does publish gate bind blogId today? | **NO** — gate returns READY_TO_PUBLISH + Metricool DISABLED; **no outbound payload / blogId injection** implemented |
| Risk if writes enabled without adapter? | High wrong-brand / wrong-network until explicit `brand_key → blogId → providers[]` binding is coded and tested |

## Performance DATA (Beta store)

Source: `performance_records` WHERE `brand_key=habitat` AND `external_profile_id=6260634` (READ SELECT only).

| Field | Result |
|---|---|
| Rows | **179** |
| Platforms in store | **instagram only** |
| Surfaces | post **21** · story **158** |
| Content types | VIDEO 128 · IMAGE 30 · FEED_CAROUSEL_ALBUM 15 · FEED_IMAGE 6 |
| Date coverage | **2026-07-21 → 2026-09-14** UTC (~8 weeks) |
| Reach / impressions | present on 179 |
| Engagement / views | present on **21** (feed posts); stories lack engagement fields in store |
| Clicks / conversions / followers | **not in schema / not available** in these rows |
| External post id + permalink | present |
| Sync path | `scripts/sync_metricool_performance.py` + Habitat helper; Beta client **fail-closed** when ENABLED=false (historical rows remain) |

All brands’ stored Metricool sync is Instagram-only today (Atrium/Selo/Tropik/Uma Blu same pattern).

## Reconciliation Wolf content → Metricool post

| Link | Status |
|---|---|
| `content_planner` → `external_post_id` | **UNAVAILABLE** — no Metricool/external columns |
| `content_cards` → Metricool | **UNAVAILABLE** — no external id fields |
| Version hash → Metricool | **UNAVAILABLE** — hash is internal fingerprint only |
| Caption fuzzy match | **INFERENCE only** — not used as truth |

**Classification: UNAVAILABLE** for deterministic WOLF ITEM → METRICOOL → EXTERNAL → PERFORMANCE.

## DATA ≠ LESSON (preserve layers)

| Layer | Habitat status |
|---|---|
| DATA | AVAILABLE (`performance_records`) |
| OBSERVATION | Not systematically stored from Metricool (analyze skill exists descriptive-only) |
| HYPOTHESIS / EXPERIMENT / RESULT | ABSENT as governed objects |
| APPROVED LESSON | ABSENT in `memory_items` from performance |

**Do not** auto-promote AI summaries into APPROVED RULES.

### Recommended learning model (no new DB)

Reuse `memory_items` with types + `approval_state`:

DATA stays in `performance_records` → human/system may write **OBSERVATION** (PROPOSED) → **HYPOTHESIS** → experiment via next `content_plans` → RESULT observation → only then **APPROVED** RULE/LESSON.

Existing `analyze_metricool_performance` skill already forbids causal language and blending story/reel scores — keep that bar.

## Descriptive findings (evidence-only; n noted)

1. Stored Habitat Metricool history is **Instagram-only** (n=179).  
2. Feed posts with engagement (n=21): **carousels** show higher mean engagement than FEED_IMAGE (carousel n=15 mean eng≈11.5; FEED_IMAGE n=6 mean≈4.8) — **small sample, not a strategy**.  
3. Highest feed reach in window: carousel ~672 reach / 22 eng (“honest truth / investment…” permalink DcNw6o9DqJb) — **outlier**, not a rule.  
4. Stories dominate count (158/179) but **lack engagement metrics** in store — cannot rank story “winners” fairly.  
5. Local post hours (WITA) cluster morning **07–08** and afternoon **14–16** — descriptive schedule pattern only.  
6. Mean IG reach across all stored rows ≈31 (median≈18) — skewed by stories; do not treat as brand KPI.  
7. No pillar tags on performance rows → **cannot** score pillars from this store.  
8. No video-completion / click / follower series in schema → those questions **UNKNOWN**.  
9. Cross-network Habitat targets exist in Metricool settings but **zero** non-IG performance rows → FB/TikTok/etc. performance **UNKNOWN** in Beta.  
10. Analyze skill + planning_context_refs can attach Metricool evidence hashes to plans — **observation plumbing partial**, lessons not closed.

### Limitations

- Instagram-only sync · ~8 weeks · engagement mostly on 21 feed posts · no clicks/conversions · no pillar mapping · no Wolf↔Metricool id join · Beta live Metricool API disabled (`ENABLED=false`) so this pass used **stored** data + MCP brand settings READ (not a fresh sync).

## Content Machine feedback loop gap

| Stage | Exists? |
|---|---|
| PLAN | YES (`content_plans`) |
| PRODUCE | PARTIAL (library/assets/planner) |
| APPROVE | YES (Core Habitat publish gate) |
| PUBLISH | NO outbound (write lock + no adapter) |
| METRICOOL DATA | YES (IG store) |
| OBSERVATION | PARTIAL (skill; not routine governance) |
| HYPOTHESIS → NEXT PLAN | ABSENT as governed loop |

## Write commission readiness — **NOT READY**

| Check | Status |
|---|---|
| Exact Habitat Metricool account | VERIFIED (6260634) |
| Exact social targets | IG VERIFIED; others PARTIAL |
| Credentials capable of write | **UNKNOWN** — `BETA_METRICOOL_ENABLED=false`; no Beta-local creds path set in `.env` (example only); status does not load secrets |
| Beta isolation | YES — fail-closed client + tests |
| Publish gate binds exact target | **GAP** — no blogId/provider on gate output |
| Content version → outbound payload | **GAP** — version hash internal only |
| External id returns into Wolf | **GAP** — no column/path |
| Timeout/error behavior | PARTIAL — write blocked exception exists; full schedule API error matrix not exercised (correctly — no write) |
| Duplicate publish protection | **GAP** — no idempotency key / external-id uniqueness for publish |
| Rollback/cancel | UNKNOWN (Metricool schedule cancel not tested; must not test with writes) |

## Grok challenge

- Account certainty: **strong** on blogId; network write mapping still weak.  
- Wrong-brand risk: **mitigated for identity**, **open for publish adapter**.  
- Reconciliation: must not caption-match into truth.  
- Stats: carousel > image is **tiny n** — reject “winning strategy” claims.  
- Duplicate publish: unsolved until external id stored.  
- Timeout ambiguity: unproven until controlled Beta write dry-run design.  
- Learning: **enough DATA for IG descriptive work**; **not enough for APPROVED lessons**.  
- Infrastructure: **do not** build second Metricool DB, Learning Library product, or agent — extend mapping + memory_items.

## Human commissioning

`content_planner` Habitat slots unchanged this mission (smoke/draft; no work_item/core_approval touched). No Metricool schedule/create/update called.
