# BZG-CLOSE-GOVERNED-TAKEOVER-1 RESULT

**As of:** 2026-10-02 WITA · **Branch:** `build/wolf-command-rebuild` (local only — no push)  
**Decision:** 2026-09-17 · PICK Uma Blu Daily Close (extend) + Owner takeover pack  
**Prod `:8787`:** READ-ONLY untouched (pid `15975`)  
**Flags:** `staff_ready=false` · `human_commissioned=false` · `iza_commissioning=FAIL` (unchanged)  
**Do not claim Matt-ready** — Peaches verifies deployed route; then **MATT RETEST READY**.

## Tonight (verified, not wiped)

| Field | Value |
| --- | --- |
| close_id | `VDC-87202768-55af-4c8e-abc3-382a5496b8c6` |
| business_date | `2026-10-02` |
| state | `OPEN` |
| holder | **PERS-IZA** · Iza Zainatulloh Hulhidayati |
| Engineering | Did **not** delete close, clear DB ownership, or perform live Matt takeover |

## What landed

### Permission / RBAC
- `venue.close.reassign` (`PERM-VENUE-CLOSE-REASSIGN`)
- Grants: Captain, HFB, FB-Ops-Lead, Matt
- **Not** Cashier / CLOSER — ordinary cashiers cannot steal
- Migration does not mutate tonight’s holder/state

### API
- `POST /api/venue-close/takeover` — actor becomes holder; **reason required**
- `POST /api/venue-close/reassign` — assign to authorised closer; **reason required**
- Concurrent take still **409** with holder payload + `governed_takeover` + `requires_permission`
- Mutations (capture / declare / reconcile / EDC+ESB confirm) refuse while held by another
- Work preserved (photos, extracts, cash, EDC, QRIS, notes, state) — only `taken_by_*` changes
- Audit `venue_close.takeover` / `venue_close.reassign` with prior/new holder, reason, before/after snapshot

### UI (`dashboards/uma-blu-close.html`)
- Lock panel when held by another closer: holder name + preserved-work summary
- Authorised supervisor: reason field + **Take Over Close** / **Reassign Close**
- Cashiers see lock message without steal buttons
- After success, controls enable for new closer; prior work shown

## Deploy prove

| Check | Evidence |
| --- | --- |
| Beta `:8788` restart | launchctl kickstart `net.wolfcommand.serve-beta` → pid **61131** (was 57765) |
| Auth mode | `cloudflare_access` · `development_assertion_allowed=false` |
| Prod `:8787` | pid **15975** unchanged |
| Unsigned `/uma-blu-close` | **403** (auth gate) |
| Ephemeral harness HTML 200 | Take Over Close, Reassign, `takeoverReason`, `lockPanel` present |
| Harness Matt open tonight | **409** `concurrent_take` · holder **Iza** · `requires_permission=venue.close.reassign` |

## Tests

| Suite | Result |
| --- | --- |
| `scripts/tests/test_bzg_close_governed_takeover_1.py` | **pass=46 fail=0** |
| `scripts/tests/test_iza_assignment_resolution_1.py` | **pass=23 fail=0** |

## Files

- `scripts/migrations/migrate_bzg_close_governed_takeover_1.py`
- `scripts/core/venue_close.py`
- `scripts/core/bzg_daily_close.py`
- `scripts/core/uma_devi_p0.py` (caps.reassign / takeover)
- `scripts/core/audit.py` (metadata allowlist for takeover fields)
- `scripts/serve_beta.py` (takeover / reassign routes)
- `dashboards/uma-blu-close.html`
- `scripts/tests/test_bzg_close_governed_takeover_1.py`

**Impl tip:**  · **Parent tip:** `69de1bb`

RESULT: **PASS** (engineering). `staff_ready=false`. Iza commissioning remains **FAIL**. Human: Peaches independent verify → **MATT RETEST READY** (not claimed here).
