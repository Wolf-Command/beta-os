# STAFF-ACCESS-TRUTH-1 RESULT — Staff access truth deepen (no invent roles)

**As of:** 2026-09-30 ~09:35 WITA · **Branch:** `build/wolf-command-rebuild` (beta-os)  
**Ports:** Prod `:8787` pid **15975** READ-ONLY untouched · Beta test harness ephemeral  
**Flags:** `staff_ready=false` · `human_commissioned=false` · **No push** · **Did not start APPROVALS-LIVE-DEEPEN-1 / HEADCHEF / Exit Report**

## Decision / canon

Serves **FINAL_WOLF_COMPLETION_MISSION Phase 2 Wave9 pack STAFF-ACCESS-TRUTH-1** (armed after OCCUPANCY-EXTERNAL-HOLD-1 / Wave8 PASS_VERIFIED).  
Deepens staff access truth board from **live registry stamps / authorised identity only**.  
**Never invent roles · permissions · staff lists.**  
Honest empty when no staff commissioned (PASS count=0).  
Preserve **staff_access** honesty.  
Honest close-toward: **CAP-CORE staff access**.

## Classification pins

| Pin | Classification | Evidence |
| --- | --- | --- |
| Pack / registry board | **INTERNALLY_SOLVABLE** | Live org_* stamps wireable without invent |
| Human commissioning | **HUMAN_COMMISSIONING** | All seats PENDING / PENDING_FAIL; PASS=0 |
| Cloudflare Access include | **MATT_ACTION** | Owner-only include list; Zarah/Frail OWNER_ADDED documented |
| CF Access membership auto-probe | **EXTERNAL_BLOCKER** | No CF Access reader in Wolf |
| Invent-role writes | **REFUSED** | POST → 403 |
| staff_ready / human_commissioned | **false** always | Never flip |

## What landed

### 1) Truth board
- Page `/ops/staff-access-truth-1` (`dashboards/staff-access-truth-1.html`)
- Surfaces: registry · active seats · role mailboxes · human commissioning · CF Access · CF API · staff_access preserved · invent-role refuse · staff_ready refuse
- Active seat table from registry only (role_id / landing / commissioning / CF stamp)
- `commissioned_count=0` · honest empty · never invent PASS

### 2) API
- `GET /api/ops/staff-access-truth-1` (auth; Owner / progress.read) → same board (alias `/api/staff/access-truth-1`)
- Unsigned → **403**
- POST invent role / permission / staff_list / staff_ready / prod_mutate → **403**

### 3) Honesty stamps
| Pin | Value |
| --- | --- |
| classification | **INTERNALLY_SOLVABLE** |
| invented_roles / invented_staff | **false** |
| honest_empty_commissioned | **true** |
| staff_access | **PRESERVED** |
| `staff_ready` / `human_commissioned` | **false** |
| next_pack_for_parent_only | **APPROVALS-LIVE-DEEPEN-1** |
| cursor_did_not_auto_start_next | **true** |

## Tests

| Suite | Result |
| --- | --- |
| `scripts/tests/test_staff_access_truth1_20260930.py` | **PASS=135 FAIL=0** |

Shots: `docs/wolf/ops/shots/staffaccess1-desk-desktop.png`, `staffaccess1-desk-phone.png`, `staffaccess1-stamps.png`, `staffaccess1-unsigned-deny.png`.

## Files

- Core: `scripts/core/staff_access_truth1.py`
- Serve: `scripts/serve_beta.py` (`_staff_access_truth1_dispatch` + write refuse)
- UI: `dashboards/staff-access-truth-1.html`
- Shell crumbs/canonical: `scripts/core/wolf_shell.py`
- Tests: `scripts/tests/test_staff_access_truth1_20260930.py`
- Stamp: `state/final-completion/packs/STAFF-ACCESS-TRUTH-1-ARM.json`
- Classification: `state/final-completion/CLASSIFICATION-LOG-20260930.json`
- Preserved: `scripts/core/staff_access.py` · `dashboards/staff-ops-routing.html`

## Out of scope (not started from this EXIT)

- **APPROVALS-LIVE-DEEPEN-1** (next — Peaches/parent arms after verify; Cursor must not auto-chain)
- Invent roles / permissions / staff lists / force staff_ready
- HEADCHEF / Exit Report / prod mutate / push / Cloudflare Access admin edits

## Classification

Ceiling **staff access MISSING deepen** → **INTERNALLY_SOLVABLE** (live stamps wired).  
Sub-pins: HUMAN_COMMISSIONING (PASS empty) · MATT_ACTION (CF include) · EXTERNAL_BLOCKER (CF API).  
staff_access honesty preserved. No invent roles.

## EXIT

**EXIT:0**

`staff_ready=false` · `human_commissioned=false` · prod pid 15975 untouched · classification INTERNALLY_SOLVABLE · staff_access preserved · no push · did not auto-chain next pack.
