# WOLF METRICOOL READ AUDIT — Phase 2 Prep

**Date:** 2026-09-15 (WITA / Asia/Makassar)  
**Scope:** READ-ONLY inventory + safe live list-brands GET  
**Machine:** Wolfs-Mac-Studio.local (`36d8fa4b-2d58-4983-b227-e5bfa5495e78`) + box `/home/box` copies  
**Deliverable only write:** `/tmp/WOLF-METRICOOL-READ-AUDIT.md`  
**:8787:** not contacted  
**:8788:** GET `/` and GET `/api/health` only  

---

## A. Executive Summary

Metricool is already integrated operationally on wolf-system (not Beta). Credentials exist (`~/.openclaw/credentials/metricool.json`, mode `0600`). A safe live **GET** ` /admin/simpleProfiles` succeeded: **6 live brand profiles**, user_id `4825908`, base `https://app.metricool.com/api`.

Five produce brands map cleanly to Wolf content brands via **blogId** (stable) + `atlas_brands.canon()` (BZG/AMG are **entity tags**, not brand aliases — `canon("BZG")` / `canon("AMG")` → `None`). Live Metricool **labels** have drifted from credential labels and from some `atlas_brands.metricool_label` strings; Phase 2 must key on **blogId**, not label string equality.

Historical analytics already land in `state/atlas-learn.db` table `atlas_metricool` (**879 rows**, ~2026-08-01 → 2026-09-14, all five produce brands GREEN as of 2026-09-15 ~07:14 WITA). Post-level and Stories surfaces are both present (126 posts / 753 stories). Engagement metrics are richer on IG posts than on stories.

**Write code exists** (`metricool_publish.py`, `schedule_post`, `upload_media`, DELETE post) — must **not** be imported into Beta Phase 2 READ connector. Beta `:8788` has publish-gate stub only; no Metricool HTTP client.

**Biggest security risk:** LaunchAgents source `wolf-secrets.env` while Metricool token lives in world-readable-path JSON at `0600`; plus live **write** client co-located with read client (`metricool_api.py` mixes GET + POST). Accidental schedule/publish if Beta imports the whole module.

**Biggest data-model risk:** Label drift (credential vs live vs display names) + IG handle mismatches in `atlas_brands` vs live Metricool — string joins will mis-attribute brands; blogId is the only safe join key.

**Recommended first Phase 2 implementation:** Read-only Beta connector that reuses `metricool_api` **GET helpers only** (or a forked thin client), syncs by blogId into `performance_record` / evidence pack for Habitat first, with `fetched_at` + source provenance — **no write methods in the Beta package**.

---

## B. Metricool Files / Integration Inventory

| PATH | PURPOSE | CURRENT/LEGACY/BACKUP | READ | WRITE | REUSABLE? | NOTES |
|------|---------|----------------------|------|-------|-----------|-------|
| `~/.openclaw/credentials/metricool.json` | Auth + brand→blogId map | CURRENT | loads token | n/a | YES (structure) | mode 0600; INDEX.md lists fields |
| `~/.openclaw/workspace/METRICOOL-SETUP.md` | Setup walkthrough | CURRENT/docs | n/a | describes write flows | PARTIAL | Advanced plan, API token steps |
| `wolf-system/scripts/metricool_api.py` | Core API client | CURRENT | whoami, list_brands, analytics_* | schedule_post, upload_media | PARTIAL — split read | X-Mc-Auth; mixes R/W |
| `wolf-system/scripts/atlas_metricool.py` | Pull + normalize + SQLite store | CURRENT | pull/status/diagnose | commits rows to local DB | YES for READ path | dry_run default True; LaunchAgents use --commit |
| `wolf-system/scripts/atlas_brands.py` | Brand canon + metricool_blog_id | CURRENT | mapping | n/a | YES | five produce slugs |
| `wolf-system/scripts/content-studio/metricool_perf.py` | Client-report performance | CURRENT | analytics via metricool_api | n/a | PARTIAL | containment label match risk |
| `wolf-system/scripts/content-studio/metricool_publish.py` | Draft schedule / delete | CURRENT | n/a | POST + DELETE | **NO for Phase 2 READ** | defaults draft=True, auto_publish=False |
| `wolf-system/dashboards/metricool_glance.py` | Hub glance HTML | CURRENT | reads atlas store | n/a | YES pattern | aliases selo/uma_blu |
| `wolf-system/dashboards/assets/metricool-glance.js` | Front-end glance | CURRENT | display | n/a | YES | |
| `wolf-system/dashboards/data/metricool-*.json` | Per-brand follower snapshots | CURRENT cache | YES | n/a | YES as cache | pulled 2026-09-10 |
| `wolf-system/dashboards/data/metricool-snapshot.json` | Aggregate snapshot | CURRENT/stale-ish | YES | n/a | PARTIAL | 2026-08-21 window |
| `wolf-system/state/atlas-metricool-status.json` | Freshness status | CURRENT | YES | rewritten by pull jobs | YES | GREEN 2026-09-15 |
| `wolf-system/state/atlas-learn.db` → `atlas_metricool` | Historical post/story rows | CURRENT | YES | local ingest | YES evidence store | 879 rows |
| `~/Library/LaunchAgents/com.wolfcommandsystem.habitat-metricool.plist` | Habitat pull every 30m | CURRENT loaded | triggers read+local write | no Metricool write | ops | launchctl listed |
| `~/Library/LaunchAgents/com.wolfcommandsystem.produce-metricool.plist` | atrium/uma-blu/selo/tropik 30m | CURRENT loaded | same | no Metricool write | ops | |
| `~/Library/LaunchAgents/com.wolfcommandsystem.atlas-metricool.plist` | Daily 05:10 all-brand pull | **Disabled** | — | — | legacy schedule | Disabled=true |
| `~/.openclaw/cron/jobs.json` | weekly-content-gap mentions Metricool | DISABLED | n/a | n/a | no | agentTurn text only |
| `~/beta-os/scripts/serve_beta.py` | publish-gate stub | CURRENT | gate GET | no Metricool HTTP | stub | :8788 |
| `~/beta-os/scripts/wolf_intelligence.py` | Phase 1 memory helper | CURRENT | n/a | n/a | no Metricool | |
| `wolf-system/archive/baks/scripts/*metricool*` | Historical bak | BACKUP | — | — | no | |
| `~/.openclaw/backups/wolf-system/2026-09-15/.../*metricool*` | Backup tree | BACKUP | — | — | no | includes publish/perf baks |
| Claude session memory `metricool-*.md` | Agent notes | LEGACY | docs | n/a | no | under Application Support |
| Box `/workspace/bzg-update/*metricool*` | Shareholder pack copies | COPY | YES | n/a | no | not SoT |

**Env:** No `METRICOOL_*` keys in `wolf-secrets.env` (token is file-based). LaunchAgents still `source` that env file for other secrets.

---

## C. Credential Structure — NAMES ONLY

**Path:** `/Users/wolfterminal/.openclaw/credentials/metricool.json`  
**Exists:** YES | **Mode:** `0600` | **Size:** 508 bytes | **Indexed:** YES (`credentials/INDEX.md`)

| FIELD NAME | PRESENT? | SAFE FORMAT DESCRIPTION |
|------------|----------|-------------------------|
| `user_token` | YES | secret string (~64 chars); used as `X-Mc-Auth` |
| `user_id` | YES | integer (~7 digits) |
| `default_blog_id` | YES | integer blog/workspace id |
| `base_url` | YES | `https://app.metricool.com/api` (non-secret) |
| `brands` | YES | object map label→blogId integers |
| `brands.Goss Group` | YES | int blogId |
| `brands.Atrium Lombok` | YES | int |
| `brands.Surga Spa` | YES | int — **not in live profiles** (stale) |
| `brands.Uma Blu Cafe` | YES | int |
| `brands.Rainforest Restaurant` | YES | int — **not in live profiles** (stale) |
| `brands.Habitat` | YES | int |
| `brands.Selong Selo` | YES | int |
| `brands.Tropic` | YES | int |

**Validity appearance:** Valid-looking (live GET succeeded with token). Not expired for list-brands. Contains **stale brand entries** (Surga Spa, Rainforest) and **stale labels** vs live API.  
**Do not rotate during audit.** Values never printed.

---

## D. Account / Workspace Structure

**Model verified:** One Metricool user/account (`user_id` 4825908) owns **multiple brand workspaces** (blogIds). Timezone on live profiles: `Asia/Makassar`.

### Live profiles (GET `/admin/simpleProfiles`) — 6 brands

| blogId | LIVE label | IG | FB | TikTok | YouTube | LinkedIn org | Notes |
|--------|------------|----|----|--------|---------|--------------|-------|
| 6260617 | Atrium Lombok | atrium_lombok | PRESENT | ABSENT | PRESENT | PRESENT | produce |
| 6260628 | Goss Group | none | none | none | none | none | **no networks** |
| 6260631 | Uma Blu Coffee & Brunch | umablulombok | PRESENT | umablulombok | PRESENT | PRESENT | produce |
| 6260634 | The Habitat | habitat.lombok | PRESENT | habitat.lombok | PRESENT | PRESENT | produce |
| 6260635 | Selo Properties | selo.properties | PRESENT | selo.properties | PRESENT | PRESENT | produce |
| 6260638 | Tropik Resort Lombok | tropiklombok | PRESENT | tropiklombok | PRESENT | PRESENT | produce |

**Credential-only blogIds not returned live:** 6260629 Surga Spa; 6260633 Rainforest Restaurant → treat as STALE / deleted / inaccessible.

**GET `/admin/networks`:** returned **HTTP 404** for all five produce blogIds during this audit → endpoint may be deprecated; network presence taken from `simpleProfiles` connector fields instead. Classify networks endpoint: **UNKNOWN / broken in current client**.

---

## E. Wolf Brand Mapping

Target content brands: **Habitat-Villas, Atrium, Uma Blu, Tropik, Selong Selo**.  
Rule: **no silent BZG/AMG alias** — verified: `atlas_brands.canon("BZG"|"AMG")` → `None`. Entities are separate attributes (`uma_blu.entity=BZG`, `atrium.entity=AMG`).

| METRICOOL NAME (live) | blogId | POSSIBLE WOLF BRAND | SLUG | CONFIDENCE | EVIDENCE |
|----------------------|--------|---------------------|------|------------|----------|
| The Habitat | 6260634 | Habitat / Habitat-Villas | `habitat` | HIGH | blogId matches `atlas_brands.metricool_blog_id`; canon("Habitat-Villas")→habitat; IG habitat.lombok |
| Atrium Lombok | 6260617 | Atrium | `atrium` | HIGH | exact label + blogId + IG atrium_lombok |
| Uma Blu Coffee & Brunch | 6260631 | Uma Blu | `uma_blu` | HIGH | blogId match; label drifted from "Uma Blu Cafe" |
| Tropik Resort Lombok | 6260638 | Tropik | `tropik` | HIGH | blogId match; live fixed spelling Tropik; cred still "Tropic" |
| Selo Properties | 6260635 | Selong Selo | `selo` | HIGH | blogId match; label drifted from "Selong Selo" |
| Goss Group | 6260628 | (agency; no content networks) | — | HIGH | no connectors; glance treats as "no networks" |
| Surga Spa (cred only) | 6260629 | not a Phase-2 content brand | — | N/A | not live |
| Rainforest Restaurant (cred only) | 6260633 | not a Phase-2 content brand | — | N/A | not live |

**Handle drift (data quality):**
- `atlas_brands.habitat.instagram` = `habitatvillas.lombok` vs live Metricool `habitat.lombok`
- `atlas_brands.selo.instagram` = `selo_group_` vs live `selo.properties`

**Do not invent BZG→Uma Blu or AMG→Atrium as Metricool brand aliases.** Entity ownership ≠ Metricool workspace identity.

---

## F. Available Read Analytics

Sources of evidence: `metricool_api.py` v2 analytics GETs; live DB `atlas_metricool` column fill rates; docstring field lists.

### Retrieval surfaces (code)

| Endpoint / helper | Method | Status |
|-------------------|--------|--------|
| `/admin/simpleProfiles` | GET | **WORKS** (tested) |
| `/admin/networks` | GET | **404** this audit |
| `/v2/scheduler/posts` | GET | present in code; NOT live-tested |
| `/v2/analytics/posts/{network}` | GET | used by atlas pulls; evidence in DB |
| `/v2/analytics/reels/{network}` | GET | code present; reels merged into content |
| `/v2/analytics/stories/{network}` | GET | code present; **753 story rows** in DB |
| `/v2/analytics/timelines` | GET | brand summary / followers |
| `/v2/scheduler/posts` | POST | WRITE — do not use Phase 2 |
| `/v2/scheduler/uploadMedia` | POST | WRITE |
| DELETE `/v2/scheduler/posts/{id}` | DELETE | WRITE (`metricool_publish`) |

### Field classification (post-level)

| Field | Classification | Evidence |
|-------|----------------|----------|
| platform / network | AVAILABLE | DB: instagram/facebook |
| profile / blogId | AVAILABLE | column `blog_id` |
| post ID | AVAILABLE | `post_id` |
| permalink | AVAILABLE | 879/879 non-null |
| published timestamp | AVAILABLE | `published_at` |
| content type / surface | AVAILABLE | `surface` post\|story; `post_type` |
| caption/text | LIKELY AVAILABLE | 129/879 non-null (stories often empty) |
| reach | AVAILABLE | 814/879; all stories in sample have reach |
| impressions | AVAILABLE | 879/879 |
| views | LIKELY AVAILABLE | 61/879 (mostly posts/reels) |
| video views / watch time / completion | UNKNOWN | not stored as dedicated columns |
| likes / comments / shares | AVAILABLE on posts | 126 rows; stories typically lack engagement aggregate |
| saves | LIKELY AVAILABLE | 61/879 |
| engagement / engagement_rate_pct | AVAILABLE on many IG posts | stories: engagement often null |
| profile visits / clicks | UNKNOWN | not in local schema |
| followers / follower change | LIKELY AVAILABLE | via timelines + per-brand JSON snapshots |

### Other

| Topic | Finding |
|-------|---------|
| Historical lookback | YES in practice — DB from ~2026-08-01; API accepts `from`/`to` ISO range |
| Pagination | UNKNOWN — client loads range bulk; no explicit cursor handling found |
| Rate limits | UNKNOWN — not documented in local setup; 403 used for disconnected networks |
| Stories data | YES — surface=`story`, 753 rows |
| Reels distinguishable | LIKELY — separate `analytics_reels` API; may land as posts in store |
| Expired stories retained | UNKNOWN — Metricool may keep analytics after expiry; local DB retains pulled rows |
| Date/timezone | Profiles Asia/Makassar; API ISO `from`/`to`; store mixes naive/`+08:00` — needs canonical UTC+WITA policy |

---

## G. Safe Read Test Result

| Item | Value |
|------|-------|
| Attempted | YES |
| Call | `metricool_api.whoami()` / `list_brands()` → GET `/admin/simpleProfiles` |
| Token handling | Loaded from file into process memory only; never echoed |
| Mutation endpoints | NOT CALLED |
| Result | **PASS** |
| brand_count | **6** |
| user_id | 4825908 (ok to record) |
| Sanitized labels | Atrium Lombok, Goss Group, Uma Blu Coffee & Brunch, The Habitat, Selo Properties, Tropik Resort Lombok |
| `/admin/networks` | NOT counted as pass — 404; mutation-safe but broken |
| Analytics GET this session | NOT re-called (avoid load); historical pulls already prove GET analytics work |

---

## H. Existing Script Audit

### `metricool_api.py` (301 lines)
- **Auth:** `X-Mc-Auth: user_token` from credentials JSON  
- **READ:** `whoami`, `list_brands`, `list_networks`, `list_scheduled_posts`, `analytics_posts|reels|stories|all_content|timeline|brand_summary`  
- **WRITE:** `schedule_post`, `upload_media`  
- **Hardcoded IDs:** none required; uses creds `brands` / default_blog_id  
- **Errors:** urllib; `alert=False` on expected 403 for disconnected networks  
- **Pagination / rate limit:** minimal / unknown  
- **Beta reuse:** **YES if write functions stripped or never imported**

### `atlas_metricool.py` (~1968 lines)
- **READ path:** transport → analytics_* → `normalise` → SQLite `atlas_metricool`  
- **Brand resolution:** atlas_brands.metricool_blog_id first, else credentials labels via `canon()`  
- **Defaults:** `pull(..., dry_run=True)`; LaunchAgents pass `--commit`  
- **Excludes** non-produce workspaces (Goss Group, Surga, Rainforest) from five-brand set  
- **Reusable:** YES as reference + optional local cache; Beta should own its own DB tables

### `metricool_perf.py`
- READ-only for reports; `resolve_blog_id` uses **containment** matching on credential labels — risk of greedy mis-hit if labels collide  
- Manual JSON override path under `state/content-studio/client-reports/`

### `metricool_publish.py` — WRITE
- POST schedule (draft default True, auto_publish False), DELETE post, media normalize  
- Attribution stamp into local systems  
- **Do not wire into Beta Intelligence Phase 2**

### `metricool_glance.py`
- Read-only hub display from atlas store; UNKNOWN not zero; Goss Group forced "no networks"

### Beta
- No Metricool HTTP client  
- `GET /api/planner/publish-gate` stub documents future write gate only

---

## I. Recommended Read-Only Connector Architecture

```
Metricool API (GET only)
        ↓
beta-os/scripts/metricool_read_client.py   ← NEW; NO schedule/upload/delete
        ↓  (auth from credentials path or injected secret; never frontend)
normalizer → performance_record rows
        ↓
Beta SQLite / evidence store (source=metricool, fetched_at, blog_id, brand_slug)
        ↓
Wolf Intelligence Evidence Pack (admin may say "Metricool"; user UI: Performance)
```

Rules:
1. Package must not import `schedule_post` / `upload_media` / `metricool_publish`.  
2. Join brands by **blogId** from `atlas_brands.metricool_blog_id` (refresh labels from live list periodically).  
3. Planning code consumes **normalized rows**, never raw API blobs.  
4. Fail soft: Metricool down → plan continues with "performance unavailable".  
5. Keep wolf-system LaunchAgents as-is until Beta sync proven; avoid dual-writers without idempotent keys.

---

## J. Recommended Performance Data Model

Minimum Phase 2 fields **supported by evidence**:

| Field | Notes |
|-------|-------|
| `brand_slug` | atrium\|habitat\|selo\|tropik\|uma_blu |
| `blog_id` | Metricool workspace id (int) |
| `network` | instagram\|facebook\|… |
| `surface` | post\|reel\|story |
| `external_post_id` | Metricool/post id |
| `permalink` | URL |
| `published_at` | store UTC; display WITA |
| `content_type` / `post_type` | as provided |
| `caption` | nullable |
| `reach` | nullable |
| `impressions` | |
| `views` | nullable |
| `likes` `comments` `shares` `saves` | nullable |
| `engagement` `engagement_rate_pct` | nullable |
| `fetched_at` | sync time |
| `source` | `metricool` |
| `raw_ref` | optional hash/pointer to raw blob — not full secret |

Optional later (UNKNOWN until verified): watch_time, completion_rate, profile_visits, clicks, follower_delta.

Primary key suggestion: `(blog_id, network, surface, external_post_id)` with upsert on fetch.

---

## K. Planning Context Snapshot Design

When Build Next Plan runs, freeze an immutable snapshot:

```
planning_context_snapshots
  id, brand_slug, created_at, created_by_subject, plan_id
planning_context_refs
  snapshot_id, ref_type, ref_id, version_or_hash
```

`ref_type` values (Phase 2 minimum):  
`brand_memory` | `decision` | `prior_plan` | `metricool_perf_window` | `trend` | `learning_item` | `asset_index`

For Metricool specifically store:
- `window_from` / `window_to`
- list of `performance_record` ids **or** content hash of the evidence pack used
- `metricool_sync_fetched_at_max`

**Do not** re-query "current" Metricool later and claim it was the planning context.

---

## L. Test / Operational Data Separation

Phase 1 acceptance plans must not become learning evidence.

Recommend durable discriminator on all intelligence tables:

| Column | Values |
|--------|--------|
| `data_lane` | `operational` \| `development` \| `test` |
| or `is_test` | boolean default false |

Rules:
- Learning / RULE promotion jobs: `WHERE data_lane='operational'` only  
- Skills dry-runs: force `data_lane='test'`  
- UI admin filter to hide test by default  
- Do **not** delete Phase 1 rows in this audit — tag going forward; backfill tags for known acceptance fixtures

---

## M. Cloudflare Identity Findings

| Layer | Finding |
|-------|---------|
| wolf-system dashboards | Mature CF Access identity: `access_identity.py`, `_cf_jwt.py` — `Cf-Access-Authenticated-User-Email`, signature-checked `Cf-Access-Jwt-Assertion`, `CF_Authorization` cookie; issuer `https://wolfcommand.cloudflareaccess.com` |
| Beta `:8788` Phase 1 | **X-Wolf-Subject** header or JSON `subject` — **not** CF JWT; comments say "until CF identity is connected" |
| Desired path | Cloudflare Access → verified email → Wolf subject → permissions (`can_create_plan`, later `can_publish`) |
| This audit | READ-ONLY inspection; **no CF config changes** |

**CLOUDFLARE IDENTITY PATH FOUND:** **PARTIAL** — production pattern exists on :8787 stack; Beta not wired yet.

---

## N. Security Findings

1. **Write client co-located with read** (`metricool_api.py`) — highest accidental-publish risk if Beta imports module wholesale.  
2. **`metricool_publish.py` live** with DELETE capability — even with draft defaults, wrong flags = schedule.  
3. **Credential file** present; LaunchAgents pull analytics every 30m — ensure logs never dump `X-Mc-Auth` (code uses header; verify log redaction).  
4. **Beta localhost subject spoofing** — anyone who can hit :8788 can send `X-Wolf-Subject` until CF JWT lands.  
5. **Label/handle drift** → wrong-brand analytics if string-matched.  
6. **Stale cred brands** (Surga/Rainforest) could confuse resolvers using containment match (`metricool_perf`).  
7. **Frontend** must never receive `user_token`.  
8. **Duplicate ingestion** risk if Beta + atlas_metricool both commit without shared idempotent keys.  
9. **Timezone:** mix of Makassar profile TZ, API ISO, naive DB timestamps — mis-bucket fortnight windows.  
10. **Test-data contamination** (Pass 9) into learning if lanes unset.

**Canonical timestamps:** ingest as UTC instant; persist `published_at_utc`; derive WITA for UI; never assume social "local day" without explicit offset.

---

## O. Phase 2 Dependencies

- Metricool Advanced API access (already working for GET profiles + historical analytics)  
- Stable blogId map in Beta config (copy from `atlas_brands`, refresh labels from live list)  
- Read-only client package (no write)  
- `performance_record` (+ optional raw blob store) migration on Beta SQLite  
- Evidence Pack consumer for Build Next Plan  
- `data_lane` / test hygiene  
- CF identity wiring for mutating Beta routes (can defer pure sync job to local machine account)  
- **Do not** require Remotion, Metricool write, or :8787 coupling  

---

## P. Exact Recommended Phase 2 Build Order

1. **Add** `metricool_read_client.py` in beta-os (copy GET helpers only; deny-list write names).  
2. **Config:** brand_slug → blog_id table (five produce brands); ignore Goss Group for performance.  
3. **Migration:** `performance_records` + unique upsert key.  
4. **One-brand sync job** (Habitat) dry-run → commit to Beta DB with `fetched_at`.  
5. **Evidence Pack** slice: last 14d Habitat IG posts+stories summary for Build Next Plan.  
6. **UI admin:** "Performance sync health" (connector name OK in admin); user checklist: "Performance reviewed".  
7. **Extend** to atrium, uma_blu, tropik, selo.  
8. **Planning context snapshot** refs to Metricool evidence window.  
9. **Tag** Phase 1 test plans `data_lane=test`.  
10. **Only later:** CF JWT for Beta; Metricool WRITE behind `can_publish` + publish-gate (Phase 3+).

---

## Q. Unknowns Requiring Verification

- Exact Metricool rate limits / quotas on Advanced  
- Whether `/admin/networks` was renamed (404)  
- Reels vs posts dual-counting in `atlas_metricool`  
- How long expired IG Stories remain queryable via analytics API  
- Watch time / completion / profile visits field names if any  
- Whether credential `default_blog_id` still points at intended default (not printed; verify manually in UI)  
- Dual-writer conflict if Beta sync and LaunchAgents both pull same windows  
- Pagination behavior beyond current date-range pulls  
- Free/paid plan seat limits after label renames (6 live vs 8 cred entries)

---

## R. Questions Requiring Matt / ChatGPT Decision

1. Authorize Beta Metricool **READ sync now** (AL#2 from Master Architecture) given live GET works?  
2. SoT for blogId/label: keep updating `credentials/metricool.json` brands map vs Beta-owned config?  
3. Retire or keep wolf-system 30m LaunchAgents after Beta sync exists?  
4. Quarantine/delete write entrypoints from any shared package vs separate `metricool_write` package?  
5. Update `atlas_brands` IG handles to match live Metricool (`habitat.lombok`, `selo.properties`)?  
6. Remove stale Surga Spa / Rainforest entries from credentials?  
7. CF JWT on :8788 before any automated sync that is network-exposed?  
8. User-facing copy: never say "Metricool" (Master Arch acceptance) vs admin transparency?

---

## Pass completion checklist

| Pass | Status |
|------|--------|
| 1 Inventory | DONE |
| 2 Credential shape | DONE (names only) |
| 3 Account/workspace | DONE (live 6 brands) |
| 4 Read capabilities | DONE (code + DB evidence) |
| 5 Safe live read | **PASS** (list brands) |
| 6 Existing code audit | DONE |
| 7 Beta integration design | DONE (section I–J) |
| 8 Planning snapshot | DONE (K) |
| 9 Test data hygiene | DONE (L) |
| 10 Identity / auth | DONE (M) — PARTIAL CF path |
| 11 Security review | DONE (N) |

---

## Non-negotiable confirmations

- NO FILES MODIFIED (except this report under `/tmp`)  
- NO DATABASES MODIFIED  
- NO METRICOOL WRITE  
- NO CONTENT SCHEDULED  
- NO CONTENT PUBLISHED  
- NO CREDENTIAL VALUES PRINTED  
- NO CLOUDFLARE CHANGES  
- NO GROK AGENT CHANGES  
- :8787 UNTOUCHED (listen check only; no HTTP)  
- :8788 GET-only (`/`, `/api/health`)

---

*End of audit.*
