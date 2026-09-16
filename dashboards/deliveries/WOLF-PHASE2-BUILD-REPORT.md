# WOLF PHASE 2 METRICOOL BUILD REPORT

**Date:** 2026-09-15 07:45 WITA (Asia/Makassar / WITA)  
**Scope:** Metricool READ → Beta OS `:8788` only  
**Machine:** Wolfs-Mac-Studio.local (`36d8fa4b-2d58-4983-b227-e5bfa5495e78`)  
**Root:** `/Users/wolfterminal/beta-os/`  
**Report path:** `/tmp/WOLF-PHASE2-METRICOOL-BUILD-REPORT.md` (+ `dashboards/deliveries/`)

---

## A. Executive Summary

Phase 2 Metricool **READ** is live on Beta `:8788`. Habitat E2E proven (sync → `performance_records` → AnalyzeMetricoolPerformance → Evidence Pack → build-next → `planning_context_snapshot`). Same data-driven architecture extended to atrium / umablu / selo / tropik. **No Metricool write.** **:8787 wolf-system untouched (PID 3758).** Tests: **32 PASS / 0 FAIL**.

---

## B. Backups (phase2 timestamp)

Timestamp: `20260915-073339`

| File |
|------|
| `content-2.0.html.bak-phase2-20260915-073339` |
| `content_library.sqlite.bak-phase2-20260915-073339` |
| `serve_beta.py.bak-phase2-20260915-073339` |
| `skills__init__.py.bak-phase2-20260915-073339` |
| `wolf_intelligence.py.bak-phase2-20260915-073339` |

Pre-change PIDs: 8787=`3758`, 8788=`1862` (beta restarted after deploy; 8787 unchanged).

---

## C. Port / Process Confirmations

| Port | PID | Command |
|------|-----|---------|
| 8787 | 3758 | `/opt/homebrew/Cellar/python@3.14/3.14.5/Frameworks/Python.framework/Versions/3.14/Resources/Python.app/Contents/MacOS/Python /Users/wolfterminal/.openclaw/workspace/wolf-system/dashboards/serve.py 8787` |
| 8788 | 5992 | `/opt/homebrew/Cellar/python@3.14/3.14.5/Frameworks/Python.framework/Versions/3.14/Resources/Python.app/Contents/MacOS/Python /Users/wolfterminal/beta-os/scripts/serve_beta.py` |
| 8789 | — | clear (`pick_port` no longer falls back) |

- 8788 = `serve_beta.py` ONLY  
- 8787 = wolf-system `dashboards/serve.py` **unchanged PID 3758**  
- Restarted **only** beta `:8788` after deploy

---

## D. Schema Added / Altered

### New tables
- `brand_external_ids` — brand_key → external_system → external_id (blogId)
- `performance_records` — unique `(external_profile_id, network, surface, external_post_id)`; NULL≠0; `external_system=metricool`; `published_at_utc`; `data_lane`; `dual_count_risk`
- `planning_context_snapshots` — immutable JSON freeze on build-next
- `planning_context_refs` — `brand_memory`, `prior_plan`, `metricool_performance`, `asset_state`, `decision` (trend / learning_item prepared unused)

### Additive column
- `data_lane` (`operational`|`development`|`test`) on content_plans, plan_revisions, content_cards, card_revisions, skill_runs, performance_records, planning_context_snapshots

### Timezone
- **Store:** `published_at_utc` (UTC ISO / Z)  
- **Display / planning day:** Asia/Makassar (WITA)  
- Documented in migration SQL header + `wolf_intelligence.py` + read client

`integrity_check` = **ok**

---

## E. brand_external_ids Seed

| brand_key | blogId | label |
|-----------|--------|-------|
| atrium | 6260617 | Atrium Lombok |
| habitat | 6260634 | The Habitat |
| selo | 6260635 | Selo Properties |
| tropik | 6260638 | Tropik Resort Lombok |
| umablu | 6260631 | Uma Blu Coffee & Brunch |

No Goss Group planning brand. No BZG/AMG mapping. Config is **data-driven** via this table.

---

## F. Sync Counts

**Total performance_records:** 1103  
**Habitat:** n=179, oldest_published_at_utc=`2026-07-21T06:13:22Z`, newest=`2026-09-14T08:11:35Z`  
**Reels imported:** 0 (API returned empty reels for all five brands in this window; dual-count dedupe path retained)  
**dual_count_risk flags:** 0  
**NULL engagement retained (habitat):** 158 (NULL≠0)

### By brand
- **atrium:** 198
- **habitat:** 179
- **selo:** 240
- **tropik:** 276
- **umablu:** 210

### By brand × surface
| brand_key | surface | n |
|-----------|---------|---|
| atrium | post | 33 |
| atrium | story | 165 |
| habitat | post | 21 |
| habitat | story | 158 |
| selo | post | 13 |
| selo | story | 227 |
| tropik | post | 11 |
| tropik | story | 265 |
| umablu | post | 13 |
| umablu | story | 197 |

Idempotent upsert verified (second Habitat sync: inserted=0).

---

## G. READ-ONLY Client

`scripts/metricool_read_client.py`
- GET helpers only: `list_profiles`, `analytics_posts` / `reels` / `stories`, `analytics_all_content`
- **No** `schedule_post` / `upload_media` / delete / publish / `_post`
- Does **not** import wolf-system write modules
- Soft-fail `MetricoolReadError` — no secrets in exceptions
- Creds: `~/.openclaw/credentials/metricool.json` loaded in-process only

CLI: `scripts/sync_metricool_habitat.py` + `scripts/sync_metricool_performance.py --brand …`  
API: `POST|GET /api/admin/sync-metricool?brand=habitat` gated by `can_create_plan` via `resolve_authenticated_subject` (**X-Wolf-Subject = DEVELOPMENT ONLY**)

---

## H. Skills / Evidence Pack

- `load_metricool_evidence`  
- `analyze_metricool_performance` — full contract (`result`/`evidence`/`confidence`/`assumptions`/`missing_information`); medians + quartiles **per surface**; never blends Story vs Reel; no causal claims; links `evidence_items` (type performance_record, source metricool, permalink)  
- `build_evidence_pack` — Brand Memory + Previous Plans + Metricool Evidence + Asset State; Trend/Learning **not connected**  
- Wired into build-next order: Memory → Plans → Metricool Evidence → Asset State → Evidence Pack → Strategy → Working Draft  
- Soft-fail if Metricool down/empty: plan still builds with **Performance unavailable**

---

## I. planning_context_snapshots

- Frozen on every build-next; linked to `plan_id` + AI_PROPOSAL revision  
- Never overwritten by later re-query  
- Snapshots: **5**; refs: **115**; types: ['asset_state', 'brand_memory', 'metricool_performance', 'prior_plan']

---

## J. data_lane Hygiene

- Phase 1 fixtures backfilled `data_lane=test` (not deleted): **3** plans  
- New build-next plans: `operational` (**5**)  
- Metricool imports: `operational`  
- Skills/learning default **ignore non-operational**

---

## K. UI

- Checklist **Performance reviewed** = complete when performance evidence used  
- Trend / Inspiration remain **not connected**  
- No provider names in user checklist steps; no secrets in API JSON

Latest operational plan_id=8 checklist:
```json
[
  [
    "Brand Memory",
    "done",
    null
  ],
  [
    "Previous Plans",
    "done",
    null
  ],
  [
    "Performance reviewed",
    "done",
    null
  ],
  [
    "Evidence Pack",
    "done",
    null
  ],
  [
    "Strategy",
    "done",
    null
  ],
  [
    "Feed Cards",
    "done",
    null
  ],
  [
    "Story Spine",
    "done",
    null
  ],
  [
    "Asset State",
    "done",
    null
  ],
  [
    "Brand Rules",
    "done",
    null
  ],
  [
    "Trend signals",
    "placeholder",
    "not connected"
  ],
  [
    "Inspiration library",
    "placeholder",
    "not connected"
  ],
  [
    "Publish / schedule",
    "placeholder",
    "out of Phase 2 \u2014 no publish"
  ]
]
```

---

## L. Evidence Sample (sanitized)

Important learnings (descriptive only):
```json
[
  {
    "source": "performance",
    "surface": "post",
    "text": "Within post surface only, median reach was 91.0 across 21 items with non-null reach."
  },
  {
    "source": "performance",
    "surface": "story",
    "text": "Within story surface only, median reach was 16.0 across 158 items with non-null reach."
  }
]
```

evidence_items sample:
```json
[
  {
    "id": 73,
    "kind": "performance_record",
    "ref": "metricool:22",
    "brand_id": "habitat",
    "content": {
      "external_post_id": "3985876269530240715",
      "performance_record_id": 22,
      "permalink": "https://www.instagram.com/stories/habitat.lombok/3985876269530240715",
      "source": "metricool",
      "surface": "story",
      "type": "performance_record"
    }
  },
  {
    "id": 72,
    "kind": "performance_record",
    "ref": "metricool:40",
    "brand_id": "habitat",
    "content": {
      "external_post_id": "3981250927335607535",
      "performance_record_id": 40,
      "permalink": "https://www.instagram.com/stories/habitat.lombok/3981250927335607535",
      "source": "metricool",
      "surface": "story",
      "type": "performance_record"
    }
  }
]
```

evidence_items count (performance_record): **54**

---

## M. Identity

`resolve_authenticated_subject(request)` implemented.  
**X-Wolf-Subject / JSON subject = DEVELOPMENT ONLY.** Cloudflare Access JWT not wired (no CF changes this phase).

---

## N. Tests

File: `scripts/tests/test_phase2_metricool.py`

```
ount ok) — null_engagement=158
PASS  11 published_at_utc stored — 179
PASS  12 metricool imports data_lane=operational — 1103
PASS  13 Phase1 fixtures data_lane=test — 3
PASS  14 test-lane plans excluded from operational evidence default — recent=[7, 6, 5, 4]
PASS  15 idempotent sync (count stable) — 179->179 ins=0
PASS  16 AnalyzeMetricoolPerformance contract keys
PASS  17 no causal claim words in analysis statements
PASS  18 disclaimer separates surfaces / no blend score
PASS  19 evidence_items performance_record linked — 48
PASS  20 build-next metricool evidence in strategy — used=True learnings=2
PASS  21 planning_context_snapshot created — 5
PASS  22 snapshot refs include metricool_performance or brand_memory — ['asset_state', 'brand_memory', 'metricool_performance', 'prior_plan']
PASS  23 checklist says Performance reviewed not Metricool — ['Brand Memory', 'Previous Plans', 'Performance reviewed', 'Evidence Pack', 'Strategy', 'Feed Cards', 'Story Spine', 'Asset State', 'Brand Rules', 'Trend signals', 'Inspiration library', 'Publish / schedule']
PASS  24 UI mentions Performance reviewed; Trend not connected
PASS  25 soft-fail missing brand performance
PASS  26 integrity_check ok — ok
PASS  27 8787 PID unchanged — now=3758 expected=3758
PASS  28 no secrets in build-next JSON sample
PASS  T table planning_context_snapshots exists
PASS  T table planning_context_refs exists
PASS  T table performance_records exists
PASS  T table brand_external_ids exists

TOTAL PASS=32 FAIL=0
```

**TOTAL PASS=32 FAIL=0**

Coverage includes: AST write methods absent, blogId 6260634, no BZG/AMG alias, idempotent sync, lanes, snapshot refs, soft fail, UI "Performance reviewed" not "Metricool", secrets absent, 8787 PID, integrity, tables, analyzer contract.

---

## O. Forbidden Actions — Confirmations

- NO Metricool write / schedule / publish / delete  
- NO `metricool_publish` import  
- NO :8787 / wolf-system production edits  
- NO Cloudflare changes  
- NO Obsidian write  
- NO Grok agent changes  
- NO Remotion  
- NO secrets printed / logged / returned in API  
- Phase 1 path still works (soft-fail performance if unavailable)

---

## P. Known Limitations / Honesty

1. **Reels:** Metricool reels endpoint returned **0 rows** for all five brands in the 60d window. Posts+stories imported. Dual-count risk flagging is implemented for when both routes return the same postId.  
2. Stories often have **NULL** engagement — retained as NULL (not zero).  
3. Join key is **blogId** only (label drift ignored).  
4. If Metricool API fails, sync reports `ok=false` with soft errors; planning continues with Performance unavailable.

---

## Q. Files Touched (beta-os only)

- `scripts/metricool_read_client.py` (new)  
- `scripts/sync_metricool_performance.py` (new)  
- `scripts/sync_metricool_habitat.py` (new)  
- `scripts/migrations/002_phase2_metricool.sql` (new)  
- `scripts/migrations/migrate_phase2.py` (new)  
- `scripts/skills/analyze_metricool_performance.py` (new)  
- `scripts/skills/load_metricool_evidence.py` (new)  
- `scripts/skills/build_evidence_pack.py` (new)  
- `scripts/skills/__init__.py`, `build_fortnight_strategy.py`, `load_recent_plans.py`, `load_brand_memory.py`  
- `scripts/wolf_intelligence.py`  
- `scripts/serve_beta.py`  
- `dashboards/content-2.0.html`  
- `scripts/tests/test_phase2_metricool.py` (new)  
- DB: `catalog/content_library.sqlite`

---

## Confirmation Lines

- BACKUPS: YES (`20260915-073339`)  
- SCHEMA: YES  
- HABITAT SYNC: YES (179 rows; oldest=2026-07-21T06:13:22Z; newest=2026-09-14T08:11:35Z)  
- OTHER BRANDS SYNC: YES (atrium/umablu/selo/tropik)  
- EVIDENCE PACK: YES  
- SNAPSHOTS: YES (5)  
- EVIDENCE ITEMS: YES (54)  
- TESTS: PASS=32 FAIL=0  
- 8787 PID UNCHANGED: YES (3758)  
- 8788 = serve_beta: YES (5992)  
- NO SECRETS IN API: YES  
- NO METRICOOL WRITE: YES  
- NO CLOUDFLARE / OBSIDIAN / REMOTION / GROK AGENTS: YES  

*End of Phase 2 Metricool build report.*
