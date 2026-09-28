# LEGACY-1 — Non-HR legacy work discovery + classification

**Owner direction:** Matt, 29 Sep 2026 07:20 · P0 UNIVERSAL MY WORK · HR excluded  
**Mode:** READ-ONLY discovery. No import. No ClickUp/Alchemist/ESB writes. No Beta restart. No edits to `serve_beta.py` / dashboards.

## Outputs

| File | Purpose |
|------|---------|
| `state/legacy/legacy-work-candidates.json` | Every non-HR candidate + classification + provenance |
| `state/legacy/proposed-migration.json` | ACTIVE / OVERDUE / MISSED only, shaped for `core_work_items` (`origin=legacy`) — **not imported** |
| This result | Counts, cut-line, top 20 |

## Sources searched

| Source | Status | Notes |
|--------|--------|-------|
| Wolf-desk `tasks.json` | **found** | 85 tasks (17 open); Matthew-only operator desk |
| ClickUp bridge mirror on wolf-desk | **found** | 10 open assignee IDs refreshed 2026-09-28 (`clickup-inbox.json`); bridge `open_assignee_count=8` / merge kept 8 |
| ClickUp bridge state | **found** | Live sync today 06:59; skipped lists `901820560416`, `901818511985` |
| ClickUp July create log | **found** | 7 tasks created 2 Jul 2026; **no later local status** for most |
| ClickUp desktop IndexedDB | **found, not parsed** | LevelDB binary; used desk mirror instead |
| Amanda / Uma Blu / Mila desks | **found** | 23 / 19 / 2 tasks |
| Notion task-ledger (`task-mirror/task-ledger.db`) | **found** | 443 rows; last_seen max **2026-08-20** (stale vs ClickUp) |
| Alchemist `data/alchemist.db` `pr_orders` | **found** | 504 PRs; live queue |
| Alchemist root `alchemist.db` | **found empty** | 0 tables; live DB is `data/alchemist.db` |
| Vault `BZG-Alchemist-Open-Tasks.md` | **found** | 14 open checkboxes; updated 2026-07-19 |
| Owner TODO md | **found** | 20 unticked; compiled 2026-06-17 |
| Beta `core_work_items` | **found empty** | 0 rows — nothing already in Wolf Core |
| Beta `content_plans` | **found** | 9 plans (3 test / 6 operational already on My Work as `origin=historical`) |
| Contract-tasks ClickUp map | **found — HR skipped** | 48 staff PKWT reminder tasks |
| Briefing tasks May 2026 | **found** | Historical snapshot only |
| `chasing.md` | **not found** | Skill expects `~/.openclaw/wolf-output/chasing.md` — absent |
| Google Drive CloudStorage | **not found** | No Drive sync folder on this Mac |
| Obsidian Task-Log | **found empty** | Directory exists; 0 markdown files |
| Mac Reminders | **container only** | Not parsed (no plaintext export) |
| NAS `05-Wolf-Vault-Mirror` | **mounted** | Shallow scan; no discrete task DB |
| `hr/clickup-tasks.jsonl` | **skipped HR** | Excluded this pass |
| Live ClickUp / Alchemist / prod APIs | **not queried** | Local caches / authorised local DBs only |

## Counts

**Candidates (non-HR):** 1097  
**HR skipped (counts only):** 89 — wolf-desk 6 · notion-ledger 32 · alchemist-open-md 1 · clickup-contract-tasks 48 · briefing 2

| Classification | Count |
|----------------|------:|
| COMPLETE — HISTORY ONLY | 532 |
| OBSOLETE — RETAIN HISTORY | 343 |
| UNKNOWN — REVIEW | 63 |
| MISSED-UNRESOLVED — MIGRATE | 58 |
| ACTIVE — MIGRATE | 57 |
| OVERDUE — MIGRATE | 33 |
| DUPLICATE — LINK-CONSOLIDATE | 11 |

**Proposed migration rows (ACTIVE+OVERDUE+MISSED):** 148 — proposal only, `do_not_import_yet=true`.

Per-source per-class detail is in `legacy-work-candidates.json` → `counts_per_source_per_class`.

## Top 20 active / overdue (plain words)

1. **Connect all emails and calendars** — still open on ClickUp Personal Tasks (live mirror). Owner / Executive · Matthew.
2. **Decide 8 or Simba phone plans** — ClickUp Personal List. Owner · Matthew.
3. **Atrium trucker hat** — ClickUp Sales & Marketing. Owner · Matthew.
4. **Print Core Values** — ClickUp Personal List. Owner · Matthew.
5. **Tips on card processing** — ClickUp Finance & Admin. GGV Finance Operator role · currently on Matthew’s desk.
6. **Atrium lead: EtHan Briffa** — ClickUp GGV Sales Pipeline. Owner · Matthew.
7. **Atrium lead: Kevin Bizien** — same list. Owner · Matthew.
8. **Atrium lead: Oma Oma** — same list. Owner · Matthew.
9. **Atrium lead: Timothy Choi** — same list. Owner · Matthew.
10. **Non-Residential PPJB review for Erick** — ClickUp Atrium list (desk native copy marked DUPLICATE). Owner · Matthew.
11. **Try Eddie AI (free credits / one week selects)** — wolf-desk only. Owner · Matthew.
12. **Mac file-watch + Ollama drafts after 24 Aug** — wolf-desk. Owner · Matthew.
13. **Promo video for room TVs** — Amanda desk, open since late Aug. Content Management · Amanda.
14. **Check Metricool reels and stories counts** — Amanda desk, overdue. Content Management · Amanda.
15. **PR-1500 Kitchen · BU SEPTI awaiting Devi** — Alchemist (SoR stays Alchemist). Head of F&B · Devi.
16. **PR-1501 Bar · Cleo awaiting Devi** — same. Head of F&B · Devi.
17. **PR-1502 Bar · Siani awaiting Devi** — same. Head of F&B · Devi.
18. **PR-1503 Bar · BU SEPTI awaiting Devi** — same. Head of F&B · Devi.
19. **Ads Studio: set Meta credentials** — Amanda desk. Content Management · Amanda.
20. **Cost recipe: Blu Buddha Bowl — Tempeh** — Uma Blu desk costing queue (overlaps Alchemist “cost remaining dishes”). Head of F&B · Devi.

Also queued for migration (not in top 20): 19 Uma Blu recipe-cost rows; Amanda star-review replies; 24 recent Ordered PRs; 58 MISSED-UNRESOLVED (Notion High/Urgent stale + Owner TODO brand/Metricool gaps). Pre-2026-09-15 Alchemist “Awaiting Devi” left as UNKNOWN — REVIEW (stuck; do not auto-resurrect).

## ClickUp cut-line proposal

**Still live on ClickUp (local evidence 28–29 Sep):** the open assignee set mirrored onto wolf-desk — currently the 10 inbox IDs (`86exu7c40`, `86exuxtgv`, `86exvqrw6`, `86exx1kxq`, `86exzzn5a`, `z8wf5rf9ej`, `z8wf5rfh2a`, `z8wf5rfjc9`, `z8wf5rfptv`, `z8wf5rfqa8`). Bridge reports 8 open assignees after merge; inbox lists 10 IDs — treat all 10 as live until a human closes them in ClickUp.

**Must move into Wolf My Work before ClickUp writes stop:** those 10 live open tasks (Owner / Finance / Sales). Staff-facing ClickUp create path (Telegram→ClickUp) must be redirected to Wolf Core work items before write-cutoff. Amanda desk open work that has no ClickUp id should be created in Wolf, not left only on the desk JSON.

**Stays ClickUp read-only history (never delete):** closed/done ClickUp tasks; July 2026 social-report creates whose local status is unknown; skipped lists; HR contract-task list (out of this pass); any ClickUp list not in the open mirror. History retention = keep ClickUp archive + local create logs + desk `status=done` rows.

**Do not treat as live just because found:** Notion ledger “Not started” mass (300 obsolete / 44 missed for review); May briefing snapshot; empty Obsidian Task-Log; July create receipt without status.

## Discipline notes

- People are not roles: every migrate row has `proposed_role` plus `wolf_assigned_person` when Wolf has one.
- Alchemist PRs remain Alchemist system-of-record; migration JSON is a projection proposal only.
- Habitat content plans already project onto My Work as `origin=historical` — classified DUPLICATE / LINK-CONSOLIDATE, not re-imported.
- `core_work_items` stays 0. No import ran.

RESULT: PASS
