# METRICOOL-RUNTIME-WIRE-1 RESULT — Authorised Metricool runtime into Beta

**As of:** 2026-09-30 ~08:03 WITA · **Branch:** `build/wolf-command-rebuild`  
**Ports:** Prod `:8787` pid **15975** READ-ONLY untouched · Beta test harness ephemeral  
**Flags:** `staff_ready=false` · `human_commissioned=false` · **No push** · **Did not start ESB-SETTLEMENT-PATH-1 / HEADCHEF / Exit Report**

## Decision / canon

Serves **FINAL_WOLF_COMPLETION_MISSION Phase 2 pack METRICOOL-RUNTIME-WIRE-1** (armed after PIPE-RELIABILITY-AUTO-1 PASS_VERIFIED).  
Challenges overnight blanket **NOT_RUNTIME** honesty ceiling from GGV-METRIC-HONESTY-1. **Does not re-do GGV-METRIC.**  
Wires Beta board/API to authorised Metricool **brand stamps** + **available analytics paths** (MCP evidence).  
Per-surface honesty: **RUNTIME_WIRED | NOT_RUNTIME | EXTERNAL_BLOCKER**.  
Never invents engagement / last_success / publish values. Preserves GGV-METRIC-HONESTY-1 + CONTENT-ENGINE-LIVE-1.  
Classification **INTERNALLY_SOLVABLE**. Credit exception `FINAL_WOLF_COMPLETION_MISSION`.

## What landed

### 1) Authorised brand stamps (RUNTIME_WIRED)
| Brand | blogId | Status | Engagement |
| --- | --- | --- | --- |
| Atrium Lombok | 6260617 | RUNTIME_WIRED | null |
| Goss Group | 6260628 | RUNTIME_WIRED | null |
| Uma Blu | 6260631 | RUNTIME_WIRED | null |
| Habitat | 6260634 | RUNTIME_WIRED | null |
| Selo | 6260635 | RUNTIME_WIRED | null |
| Tropik | 6260638 | RUNTIME_WIRED | null |

Evidence: MCP `getBrandSettings` → 6 brands (CLASSIFICATION-LOG `#metricool_runtime_probe`).

### 2) Analytics paths (RUNTIME_WIRED catalog)
| Field | Value |
| --- | --- |
| network / surface | instagram / posts |
| MCP tool | getAnalyticsAvailableMetrics |
| field_count | **29** |
| proven_includes | engagement, likes, reach |
| values_fetched | **false** (numeric values stay null) |

### 3) Per-surface honesty (replaces blanket NOT_RUNTIME)
| Surface | Status |
| --- | --- |
| mcp_server | RUNTIME_WIRED |
| brand_stamps | RUNTIME_WIRED |
| analytics_paths_instagram_posts | RUNTIME_WIRED |
| engagement_values | NOT_RUNTIME (null) |
| last_success | NOT_RUNTIME (null) |
| publish_success | NOT_RUNTIME (null) |
| wolf_http_connector | EXTERNAL_BLOCKER (`BETA_METRICOOL_ENABLED=false`) |

### 4) INTG-TRUTH-1 overlay
- `INT-MET-WOLF` → `probe_status=RUNTIME_WIRED_PARTIAL`, `audit_status=PARTIAL_IN_BETA`
- `honesty.metricool_wolf` → `PER_SURFACE` (was blanket `NOT_RUNTIME`)
- `last_success` / engagement remain **null**
- `MCP-Metricool` stays `AGENT_HOST_ONLY`

### 5) Auth page + API
- Page `/ops/metricool-runtime-wire-1` (+ aliases)
- API `GET /api/ops/metricool-runtime-wire-1`
- Unsigned → **403**
- POST/PATCH/PUT invent-engagement / last_success / prod-mutate / staff_ready → **403**

### 6) Preserved
| Surface | Status |
| --- | --- |
| GGV-METRIC-HONESTY-1 | **PRESERVED** (engagement/publish/last_success null; fake_metrics false) |
| CONTENT-ENGINE-LIVE-1 | **PRESERVED** (Metricool values still NOT_RUNTIME on content board) |

## Classification pin

| Shell / residue | Classification | Why |
| --- | --- | --- |
| Metricool brands + analytics catalog wire (this pack) | **INTERNALLY_SOLVABLE** | MCP authorised; Beta board stamps RUNTIME_WIRED |
| Engagement / last_success / publish **values** | **NOT_RUNTIME** | Not fetched; never invent (GGV honesty) |
| Wolf Beta HTTP Metricool connector | **EXTERNAL_BLOCKER** | `BETA_METRICOOL_ENABLED=false` evidenced |
| Next pack ESB-SETTLEMENT-PATH-1 | **EXTERNALLY_OR_HUMAN_TBD** | Parent/Peaches arms after verify — Cursor did not auto-chain |
| Exit Report / HEADCHEF | **MATT_ACTION** | Forbidden until Phase 13 / separate Matt arm |
| Prod mutate / push / fake engagement | **EXTERNAL_BLOCKER** | Hard rule — pid 15975 held RO |

Ceiling update (CLASSIFICATION-LOG Metricool row): blanket NOT_RUNTIME → **PER_SURFACE**; not_complete_until brands+catalog wired **DONE**; live engagement values remain NOT_RUNTIME / Wolf HTTP EXTERNAL_BLOCKER.

## Tests

| Suite | Result |
| --- | --- |
| `scripts/tests/test_metricool_runtime_wire1_20260930.py` | **PASS=136 FAIL=0** |

Shots: `docs/wolf/ops/shots/metricoolruntime1-desk-desktop.png`, `metricoolruntime1-desk-phone.png`, `metricoolruntime1-surfaces.png`, `metricoolruntime1-unsigned-deny.png` (4 distinct sha256).

## Files

- Core: `scripts/core/metricool_runtime_wire1.py`
- INTG overlay: `scripts/core/intg_truth_board.py` (INT-MET-WOLF per-surface)
- Serve: `scripts/serve_beta.py` (`_metricool_runtime_wire1_dispatch` + write refuse)
- Shell: `scripts/core/wolf_shell.py`
- UI: `dashboards/metricool-runtime-wire-1.html`
- Tests: `scripts/tests/test_metricool_runtime_wire1_20260930.py`
- Stamp: `state/final-completion/packs/METRICOOL-RUNTIME-WIRE-1-ARM.json`

## Out of scope (not started from this EXIT)

- **ESB-SETTLEMENT-PATH-1** (next — Peaches/parent arms after verify; Cursor must not auto-chain)
- Fetching live engagement numbers / inventing last_success
- Enabling `BETA_METRICOOL_ENABLED` / Metricool write
- Re-doing GGV-METRIC-HONESTY-1
- HEADCHEF / Exit Report / prod mutate / push

## EXIT

**EXIT:0**

`staff_ready=false` · `human_commissioned=false` · prod pid 15975 untouched · 6 brands RUNTIME_WIRED · analytics catalog 29 RUNTIME_WIRED · engagement/last_success null · Wolf HTTP EXTERNAL_BLOCKER · no fake metrics · no push · did not auto-chain next pack.
