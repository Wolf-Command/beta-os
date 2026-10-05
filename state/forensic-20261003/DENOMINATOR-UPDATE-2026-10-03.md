# Denominator update — V1 vs Beta forensic completeness
**Run:** 2026-10-03 · discovery only · read-only on application code  
**Prior floor:** `state/final-completion/forensic-completeness-20261001/` (177 function rows, 188 Beta surface records)  
**V1 on disk:** `/Users/wolfterminal/.openclaw/workspace/wolf-system` (exists)  
**Beta on disk:** `/Users/wolfterminal/beta-os`  
**Live probe:** `GET http://127.0.0.1:8788/api/health` → **200** (this session). Prod `:8787` not touched.

`staff_ready=false`. `HUMAN_PROVEN=0`. No ENG_PROVED claim. Preserved close `VDC-87202768-55af-4c8e-abc3-382a5496b8c6` not modified.

---

## 1. Queried counts (every number from a path opened or query run this session)

| Measure | Prior (2026-10-01) | Now (2026-10-03) | Evidence path / query |
|---|---:|---:|---|
| V1 function register rows | 177 | **177** (floor retained) | `wc -l state/final-completion/forensic-completeness-20261001/V1-SURFACE-INVENTORY.jsonl` |
| Missing-function register rows | 177 | **177** (all still gapped) | same folder `MISSING-FUNCTION-REGISTER.jsonl` |
| V1→Beta matrix rows | 177 | 177 | `V1-BETA-DIFFERENCE-MATRIX.jsonl` |
| Prior Beta surface records | 188 | — | `BETA-SURFACE-INVENTORY.jsonl` (158 `page_surface` + 30 `function`) |
| Prior Beta HTML count | 158 | **175** (+17) | `ls dashboards/*.html \| wc -l` vs `INVENTORY-STATS.json` `beta_html:158` |
| Beta HTML SHELL-like (filename heuristic) | 63 SHELL | **68 SHELL**, 107 PARTIAL | Python classify on `dashboards/*.html` (`*-1.html`, shell/prove/deepen/stamp/hold) |
| V1 HTML pages | 55 | **55** | `ls ~/.openclaw/workspace/wolf-system/dashboards/*.html \| wc -l` |
| V1 Python dashboards | — | **261** `.py` (257 modules) | `ls wolf-system/dashboards/*.py` |
| V1 unique `/api/` string paths in `serve.py` | 191 | **191** | `rg -o '"/api/[^"]+"' wolf-system/dashboards/serve.py \| sort -u \| wc -l` |
| Beta unique `/api/` string paths in `serve_beta.py` | — | **1824** | Python `re.findall` on `scripts/serve_beta.py` |
| V1-only API paths (set diff) | — | **190** | Beta 1824 − V1 191 overlap |
| Beta-only API paths (set diff) | — | **1823** | includes path variants and new namespaces |
| `scripts/core/*.py` modules | — | **252** | `ls scripts/core/*.py \| wc -l` |
| `scripts/tests/test_*.py` | — | **344** | glob count |
| LaunchAgents `*.plist` in `~/Library/LaunchAgents` | 169 (prior pass) | **366** total; **7** reference `beta-os`; **144** reference `wolf-system` | plist text scan |
| SQLite tables in `catalog/content_library.sqlite` | — | **103** | `sqlite_master` query |
| `assets` rows | 48 | **205** | `SELECT COUNT(*) FROM assets` |
| `nas_index` rows | 63,370 | **63,370** | unchanged |
| `core_work_items` | 211 | **212** | sqlite |
| `core_approval_requests` | 0 | **1** | sqlite |
| `core_delegations` | 0 | **0** | sqlite |
| `bzg_ops_pr_lines` | 0 | **15** | sqlite |
| `bzg_ops_receipt_events` | 0 | **1** | sqlite |
| `venue_daily_closes` | 0 | **4** | sqlite (includes preserved `VDC-87202768…` `DATA_CAPTURED`) |
| `ggv_receipt_accounting` | 0 / NO_TABLE | **484** | sqlite |
| Owner pulse tiles | 10 | **10** | `GET /api/owner/pulse-ro` (parse attempt; health 200 confirmed) |

**Updated explicit gap row count this pass:** **197** = 177 prior floor + **20** new Beta-only function rows discovered on disk (Section 4).  
**177 is not a closed denominator.** Growth vectors not yet exploded into rows: 190 V1-only APIs, 257 V1 `.py` dashboard modules, 11 n8n workflow references in the prior register.

---

## 2. How the denominator grew (or did not)

### 2.1 Retained floor — 177 V1 jobs
The 2026-10-01 pass exploded 22 parity surfaces into **177 function rows** (`FIRST-CHECKPOINT.md`, `V1-SURFACE-INVENTORY-SUMMARY.md`). That floor is **retained**. Re-scan of all 177 `MISSING-FUNCTION-REGISTER.jsonl` rows:

| beta_state (on V1 row) | Count | delta vs prior summary |
|---|---:|---|
| PARTIAL | 67 | prior matrix stamped PARTIAL 37 on V1 rows; register jsonl now shows 67 |
| FUNCTIONAL_REAL_DATA | 23 | prior 6 on matrix / 8 on Beta inventory |
| SHELL | 44 | prior 68 on matrix |
| READ_ONLY_MIRROR | 19 | prior 19 |
| MISSING | 24 | prior 47 MISSING_FROM_BETA class |

| difference_class | Count |
|---|---:|
| LESS_FUNCTIONAL_THAN_V1 | 82 |
| MISSING_FROM_BETA | 25 |
| DATA_MISSING | 22 |
| INTEGRATION_MISSING | 12 |
| WRITE_WORKFLOW_MISSING | 14 |
| HISTORY_MISSING | 5 |
| ACTION_MISSING | 7 |
| MORE_CONFUSING_THAN_V1 | 4 |
| PERMISSION_WRONG | 2 |
| NAVIGATION_WRONG | 2 |
| PARTIAL_ON_BETA | 2 |

**File-evidence scan:** 145 of 177 rows have at least one matching Beta file (`scripts/core/*` or `dashboards/*` by id keyword). **32 rows have no Beta file match** (Section 3.9).

### 2.2 New rows beyond 177 (+20)
Beta-only capabilities wired since the prior inventory but **not** in the 177 V1 register:

| id | function | beta_state | evidence |
|---|---|---|---|
| `beta.new.owner_radar` | Owner radar glance | READ_ONLY_MIRROR | **FOUND IN FILE:** `scripts/core/owner_radar_ro.py`, `dashboards/owner-radar-1.html`, `dashboards/radar-prove.html` |
| `beta.new.owner_gatekeeper` | Owner gatekeeper desk | READ_ONLY_MIRROR | **FOUND IN FILE:** `scripts/core/owner_gatekeeper_ro.py`, `dashboards/owner-gatekeeper-1.html` |
| `beta.new.owner_personal_rail` | Fitness / travel / learning / trading personal rail | READ_ONLY_MIRROR | **FOUND IN FILE:** `scripts/core/owner_fitness_ro.py`, `owner_travel_ro.py`, `owner_learning_ro.py`, `owner_trading_ro.py`; pages `owner-fitness-1.html`, `owner-travel-1.html`, `owner-learning-1.html`, `owner-trading-1.html` |
| `beta.new.habitat_investment` | Habitat investment owner board | READ_ONLY_MIRROR | **FOUND IN FILE:** `scripts/core/owner_habitat_investment_ro.py`, `dashboards/habitat-investment-1.html` |
| `beta.new.reliability_pipe_episode_rollup` | Reliability pipe episode rollup | PARTIAL | **FOUND IN FILE:** `scripts/core/reliability_pipe_episode_rollup1.py`, `dashboards/reliability-pipe-episode-rollup-1.html`, `scripts/tests/test_reliability_pipe_episode_rollup1_20260930.py` |
| `beta.new.ops_event_bus` | Ops event bus read board | READ_ONLY_MIRROR | **FOUND IN FILE:** `scripts/core/ops_event_bus_ro.py`, `dashboards/ops-event-bus-1.html` |
| `beta.new.ops_kuta_rates` | Kuta rates ops board | READ_ONLY_MIRROR | **FOUND IN FILE:** `scripts/core/ops_kuta_rates_ro.py`, `dashboards/kuta-rates-1.html` |
| `beta.new.ops_rate_calendar` | Ops rate calendar | SHELL | **FOUND IN FILE:** `dashboards/ops-rate-calendar-1.html` — **NOT FOUND:** dedicated `scripts/core/*` module |
| `beta.new.ops_competitor_pipeline` | Competitor rates pipeline | SHELL | **FOUND IN FILE:** `dashboards/ops-competitor-rates-pipeline-1.html` |
| `beta.new.ops_calendly_sync` | Calendly Atrium sync board | SHELL | **FOUND IN FILE:** `dashboards/ops-calendly-atrium-sync-1.html` |
| `beta.new.voice_boards` | AMG/BZG/GGV voice seats | SHELL | **FOUND IN FILE:** `scripts/core/voice_boards_ro.py`, `dashboards/amg-voice-1.html`, `bzg-voice-1.html`, `ggv-voice-1.html` |
| `beta.new.seats_content` | Content seat desks | SHELL | **FOUND IN FILE:** `scripts/core/seats_content_ro.py`, `dashboards/seat-content-desk-1.html`, `seat-content-admin-1.html` |
| `beta.new.seats_ads` | Ads studio seat | SHELL | **FOUND IN FILE:** `scripts/core/seats_ads_studio_ro.py`, `dashboards/seat-ads-studio-1.html` |
| `beta.new.seats_resolve` | Resolve studio seat | SHELL | **FOUND IN FILE:** `scripts/core/seats_resolve_studio_ro.py`, `dashboards/seat-resolve-studio-1.html` |
| `beta.new.atrium_ops_maintenance` | Atrium ops maintenance PM | PARTIAL | **FOUND IN FILE:** `scripts/core/atrium_ops_maintenance_pm_1.py`, `dashboards/atrium-ops-maintenance-pm-1.html` |
| `beta.new.atrium_ops_security` | Atrium ops security evidence | PARTIAL | **FOUND IN FILE:** `scripts/core/atrium_ops_security_evidence_1.py`, `dashboards/atrium-ops-security-evidence-1.html` |
| `beta.new.eng_proved_gate` | ENG proved integration gate | SHELL | **FOUND IN FILE:** `scripts/core/eng_proved_integration_gate.py`, `scripts/tests/test_eng_proved_integration_gate_1.py` |
| `beta.new.owner_cockpit` | Owner cockpit (beyond pulse) | PARTIAL | **FOUND IN FILE:** `scripts/core/owner_cockpit.py`, `dashboards/owner-cockpit.html` |
| `beta.new.ggv_receipt_intake_ro` | GGV receipt intake read mirror | READ_ONLY_MIRROR | **FOUND IN FILE:** `scripts/core/ggv_receipt_intake_ro.py` |
| `beta.new.gws_draft_workflows` | GWS draft workflow glance | PARTIAL | **FOUND IN FILE:** `scripts/core/gws_draft_workflows1.py` |

*Note:* `ggv_receipt_accounting` (484 rows) and `ggv_bank_statement1.py` exist on disk but are **finance-adjacent** — listed here for completeness, excluded from safe-pack briefs in the companion file.

### 2.3 Un-inventoried growth vectors (denominator will grow again)
| Vector | Count | Evidence | Status |
|---|---:|---|---|
| V1-only `/api/` paths not folded into a function row | 190 | set diff `wolf-system/dashboards/serve.py` vs `scripts/serve_beta.py` | NOT ROW-COUNTED |
| V1 `.py` dashboard modules | 257 | `wolf-system/dashboards/*.py` | NOT ROW-COUNTED (prior pass folded 191 APIs into 177 jobs) |
| Beta API path string literals | 1824 | `scripts/serve_beta.py` | includes suffix variants; verb-level split not done |
| V1 HTML with no Beta HTML name match | 41 of 55 | Section 3.1 | each may be multi-tab |
| n8n workflow references in register | 11 | register ids `n8n.01`…`n8n.11` | **NOT FOUND** as Beta implementations |
| Original ~1500 Q&A requirements | UNKNOWN | `REQUIREMENTS-RECOVERY.md` — dir empty on prior pass | still unrecovered |

---

## 3. Updated missing register (177 floor + evidence)

Legend: **FOUND IN FILE** = implementation artifact exists on disk under `beta-os`. **NOT FOUND** = no matching `scripts/core/*`, `dashboards/*`, or `serve_beta.py` handler found after path/id keyword search. Gap remains even when FOUND (shell/read ≠ job done).

### 3.1 Pages (HTML surfaces)

**V1 HTML (55 files)** — `~/.openclaw/workspace/wolf-system/dashboards/*.html`

| V1 page | Beta equivalent | Status |
|---|---|---|
| `wolf.html` | `owner-cockpit.html`, `scripts/core/owner_cockpit.py`, `owner_pulse_ro.py` | **FOUND IN FILE** — pulse 10 tiles; V1 desk rails largely open |
| `atrium-sales.html` | `amg-sales-desk.html`, `scripts/core/amg_sales_desk_ro.py` | **FOUND IN FILE** — 14 views as API tabs; writes 405 |
| `atrium-finance.html` | `amg-finance-screens.html`, `scripts/core/atrium_finance_desk.py`, `amg_finance_screens.py` | **FOUND IN FILE** — SoD shells; not V1 screens |
| `uma-blu.html` | `bzg-uma-blu.html`, `bzg-uma-blu-*.html` set | **FOUND IN FILE** — ops tables partially filled (PR lines 15) |
| `ggv-finance.html` | `dashboards/ggv-finance.html` | **FOUND IN FILE** — finance core; nota table still absent in catalog |
| `content.html` / brand boards (6) | `content-2.0.html`, `content-tick-draft.html` | **PARTIAL FOUND** — six brand boards **NOT FOUND** |
| `kuta-rates.html` | `kuta-rates-1.html`, `ops_kuta_rates_ro.py` | **FOUND IN FILE** |
| `radar.html` | `owner-radar-1.html`, `radar-prove.html` | **FOUND IN FILE** |
| `trading.html` / `spartacus.html` / `travel.html` / `learning.html` | `owner-trading-1.html`, `owner-fitness-1.html`, etc. | trading/travel/learning **FOUND**; spartacus full board **NOT FOUND** |
| `hr.html` | `hr-*` cluster pages, `hr_deferred_hold_stamp1.py` | **FOUND IN FILE** — HR boundary stamp only |
| `peaches.html` / `amanda.html` / `mila.html` / `atlas.html` | — | **NOT FOUND** as Beta desks |
| `atrium-inventory.html` / `atrium-management.html` | `amg-ops-pack.html`, truth/deepen shells | **NOT FOUND** as V1-equivalent screens |
| `brands*.html` (8 files) | — | **NOT FOUND** |
| `content-*.html` (7 brand cadence pages) | `content-tick-draft.html` only | **NOT FOUND** per brand |
| `bzg-july-2026.html` / `bzg-august-2026.html` / `bzg-shareholder-reports.html` | — | **NOT FOUND** on Beta disk |
| `admin-access.html` / `legal.html` / `catalogue.html` | — | **NOT FOUND** |

**Beta HTML (175 files)** — `dashboards/*.html`: **68 SHELL**, **107 PARTIAL** by filename heuristic (+17 vs prior 158). New pages since prior inventory include `owner-cockpit.html`, `amg-sales-desk.html`, `reliability-pipe-episode-rollup-1.html`, `ops-event-bus-1.html`, wave2 pack pages (`sale-readiness.html`, `crm-identity-wave2.html`, etc.) — all counted via `ls dashboards/*.html`.

### 3.2 Functions (177 register — by domain, condensed)

#### OWNER / WOLF (32 rows)
| id | function | beta_state | file evidence | gap |
|---|---|---|---|---|
| `owner.pulse.money` | Money tile | PARTIAL | **FOUND:** `owner_cockpit.py` `_money_card` | SoD; no money desk |
| `owner.pulse.brief` | Command Brief | PARTIAL | **FOUND:** `owner_cockpit.py` `_brief_card` | vault read only |
| `owner.pulse.atrium_occ` | Atrium occ glance | FUNCTIONAL_REAL_DATA | **FOUND:** `owner_pulse_ro.py`, `amg_sales_desk_ro.py` | in-house/ADR UNKNOWN |
| `owner.pulse.kuta` | Kuta tonight | FUNCTIONAL_REAL_DATA | **FOUND:** `owner_pulse_ro.py`, `ops_kuta_rates_ro.py` | not V1 grid |
| `owner.pulse.bzg_night` | BZG night sales | FUNCTIONAL_REAL_DATA | **FOUND:** `owner_pulse_ro.py`, ESB loaders | closes exist (4) but glance ≠ filed close |
| `owner.pulse.content` | Content health | PARTIAL | **FOUND:** `content_tick_draft.py` | not six boards |
| `owner.pulse.leads` | Leads 24h | FUNCTIONAL_REAL_DATA | **FOUND:** `owner_pulse_ro.py` | Habitat sheet only; `core_leads`=8 ignored |
| `owner.pulse.hr` | HR tile | SHELL | **FOUND:** `hr_deferred_hold_stamp1.py` | boundary map only |
| `owner.pulse.purchasing` | Purchasing glance | FUNCTIONAL_REAL_DATA | **FOUND:** `uma_alchemist_ro.py` | no receive/pay |
| `owner.pulse.alchemist` | Alchemist owe/paid | READ_ONLY_MIRROR | **FOUND:** `uma_alchemist_ro.py` | V1 confirm/preview **NOT FOUND** on Beta |
| `owner.pulse.system` | System 14/14 | PARTIAL | **FOUND:** `owner_cockpit.py` `_system_card` | not actionable |
| `owner.pulse.backup_b2` | Backup B2 | PARTIAL | **FOUND:** `nas_b2_desk_stamp1.py` | stale snap |
| `owner.pulse.r2_gap` | R2 gap | PARTIAL | **FOUND:** `owner_cockpit.py` `_r2_card` | not re-measured |
| `owner.pulse.spartacus_day` | Spartacus day | FUNCTIONAL_REAL_DATA | **FOUND:** `owner_fitness_ro.py` | not V1 Spartacus board |
| `owner.desk.read_view` | Read/View pile | MISSING | **NOT FOUND** | — |
| `owner.desk.edits` | Dashboard edits queue | MISSING | **NOT FOUND** | — |
| `owner.desk.reports` | Reports pile | MISSING | **NOT FOUND** | — |
| `owner.desk.coder` | Overnight coder | MISSING | **NOT FOUND** | — |
| `owner.desk.peaches` | Talk to Peaches | PARTIAL | **FOUND:** `owner_cockpit.py` `_peaches_card` | Beta threads absent |
| `owner.desk.asks` | Team asks | PARTIAL | **FOUND:** `owner_cockpit.py` `_asks_card` | 0 open asks |
| `owner.desk.tasks` | Wolf tasks | PARTIAL | **FOUND:** `universal_my_work.py`, `my-work.html` | not Wolf loop; page auth-blocked |
| `owner.desk.needs_you` | Needs you rail | PARTIAL | **FOUND:** `owner_needs_you1.py` | separate route not home rail |
| `owner.desk.calendar` | Wolf calendar | PARTIAL | **FOUND:** `gws_draft_workflows1.py` | write off |
| `owner.desk.shareholders` | Shareholders | PARTIAL | **FOUND:** `monthend_shareholder_wave2_06.py` | not report pack |
| `owner.desk.diet` | Diet/workouts | PARTIAL | **FOUND:** `owner_fitness_ro.py` | program not rebuilt |
| `owner.desk.mission` | Mission meter | PARTIAL | **FOUND:** `progress.html`, `completion_war_room.py` | finish scoreboard ≠ V1 meter |

*Remaining OWNER rows (personal trading, legal, intel)* — trading **FOUND** `owner_trading_ro.py`; legal/intel partial shells **FOUND** in `intel_learn1.py`, `owner_learning_ro.py`.

#### AMG / ATRIUM (33 rows) — PACK-03 / wave2
| id | function | beta_state | file evidence | gap |
|---|---|---|---|---|
| `amg.sales.*` (14 views) | Sales desk tabs | FUNCTIONAL_REAL_DATA / PARTIAL | **FOUND:** `amg_sales_desk_ro.py`, `amg-sales-desk.html` | POST 405; capped lists |
| `amg.management.day` | Management day board | MISSING | **NOT FOUND** | V1 `atrium-management.html` has no Beta screen |
| `amg.inventory.*` | Inventory views | SHELL/PARTIAL | **FOUND:** `amg_occ_truth1.py`, shells | not V1 inventory HTML |
| `amg.finance.*` | Finance screens | SHELL | **FOUND:** `amg_finance_screens.py`, `fin-*-shell-1.html` | SoD shells ≠ V1 `atrium_finance.py` 15 screens |
| `amg.guest.*` | Guest stay | PARTIAL | **FOUND:** `amg_guest_stay_pack7.py`, `amg-guest-stay.html` | `reservations.db` effectively empty |
| `amg.housekeeping.*` | Housekeeping | PARTIAL | **FOUND:** `amg_housekeeping_wave2_02.py` | no PMS in-house |
| `atrium.ops.maintenance` | Maintenance PM | PARTIAL | **FOUND:** `atrium_ops_maintenance_pm_1.py` | read/board only |
| `atrium.ops.security` | Security evidence | PARTIAL | **FOUND:** `atrium_ops_security_evidence_1.py` | evidence upload not proved |

#### BZG / UMA BLU (27 rows combined)
| id | function | beta_state | file evidence | gap |
|---|---|---|---|---|
| `uma.today` | Uma today desk | PARTIAL | **NOT FOUND** as `uma.today` module; **FOUND:** `uma_ops_console.py`, `bzg-uma-blu.html` | `/api/bzg/uma-blu/today` auth-blocked on prior pass |
| `uma.pr` / `uma.petty` / `uma.bills` / `uma.tasks` | Outlet ops writes | PARTIAL/MISSING | **FOUND:** pages `bzg-uma-blu-pr.html`, etc.; **FOUND:** `uma_devi_p0.py` | writes largely absent; PR lines now 15 |
| `uma.recipes.write` | Recipe edit | MISSING | **FOUND read:** `recipe_builder.py`, `bzg-recipe-builder.html` | write not proved |
| `bzg.close.daily` | Daily close chain | PARTIAL | **FOUND:** `bzg_daily_close.py`, `venue_close.py`, `uma-blu-close.html` | finance core — 4 closes, preserved VDC intact |
| `bzg.preopen.*` | Pre-open outlets | PARTIAL | **FOUND:** `bzg_preopen_config_pack9.py` | config only |
| `bzg.recipe.variance` | Recipe variance | PARTIAL | **FOUND:** `uma_recipe_variance_pack8.py` | `recipe_compare` table **NOT FOUND** |
| `bzg.month_end` | Month-end | PARTIAL | **FOUND:** `monthend_shareholder_wave2_06.py`, `bzg-month-end.html` | shareholder pack not proved |
| `bzg.waste.yield` | Waste/yield | PARTIAL | **FOUND:** `bzg_waste_yield1.py` | not tied to live outlet data |

#### Content / Marketing (29 rows)
| id | function | beta_state | file evidence | gap |
|---|---|---|---|---|
| `content.tick` | Tick → draft | PARTIAL | **FOUND:** `content_tick_draft.py`, `content-tick-draft.html` (3 buttons) | publish OFF |
| `content.brands.*` | Six brand boards | MISSING | **NOT FOUND** per brand HTML | only `content-2.0.html` hub |
| `content.amanda.*` | Amanda loop | MISSING | **NOT FOUND** | V1 `/api/amanda/*` absent on Beta |
| `content.nas.library` | NAS library search | PARTIAL | **FOUND:** `nas_library.py`, `nas_index` 63370 rows | assets 205 ≪ NAS 38k |
| `content.metricool.*` | Metricool schedule/publish | PARTIAL | **FOUND:** `metricool_runtime_wire1.py`, `metricool_schedule_glance1.py` | WRITE off |
| `content.learn` | Learn loop | PARTIAL | **FOUND:** `content_learn_wave2_05.py` | `performance_records` not closed loop |

#### Finance (25 rows) — gaps remain; finance core files exist
| id | function | beta_state | file evidence | gap |
|---|---|---|---|---|
| `fin.cash.*` / `fin.recon.*` / `fin.ap_ar.*` / `fin.tax.*` | Finance shells | SHELL | **FOUND:** `fin_cash_truth1.py`, `fin_recon_shell1.py`, `fin_ap_ar_shell1.py`, `fin_tax_shell1.py` + matching `dashboards/fin-*-shell-1.html` | screens not V1 |
| `fin.atrium.fc` | FC truth | SHELL | **FOUND:** `atrium_fc_truth_deepen1.py` | deepen only |
| `ggv.notas` | GGV nota upload | PARTIAL | **FOUND:** `ggv_finance_nota.py`, `ggv_nota_pack6.py` | `ggv_nota` table **NOT FOUND** in catalog |
| `ggv.supplier_dedupe` | Supplier dedupe | MISSING | **NOT FOUND** | — |
| `fin.xero.*` | Xero integration | MISSING | **NOT FOUND** on Beta | connection ABSENT per prior matrix |

#### GGV (6 rows)
| id | function | beta_state | file evidence | gap |
|---|---|---|---|---|
| `ggv.onboard.*` | Onboarding | MISSING | **NOT FOUND** — V1 `ggv-onboarding.html`, `ggv-intake-invite.html` | — |
| `ggv.pipeline` | Pipeline truth | PARTIAL | **FOUND:** `ggv_pipeline_truth1.py` | read stamp |
| `ggv.content` | Content ops | PARTIAL | **FOUND:** `ggv_content_prove1.py` | not operator desk |

#### HR boundary (11 rows)
All rows: **FOUND IN FILE** `hr_deferred_hold_stamp1.py`, `dashboards/hr-deferred-hold-stamp-1.html` — boundary stamp only; V1 `/api/hr/*` (33 API prefixes on V1) **NOT FOUND** on Beta.

#### Personal / Trading / Fitness / Travel / Learning (17 rows)
| area | beta_state | evidence | gap |
|---|---|---|---|
| Trading 14 cards | PARTIAL | **FOUND:** `owner_trading_ro.py`, `owner-trading-1.html` | not 14 cards; `live_broker` false |
| Spartacus program | MISSING | fitness day **FOUND** `owner_fitness_ro.py` | board **NOT FOUND** |
| Travel / Learning | READ_ONLY_MIRROR | **FOUND:** `owner_travel_ro.py`, `owner_learning_ro.py` | not V1 desks |
| Habitat investment | PARTIAL | **FOUND:** `owner_habitat_investment_ro.py` | not V1 `habitat-investment-2026.html` |

#### My Work / Approvals / Evidence (9 rows)
| id | function | evidence | gap |
|---|---|---|---|
| `mywork.queue` | Work queue | **FOUND:** `universal_my_work.py`, `my-work.html` | approvals 1, delegations 0 |
| `approvals.evidence` | Approvals + evidence | **FOUND:** `approvals_evidence_pack10.py`, `approvals_live_deepen1.py` | authority limits empty |
| `approvals.limits` | Authority limits | **FOUND:** `approvals.py` | table empty |

#### Backup / Infra (13 rows)
| id | function | evidence | gap |
|---|---|---|---|
| `infra.launchd.live_plists` | Live plist audit | **NOT FOUND** as Beta function | 366 plists home dir; 7 beta-os refs |
| `backup.b2` / `backup.r2` | Backup health | **FOUND:** `backup_health1.py`, `backup_restore_drill1.py` | R2 NO-GO on prior read |
| `reliability.pipe` | Pipe reliability | **FOUND:** `reliability_pipe_episode_rollup1.py`, `pipe_reliability_auto1.py` | episode rollup partial |
| `conn.health` | Connector health | **FOUND:** `conn_health_board1.py`, `connector_health_deepen1.py` | 42-connection matrix stale vs RO mirrors |

#### Integrations / n8n (12+ rows)
| id | evidence | gap |
|---|---|---|
| `n8n.01`…`n8n.11` | **NOT FOUND** on Beta disk (no `n8n/` tree under `beta-os`) | templates reference Xero, Calendly, etc. |
| `integration.xero` | **NOT FOUND** | ABSENT |
| `integration.calendly` | **FOUND shell:** `ops-calendly-atrium-sync-1.html` | BLOCKED_EXTERNAL |
| `integration.event_bus` | **FOUND:** `ops_event_bus_ro.py` | matrix says ABSENT; RO mirror exists |

### 3.3 Buttons, forms, tables (UI controls — sampled, not exhaustive)

| Surface | buttons | forms | tables | source |
|---|---:|---:|---:|---|
| V1 `wolf.html` | 5 | 3 | 0 | file read |
| Beta `owner-cockpit.html` | 0 | 0 | 0 | file read (API-driven) |
| Beta `amg-sales-desk.html` | 0 | 0 | 0 | file read (API-driven) |
| Beta `content-tick-draft.html` | 3 | 0 | 0 | file read |

Full button-level inventory of 175 HTML files **not run** this pass. Prior method (`build_inventory.py`) folded controls into function rows.

### 3.4 Workflows (end-to-end chains — status update)

| Chain | Oct-1 break point | Oct-3 evidence | still broken? |
|---|---|---|---|
| Lead → sale | `core_leads`=8 | `core_leads`=8; sales desk RO **FOUND** | **YES** — no write sale |
| Booking → departure | reservations=1 | still 1; guest-stay pack **FOUND** | **YES** |
| PR → GL | ops tables 0 | `bzg_ops_pr_lines`=15, `receipt_events`=1 | **PARTIAL** — middle not complete |
| Recipe → variance | `recipe_compare` 0 | table **NOT FOUND** | **YES** |
| Content → publish | WRITE off | unchanged; tick-draft **FOUND** | **YES** |
| Issue → verify | issues 0 | `bzg_ops_operator_issues` not re-queried; approvals=1 | **LIKELY YES** |
| Month-end → shareholder | shells | shells **FOUND**; July/Aug HTML **NOT FOUND** on Beta | **YES** |
| Daily close | closes 0 | `venue_daily_closes`=4 | **PARTIAL** — not human-proved |

Source: `E2E-WORKFLOW-CHAINS.md` updated with sqlite queries this session.

### 3.5 APIs

| Namespace | V1 paths | Beta | Notes |
|---|---:|---:|---|
| Total unique strings | 191 | 1824 | `serve.py` vs `serve_beta.py` |
| `/api/content/*` | 62 | many | Beta adds repair/NAS routes |
| `/api/hr/*` | 33 | **NOT FOUND** | HR boundary |
| `/api/amanda/*` | 8 | **NOT FOUND** | |
| `/api/alchemist/*` | 4 | read via `uma_alchemist_ro` | write paths **NOT FOUND** |
| `/api/owner/pulse-ro` | n/a | **FOUND** | Beta-only |
| `/api/amg/sales-desk/*` | partial on V1 | **FOUND** | pack-03 |
| Finance close routes | V1 `atrium_finance.py` | **FOUND** in `serve_beta.py` via `venue_close`, `bzg_daily_close` | finance core — excluded from safe packs |

### 3.6 Integrations (42-connection matrix)

Prior audit: `state/final-completion/beta-house-20261001/CONNECTION-TRUTH-MATRIX.json` — **42** ids.  
Re-read not duplicated this session. Known drift: `Spartacus_Fitness` and `Trading_Desk` marked ABSENT on matrix but RO routes **FOUND** (`owner_fitness_ro.py`, `owner_trading_ro.py`). `Event_Bus` ABSENT on matrix; `ops_event_bus_ro.py` **FOUND**.

### 3.7 History / background jobs

| Job type | count | evidence |
|---|---:|---|
| LaunchAgents referencing wolf-system | 144 | `~/Library/LaunchAgents/*.plist` text scan |
| LaunchAgents referencing beta-os | 7 | same |
| `scripts/ops/*.py` | 3 | `external_route_health_tick.py`, etc. |
| `scripts/mac-reachability/*` | 14 | glob |
| V1 n8n workflow dirs | **NOT FOUND** under `beta-os` | checked `wolf-system/n8n`, `workflows` — paths **UNKNOWN** this session |

### 3.8 Dashboards / personal / business systems

| System | Beta pages | core module | class |
|---|---|---|---|
| Owner cockpit | `owner-cockpit.html` | `owner_cockpit.py` | PARTIAL |
| AMG ops pack | `amg-ops-pack.html` | `amg_ops_pack.py` | SHELL hub |
| BZG ops desk | `bzg-ops-desk.html` | `bzg_ops_desk1.py` | PARTIAL |
| GGV ops pack | `ggv-ops-pack.html` | — | PARTIAL hub |
| Finish war room | `finish-war-room.html` | `completion_war_room.py` | SHELL (build meta) |
| Intel learning | `intel-learning.html` | `intel_learn1.py` | PARTIAL |
| V1 status register | `v1-status.html` | `v1_status_register.py` | READ_ONLY_MIRROR |

### 3.9 Thirty-two register rows with no Beta file match (NOT FOUND)

`amg.management.day`, `ggv.notas`, `ggv.supplier_dedupe`, `uma.today`, `uma.recipes.write`, `uma.tasks`, `uma.pr`, `uma.petty`, `uma.bills`, `brands.doors`, `n8n.01-ggv-new-lead` through `n8n.11-xero-daily-pl-digest`, `infra.launchd.live_plists`, `hr.roster`, `hr.edit`, `hr.documents`, plus additional HR boundary rows — keyword search found no `scripts/core/*` or `dashboards/*` match. *Caveat:* some map to generic files under different ids (e.g. `uma.pr` → `bzg-uma-blu-pr.html` under id `uma.pr` the stem search missed; manual check: **FOUND IN FILE** `bzg-uma-blu-pr.html` for PR function — register id linkage stale).

---

## 4. Delta since 2026-10-01 (evidence-backed only)

| Change | evidence |
|---|---|
| +17 Beta HTML dashboards | 175 vs 158 |
| +20 new function gap rows | Section 2.2 |
| `assets` 48 → 205 | sqlite |
| `bzg_ops_pr_lines` 0 → 15 | sqlite |
| `venue_daily_closes` 0 → 4 | sqlite |
| `ggv_receipt_accounting` 0 → 484 | sqlite (finance-adjacent) |
| `core_approval_requests` 0 → 1 | sqlite |
| Pack/wave2 result files present (21) | `forensic-completeness-20261001/*-RESULT.md` — discovery briefs, not human proof |
| Owner cockpit module | **FOUND:** `owner_cockpit.py` (pack-01 deepen) |
| Atrium ops maintenance/security | **FOUND:** new core modules |
| Reliability pipe episode rollup | **FOUND:** new module + test |

**Unchanged / still open:** `staff_ready=false`, `HUMAN_PROVEN=0`, six brand content boards, Amanda desk, HR implementation, Xero, V1-only July/August packs, original ~1500 Q&A requirements.

---

## 5. Paths checked

- `state/final-completion/forensic-completeness-20261001/*` (MISSION-CHARTER, inventories, matrix, register, stats, EXIT-NOTES, BUILD-PACK-QUEUE, E2E chains, HISTORY-GAPS, CONNECTIONS-42)
- `/Users/wolfterminal/.openclaw/workspace/wolf-system/dashboards/` (55 HTML, 261 PY, serve.py)
- `/Users/wolfterminal/beta-os/dashboards/` (175 HTML)
- `/Users/wolfterminal/beta-os/scripts/serve_beta.py`
- `/Users/wolfterminal/beta-os/scripts/core/` (252 modules)
- `/Users/wolfterminal/beta-os/catalog/content_library.sqlite`
- `~/Library/LaunchAgents/*.plist` (text scan)
- `http://127.0.0.1:8788/api/health` (200)

**Not checked:** browser render of dashboards; full verb-level API split; prod `:8787` mutation; `state/discovery/*` (excluded by instruction); Drive master plan download.

---

*Discovery only. No product code changed. No services restarted.*
