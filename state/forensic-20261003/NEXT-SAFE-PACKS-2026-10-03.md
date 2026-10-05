# Next safe packs — implementation briefs only
**Run:** 2026-10-03 · discovery only  
**Constraint:** packs MUST NOT touch Finance Core files:
- `scripts/core/ggv_finance_nota.py`
- `scripts/core/venue_close.py`
- `scripts/core/bzg_daily_close.py`
- `dashboards/ggv-finance.html`
- `dashboards/uma-blu-close.html`
- Finance close / GGV finance routes in `scripts/serve_beta.py` (e.g. `_venue_close_*`, `_bzg_daily_close_*`, `_ggv_finance_dispatch`)

Briefs only. No implementation. No `staff_ready` claim. No ENG_PROVED. Preserved close `VDC-87202768-55af-4c8e-abc3-382a5496b8c6` untouched.

Ordered by dependency and distance from finance core.

---

## PACK-SAFE-01 — Owner cockpit completion (home, not hub)

| Field | Detail |
|---|---|
| **Scope** | Close the V1 `wolf.html` questions missing from or weaker than `/api/owner/pulse-ro` + `/api/owner/cockpit` |
| **Current implementation** | **FOUND IN FILE:** `scripts/core/owner_pulse_ro.py` (10 tiles), `scripts/core/owner_cockpit.py` (brief, R2, system, asks, peaches, content, money, trading, personal rail), `dashboards/owner-cockpit.html` |
| **V1 benchmark** | `~/.openclaw/workspace/wolf-system/dashboards/wolf.html` — 5 buttons, 3 forms; `master.status.json` tiles; desk rails: asks, read/view, reports, coder, peaches, mission |
| **Data source** | `state/daemon-status.json`, `state/offbox-backup.json`, `state/r2-sync-state.json`, vault brief markdown, `peaches-desk/threads.jsonl` (V1 path), `owner_pulse_ro` loaders, `wolf-desk/tasks.json` |
| **Schema impact** | None required for read cards. Optional: `core_work_items` linkage for asks if answer-in-place is desired |
| **Permissions** | Owner (`PERS-MATT`); money card stays SoD-blocked (no finance core edits) |
| **UI** | Single cockpit page: pulse tiles + desk rails on same surface; each card opens real desk (sales, tick-draft, needs-you) not `-1` prove crumb |
| **API** | Extend `GET /api/owner/cockpit` only — no new finance routes |
| **Tests** | Extend `scripts/tests/test_owner_ro_loaders_20260930.py` pattern; assert card count, honesty stamps, href targets |
| **Beta verify would require** | Named human opens cockpit; brief/R2/system/asks/peaches show real file-backed state; clicking occ opens `amg-sales-desk` not ops-pack stub; `staff_ready` stays false until Matt signs a checklist |

**Register rows addressed:** `owner.pulse.brief`, `owner.pulse.system`, `owner.pulse.r2_gap`, `owner.desk.asks`, `owner.desk.peaches`, `owner.desk.read_view` (new surface), `owner.desk.mission`

---

## PACK-SAFE-02 — Atrium sales desk write path (sale record only)

| Field | Detail |
|---|---|
| **Scope** | First governed **write** on sales desk: record one sale into existing sqlite, without finance close or Xero |
| **Current implementation** | **FOUND IN FILE:** `scripts/core/amg_sales_desk_ro.py`, `dashboards/amg-sales-desk.html`; `GET /api/amg/sales-desk/*` returns 200; `POST` returns 405 per PACK-03 result |
| **V1 benchmark** | `atrium-sales.html` 14 views; V1 `atrium-sales` py module; payments 399, units 88, leads 570 (V1 sqlite per prior audit) |
| **Data source** | Atrium sales sqlite (path per `amg_sales_desk_ro.py` loader — verify at implement time); Yanolja read for occ context only |
| **Schema impact** | Writes to existing sales tables only — no `venue_daily_closes`, no `ggv_*` |
| **Permissions** | AMG sales role; segregated from finance SoD |
| **UI** | `amg-sales-desk.html` New Sale tab: form → POST → list refresh |
| **API** | `POST /api/amg/sales-desk/sales` (new handler in `amg_sales_desk_ro.py` only) |
| **Tests** | Extend `scripts/tests/test_amg_os_shell1_20260930.py` or dedicated sales write test; fixture sale row rolled back |
| **Beta verify would require** | Human records one Available unit sale; payment row appears in `GET /api/amg/sales-desk/payments`; pulse leads card still honest about 24h vs sheet |

**Register rows addressed:** `amg.sales.newsale`, `amg.sales.payments` (uncap), lead→sale chain middle

---

## PACK-SAFE-03 — Content tick → draft (one brand, no publish)

| Field | Detail |
|---|---|
| **Scope** | One brand cycle: card comment → Amanda-equivalent apply → tick creates Metricool **draft** or Misa queue item |
| **Current implementation** | **FOUND IN FILE:** `scripts/core/content_tick_draft.py`, `dashboards/content-tick-draft.html` (3 buttons); Metricool WRITE off per `metricool_runtime_wire1.py` |
| **V1 benchmark** | V1 `/api/amanda/*` (8 paths **NOT FOUND** on Beta), `content-habitat.html` etc., tick machine on V1 `serve.py` |
| **Data source** | `content_cards`, Habitat cycle file, Metricool schedule API (read), Misa queue stub, `assets` (205 rows), `nas_index` |
| **Schema impact** | `content_cards` state transitions; optional `misa_queue_items` if table exists — verify at implement |
| **Permissions** | Content operator; publish gate remains closed |
| **UI** | `content-tick-draft.html`: single-brand focus; library lookup shows asset-in-48 vs NAS-only |
| **API** | `POST /api/content/tick-draft/tick` in existing module; **no** `/api/planner/render` publish path |
| **Tests** | Pattern from `scripts/tests/test_content_engine_live1_20260930.py` |
| **Beta verify would require** | Human ticks one card; draft or queue id returned; `performance_records` not claimed as learn loop |

**Register rows addressed:** `content.tick`, `content.amanda.*`, `content.brands.habitat` (one brand)

---

## PACK-SAFE-04 — NAS library honest search (asset vs index)

| Field | Detail |
|---|---|
| **Scope** | Staff can answer: “is this shoot file in the Wolf library or only on NAS?” |
| **Current implementation** | **FOUND IN FILE:** `scripts/core/nas_library.py`, `nas_b2_desk_stamp1.py`; `/api/nas/index/search`, `/api/content/nas-coverage`; `assets`=205, `nas_index`=63370 |
| **V1 benchmark** | V1 `catalogue.html`, `/api/catalogue/*` (**NOT FOUND** on Beta); NAS 38,091 shallow (prior stamp) |
| **Data source** | `catalog/content_library.sqlite` (`assets`, `nas_index`); NAS mount read via existing NAS routes |
| **Schema impact** | Read-only preferred; optional `asset_nas_link` table if implementers choose — not required for first prove |
| **Permissions** | Content staff read; no NAS write |
| **UI** | Wire search into `content-tick-draft` and `seat-content-desk-1` — not a new hub page |
| **API** | Existing `/api/nas/index/search` + coverage endpoint enrichment |
| **Tests** | NAS search tests in existing nas test files if present; else new test under `scripts/tests/` |
| **Beta verify would require** | Human searches known filename; result shows FOUND_IN_ASSETS vs INDEX_ONLY vs NOT_FOUND with path honesty |

**Register rows addressed:** `content.nas.library`, history gap NAS vs library

---

## PACK-SAFE-05 — Approvals gate (non-finance)

| Field | Detail |
|---|---|
| **Scope** | One non-financial approval: e.g. content draft or ops exception — uses `core_approval_requests` without touching close/nota routes |
| **Current implementation** | **FOUND IN FILE:** `scripts/core/approvals_evidence_pack10.py`, `approvals_live_deepen1.py`, `approvals.py`; `core_approval_requests`=1, `core_delegations`=0 |
| **V1 benchmark** | V1 approval flows in ops scripts; authority limits on V1 (**NOT FOUND** as Beta table) |
| **Data source** | `core_approval_requests`, `core_audit_events` (27548 rows), evidence attachments |
| **Schema impact** | `core_approval_requests`, optional `approval_authority_limits` seed — **not** finance tables |
| **Permissions** | Requester vs approver roles via `rbac.py` |
| **UI** | `approvals-evidence.html` + deepen page; inline on My Work item |
| **API** | `POST /api/approvals/evidence/request` pattern in pack10 module |
| **Tests** | `scripts/tests/test_approvals_live_deepen1_20260930.py` |
| **Beta verify would require** | Human A requests, Human B approves; row in `core_approval_requests`; audit event; no finance route called |

**Register rows addressed:** `approvals.evidence`, `approvals.limits`, issue→verify chain tail

---

## PACK-SAFE-06 — My Work actable queue

| Field | Detail |
|---|---|
| **Scope** | Owner/staff can open `/my-work`, see assigned items, complete one with evidence — without delegations table if single-owner prove |
| **Current implementation** | **FOUND IN FILE:** `scripts/core/universal_my_work.py`, `dashboards/my-work.html`, `my-work-item.html`; `core_work_items`=212; page auth-blocked on prior pass |
| **V1 benchmark** | V1 `wolf.html#tasks`, Amanda task loop (**NOT FOUND** on Beta) |
| **Data source** | `core_work_items`, `core_audit_events` |
| **Schema impact** | `core_work_items.status` updates; optional `core_delegations` later |
| **Permissions** | Fix auth so staff role can read queue; owner sees subset |
| **UI** | `my-work.html` list + detail; evidence attach |
| **API** | Existing my-work routes in `serve_beta.py` — auth fix only in `rbac.py` / handler gates |
| **Tests** | `scripts/tests/test_mywork_prove1_20260930.py` |
| **Beta verify would require** | Staff login → my-work 200 → complete one item → audit row |

**Register rows addressed:** `owner.desk.tasks`, `mywork.queue`

---

## PACK-SAFE-07 — CRM identity stitch (read + one write)

| Field | Detail |
|---|---|
| **Scope** | Link Habitat sheet lead ↔ `core_leads` ↔ sales desk lead — one identity row |
| **V1 benchmark** | `crm-identity.html`, V1 CRM APIs; `core_leads`=8 vs Habitat 271 |
| **Current implementation** | **FOUND IN FILE:** `scripts/core/crm_identity_wave2_03.py`, `crm_identity_memory.py`, `dashboards/crm-identity-wave2.html` |
| **Data source** | Google Sheet (Habitat), `core_leads`, sales sqlite leads |
| **Schema impact** | `core_leads` + identity map table if exists |
| **Permissions** | CRM operator read; one write to `core_leads` |
| **UI** | `crm-identity-wave2.html` |
| **API** | `/api/crm/identity/*` handlers |
| **Tests** | `scripts/tests/test_crm_identity1_20260930.py` |
| **Beta verify would require** | One lead stitched; pulse leads card explains 24h vs sheet honestly |

**Register rows addressed:** `crm.identity.*`, `owner.pulse.leads`

---

## PACK-SAFE-08 — Reliability pipe episode rollup (ops visibility)

| Field | Detail |
|---|---|
| **Scope** | Owner sees pipe episodes with honesty pins — no fake uptime |
| **Current implementation** | **FOUND IN FILE:** `scripts/core/reliability_pipe_episode_rollup1.py`, `dashboards/reliability-pipe-episode-rollup-1.html`, `pipe_reliability_auto1.py` |
| **V1 benchmark** | V1 `reliability.html`, `state/reliability/*` episode logs |
| **Data source** | `state/ops/external-route-health-latest.json`, classification flap files, episode rollup state |
| **Schema impact** | Read-only; optional episode cache json under `state/` |
| **Permissions** | Owner/ops read |
| **UI** | Episode list with BLOCKED/PARTIAL stamps |
| **API** | `/api/reliability/pipe-episode-rollup/*` per module |
| **Tests** | `scripts/tests/test_reliability_pipe_episode_rollup1_20260930.py` |
| **Beta verify would require** | Known episode from Oct HA incident visible; no GREEN invent |

**Register rows addressed:** `reliability.pipe`, `infra.launchd.live_plists` (partial)

---

## PACK-SAFE-09 — Ops event bus mirror honesty

| Field | Detail |
|---|---|
| **Scope** | Align connection matrix with RO board: show last N events from V1 bus or honest EMPTY |
| **Current implementation** | **FOUND IN FILE:** `scripts/core/ops_event_bus_ro.py`, `dashboards/ops-event-bus-1.html` — `load_event_bus_ro(sample_limit=5)` |
| **V1 benchmark** | V1 `state/event_bus.db` (per CONNECTIONS-42); matrix id `Event_Bus` = ABSENT |
| **Data source** | V1 `event_bus.db` read-only mount OR honest UNAVAILABLE stamp |
| **Schema impact** | None on Beta catalog if read-only mirror |
| **Permissions** | Ops read |
| **UI** | `ops-event-bus-1.html` shows sample or UNAVAILABLE |
| **API** | Existing RO route |
| **Tests** | New read test: returns sample or explicit UNAVAILABLE |
| **Beta verify would require** | Board shows real events or UNAVAILABLE — not empty shell |

**Register rows addressed:** `integration.event_bus`, matrix drift

---

## PACK-SAFE-10 — Voice + content seats (shell → read)

| Field | Detail |
|---|---|
| **Scope** | Three voice boards + content seats show V1-equivalent **read** cards (scripts, queue depth) — not telephony write |
| **Current implementation** | **FOUND IN FILE:** `scripts/core/voice_boards_ro.py`, `seats_content_ro.py`, `seats_ads_studio_ro.py`, `seats_resolve_studio_ro.py`; pages `amg-voice-1.html`, `bzg-voice-1.html`, `ggv-voice-1.html`, `seat-content-desk-1.html`, etc. |
| **V1 benchmark** | `amg-voice.html`, `bzg-voice.html`, `ggv-voice.html`, `ads-studio.html`, `haikal-desk.html` |
| **Data source** | Voice queue files on V1 disk if readable; Metricool/content queue counts |
| **Schema impact** | None |
| **Permissions** | Seat role read |
| **UI** | Replace shell classify with READ_ONLY_MIRROR cards |
| **API** | Extend RO loaders only |
| **Tests** | Pattern from `test_hkegcav_ro_loaders_20260930.py` |
| **Beta verify would require** | Each seat page returns 200 + at least one LIVE or honest EMPTY card |

**Register rows addressed:** `beta.new.voice_boards`, `beta.new.seats_*`, content ops depth

---

## PACK-SAFE-11 — Atrium ops maintenance + security (field evidence)

| Field | Detail |
|---|---|
| **Scope** | PM checklist + security evidence upload metadata (not full MSC suite) |
| **Current implementation** | **FOUND IN FILE:** `scripts/core/atrium_ops_maintenance_pm_1.py`, `atrium_ops_security_evidence_1.py`, dashboards `atrium-ops-maintenance-pm-1.html`, `atrium-ops-security-evidence-1.html` |
| **V1 benchmark** | MSC cluster pages on V1; hotel ops workflows in prior register |
| **Data source** | Ops evidence files, maintenance schedule json |
| **Schema impact** | New ops evidence table or reuse `core_audit_events` — implementer choice; **not** finance schema |
| **Permissions** | Atrium ops manager |
| **UI** | Two pages linked from `amg-ops-pack` |
| **API** | `/api/msc/maintenance-pm`, `/api/msc/security-evidence` (already in `serve_beta.py`) |
| **Tests** | Result files exist: `ATRIUM-OPS-MAINTENANCE-PM-1-RESULT.md`, `ATRIUM-OPS-SECURITY-EVIDENCE-1-RESULT.md` |
| **Beta verify would require** | One PM task checked; one evidence artifact attached with provenance |

**Register rows addressed:** `atrium.ops.maintenance`, `atrium.ops.security`

---

## PACK-SAFE-12 — Guest stay read depth (no PMS write)

| Field | Detail |
|---|---|
| **Scope** | Guest-stay board shows honest PMS state: reservations count, UNAVAILABLE for in-house until source found |
| **Current implementation** | **FOUND IN FILE:** `scripts/core/amg_guest_stay_pack7.py`, `dashboards/amg-guest-stay.html` |
| **V1 benchmark** | V1 guest/PMS screens; `reservations.db` = 1 row |
| **Data source** | `state/reservations.db`, Yanolja read, Cloudbeds RETIRED per matrix |
| **Schema impact** | Read-only |
| **Permissions** | AMG ops read |
| **UI** | UNAVAILABLE stamps where data missing |
| **API** | `/api/amg/guest-stay/*` |
| **Tests** | Pack-07 result file as spec |
| **Beta verify would require** | Board does not invent in-house guests |

**Register rows addressed:** `amg.guest.*`, booking→departure chain steps 2–3

---

## Explicitly excluded from safe packs (finance core or touch close)

| Item | reason |
|---|---|
| Uma buy → receive → petty → **close** | requires `venue_close.py`, `bzg_daily_close.py`, `uma-blu-close.html` |
| GGV nota → books | requires `ggv_finance_nota.py`, `ggv-finance.html` |
| Atrium finance SoD screens with cash match | PACK-05 territory; `amg_finance_screens.py`, fin shells |
| EDC/bank card / recon board | `serve_beta` `_bzg_daily_close_*` routes |
| GGV receipt accounting ingest | `ggv_receipt_accounting1.py`, `ggv_bank_statement1.py` |
| Month-end shareholder **finance** pack | touches fin shells and Xero-absent chain |

---

## Suggested pack order

1. PACK-SAFE-01 Owner cockpit (unblocks home truth)  
2. PACK-SAFE-05 Approvals gate (other packs call it)  
3. PACK-SAFE-06 My Work (staff actability)  
4. PACK-SAFE-02 Sales write (first vertical write outside finance)  
5. PACK-SAFE-03 + 04 Content tick + NAS search  
6. PACK-SAFE-07 CRM identity  
7. PACK-SAFE-08–12 Ops visibility (reliability, event bus, voice seats, atrium ops, guest stay)

---

## Done means (all packs)

A named human runs the chain on Beta `:8788`, the row exists in the Beta store (or honest UNAVAILABLE is shown), read-back matches, failure surfaces on the card, and a Peaches-verify JSON/MD result is filed under `state/final-completion/` — **without** claiming `staff_ready`, ENG_PROVED, or Matt-ready.

---

*Briefs only. No code changes in this forensic pass.*
