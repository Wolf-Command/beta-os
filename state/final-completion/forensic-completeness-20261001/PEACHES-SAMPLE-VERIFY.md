# PEACHES SAMPLE VERIFY — Forensic Wolf Completeness (light)
**as_of:** 2026-10-01T19:03:43+08:00 (WITA)  
**Agent:** Peaches light independent sample  
**Honesty:** sample only · NOT completeness · no thousands crawl · no Matt ping · no Exit Report

## FINAL
- **Verdict:** `PRIOR_UNDERCOUNT_CONFIRMED`
- **Why:** Prior V1-BETA-PARITY-AUDIT audited only 22 surfaces; V1 alone has 55 dashboard HTML files and 23 manifest-registered boards. Surface count and live pulse function density exceed the 22-surface sample.
- **Key numbers:** V1 HTML **55** · manifest registered **23** · Beta HTML **158** · prior parity surfaces **22** · NAS Media shallow **38091** vs Library assets **18** · `:8787` **200** · `:8788` **403** · ORIG asked-path files **0** (sibling **7**) · V1→Beta gap functions listed **12**
- **Paths:** Mac `/Users/wolfterminal/beta-os/state/final-completion/forensic-completeness-20261001/PEACHES-SAMPLE-VERIFY.{md,json}` · Box `/workspace/state/final-completion/forensic-completeness-20261001/PEACHES-SAMPLE-VERIFY.{md,json}`

## 1) V1 board count
- `ls ~/.openclaw/workspace/wolf-system/dashboards/*.html | wc -l` → **55**
- `dashboards/data/manifest.json` registered boards → **23** (generated_at 2026-08-20T17:42:00+08:00)
- Named desks: amanda-desk, mila-desk, peaches-desk, trading-desk, uma-blu-desk, wolf-desk
- wolf-system top dirs (33): amanda-desk, archive, assets, atrium, atrium-finance, briefs, config, content-ideas, content-library, content-machine, dashboards, data, docs, flags, ggv-finance, hr-creatives, hr-reports, hr-uploads, logs, mila-desk, n8n-templates, peaches-desk, profiles, resolve-studio, scripts, state, trading-desk, training-centre, uma-blu, uma-blu-desk, usage, wolf-desk, xero-setup
- Note: file HTML count exceeds manifest registration.

### Manifest ids
| name | title |
|------|-------|
| wolf | Wolf |
| amanda | Amanda |
| mila | Mila |
| spartacus | Spartacus |
| trading | Trading |
| atrium-sales | Atrium — Sales |
| atrium-inventory | Atrium — Inventory |
| hr | HR |
| uma-blu | Uma Blu |
| uma-blu-recipes | Uma Blu — Recipes |
| atrium-management | Atrium — Management |
| legal | Legal |
| content | Content |
| content-goss-group | Content — Goss Group |
| content-habitat | Content — Habitat |
| content-uma-blu | Content — Uma Blu |
| content-atrium | Content — Atrium |
| content-selong-selo | Content — Selong Selo |
| content-tropik | Content — Tropik |
| atrium-finance | Atrium — Finance |
| ggv-finance | GGV Books |
| travel | Travel |
| kuta-rates | Kuta rates |

## 2) Beta board count
- `ls ~/beta-os/dashboards/*.html | wc -l` → **158**
- **Wave 8 retires trading / spartacus / travel from primary Boards:** YES
  - `dashboards/assets/sidenav.js` header: *Wave 8: mila/amanda NOT in primary IA…*
  - Comment: *Wave 8 — retired from primary Boards; soft-redirect handled server-side.*
  - Route-merge plan row 8: specialist trading/travel/spartacus/mila/amanda/kuta-rates → **Retire from primary; keep route**
  - Owner PERSONAL keeps `/owner/trading`, `/owner/fitness` (Spartacus), `/owner/travel`, `/owner/learning` as PARTIAL

## 3) Prior parity audited only 22 surfaces
Quoted from `/workspace/state/final-completion/ux-rescue-20260930/V1-BETA-PARITY-AUDIT.md` (also Mac `~/beta-os/state/final-completion/ux-rescue-20260930/V1-BETA-PARITY-AUDIT.md`):

> Surfaces audited: **22**  
> BETA_BETTER: **5** · BETA_MISSING_FUNCTION: **3** · BETA_MORE_CONFUSING: **2** · PARITY: **5** · V1_BETTER: **5** · V1_OBSOLETE: **2**

Undercount signal: **22 << 55 V1 HTML / 23 manifest / 158 Beta HTML**.

## 4) History — NAS vs Library (stamps only)
From `CONTENT-STACK-TRUTH` + `nas-b2-desk-stamp.json` (as_of ~2026-10-01T08:02 WITA):
- NAS `01-Media-Library` shallow maxdepth3: **38091**
- editable-3: **843** · stock-1: **207**
- Library sqlite: assets **18** · content_cards **153** · plans **9** · brands **1**
- Explicit honesty: Library ≠ NAS Media; `full_tree_indexed=false`
- No full NAS walk this sample.

## 5) Live HTTP
| port | URL | status |
|------|-----|--------|
| 8787 | http://127.0.0.1:8787/ | **200** |
| 8788 | http://127.0.0.1:8788/ | **403** (CF Access expected) |

## 6) ORIGINAL-REQUIREMENTS-RECONSTRUCTION
- Asked path `~/beta-os/ORIGINAL-REQUIREMENTS-RECONSTRUCTION`: **0 files** (empty dir)
- Content lives at `~/beta-os/state/final-completion/ORIGINAL-REQUIREMENTS-RECONSTRUCTION`: **7 files**
  - 01-INTERVIEW-LEDGER-LOCKED-REQUIREMENTS.json
  - 02-MASTER-BUILD-BACKLOG.json
  - 03-MASTER-SPEC-FULL.md
  - 03-MASTER-SPEC-SECTION-INDEX.json
  - 04-GAP-REGISTER-CLASS-SEED.json
  - 05-DRIVE-ULTIMATE-MASTER-PLAN-CITATION.json
  - requirements.jsonl

## 7) ≥10 concrete V1 functions Owner Home lacks or only shells
Sources: `wolf.html` + `master.status.json` (14 tiles @ 2026-10-01T18:44:57+08:00) vs Beta `owner-empire-pack` / `owner-*-1` PARTIAL pages.

| # | V1 function | Beta gap |
|---|-------------|----------|
| 1 | Live multi-tile Owner pulse from master.status.json (14 tiles) | owner-empire-pack pulse-strip; local :8788 CF 403 without JWT; capability fragmented |
| 2 | Atrium occupancy live tile (1.75% occ → atrium-sales.html) | AMG prove/ops sprawl; no single unauth Owner Home occ glance |
| 3 | Kuta rates tonight competitor intel tile + board | kuta-rates-1 / competitor-rates prove; Wave 8 retired primary IA |
| 4 | BZG last-night revenue + covers pulse | BZG pages exist; not same one-glance Owner pulse |
| 5 | Leads 24h by brand on Owner Home | CRM/lead prove packs ≠ Home live tile |
| 6 | Purchasing open PRs + supplier count tile | No matching Owner Home purchasing pulse in empire pack |
| 7 | Alchemist owe/paid/tin/broken live numbers | Not present as Owner Home live tile |
| 8 | Backup B2 capacity + R2 backup gap tiles | backup-health-1 / restore-drill prove — not Home dual tiles |
| 9 | Spartacus 75 day counter + Open Spartacus from Diet/workouts | owner-fitness-1.html migration_state PARTIAL |
| 10 | Talk to Peaches / Tell Peaches task comments on wolf desk | No interactive Peaches desk thread on Beta Owner Home |
| 11 | Owner desk rails: Asks / Needs you / Read-View / Shareholders | owner-needs-you-1 separate; not multi-rail cockpit |
| 12 | Trading desk real workspace vs PARTIAL paper RO | Wave 8 retired primary; /owner/trading PARTIAL shell |

### master.status.json tile keys (14)
money, brief, atrium, kutarates, bzg, content, leads, hr, purchasing, alchemist, system, backup, r2gap, spartacus

---
*Sample evidence only. Does not claim Beta or V1 completeness.*
