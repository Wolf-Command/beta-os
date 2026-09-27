# W3-P4 — Dashboard truth, data quality, staleness — 27 Sep 2026

Decision served: owner brief 27 Sep 2026, PACK 4. Extends the 2026-09-18 dashboard projection rule and the existing Wolf shell. Not a new task or approval database.

TECHNICAL PROOF is separate from DEPLOYED ROUTE PROOF, and both are separate from STAFF READINESS, HUMAN COMMISSIONING, and OPERATING ADOPTION.

Production `:8787` stayed on pid 15975 (`serve.py`). Beta `:8788` was restarted with `launchctl kickstart -k` on `net.wolfcommand.serve-beta` only, from pid 23945 to pid 26115, still `scripts/serve_beta.py`. No money, bank, or payment action. No NAS write. No external call. No ledger write.

## BEFORE

Dashboards already had pieces of honesty, and they did not share one provenance layer.

- `scripts/core/integration_health.py` could say UNKNOWN, NOT_CONFIGURED, READ_OK, DEGRADED, or ERROR for a few connectors. It did not speak LIVE / CURRENT / STALE / UNKNOWN / UNAVAILABLE / NEEDS REVIEW, and it did not cover Wolf Core, NAS, or finance ledgers as one register.
- `scripts/core/progress_read_model.py` already marks a ledger projection STALE when it disagrees with the canonical 77, and hides the percentage. That rule stays. It was not a stamp other desks could reuse.
- The Wolf shell (`#wolfnav`, `wolf-tokens.css`) was already the header and navigation. Pages did not share one card, empty, error, and permission-denied language for data freshness.
- Yanolja had no reader. ESB was a read-only warehouse with settlement unavailable. Klaviyo was a reader file that this prove does not call. Metricool status was local and not a publish. None of those were labelled commissioned.

## BUILT

- `scripts/core/dashboard_truth.py` is the shared classifier and the source register. It does not add a table. It reads Wolf Core `org_persons`, `org_roles`, `org_assignments`, and `core_work_items` read-only.
- Display states: LIVE, CURRENT, STALE, UNKNOWN, UNAVAILABLE, NEEDS REVIEW. A stale fact cannot be labelled current. Empty is not unknown. Claimed is not verified. Source found is not authoritative. Historical is not current. Estimate is not actual. Designed is not built, tested, or live.
- `mark_stale` and `projection_status` are the shared stale path. A failed read goes through `fail_closed` and comes back UNAVAILABLE, not zero.
- The register lists Yanolja, ESB, Wolf Core, NAS, finance ledgers, Klaviyo, and Metricool. `commissioned`, `human_commissioned`, and `staff_ready` are false on every row. No network probe. Absolute paths are stripped before a string is returned.
- Shared UI: existing `#wolfnav` stays the header and nav. `dashboards/assets/wolf-truth.css` and `wolf-truth.js` add the card, the six state chips, and empty / error / permission-denied. Owner page: `/dashboard-truth`. Strips on Owner Empire, My Work, AMG, GGV, and BZG call the stamp for that surface.
- Routes: `GET /api/dashboard-truth` is Owner only. `GET /api/dashboard-truth/stamp` follows the seat that can open that surface. POST, PUT, and PATCH return 403 unsigned and 405 for the Owner. Direct `/dashboard-truth.html` unsigned is 403.

Register read at the end of this pack, from the local probes, not from a manufactured KPI:

| source | display | authority | presence | claim |
| --- | --- | --- | --- | --- |
| Yanolja | UNAVAILABLE | UNKNOWN | UNKNOWN | UNVERIFIED |
| ESB | NEEDS REVIEW | SOURCE_FOUND | PRESENT | CLAIMED |
| Wolf Core | CURRENT | AUTHORITATIVE | PRESENT | VERIFIED |
| NAS | UNKNOWN | SOURCE_FOUND | UNKNOWN | UNVERIFIED |
| Finance ledgers | UNAVAILABLE | UNKNOWN | UNKNOWN | UNVERIFIED |
| Klaviyo | UNKNOWN | SOURCE_FOUND | UNKNOWN | UNVERIFIED |
| Metricool | UNAVAILABLE | UNKNOWN | UNKNOWN | UNVERIFIED |

Wolf Core CURRENT means the control store was read just now and the required tables are present. It is not a live hotel feed and it is not human commissioned. NAS and Klaviyo are UNKNOWN because the mount and the reader file were seen and the file set and the profiles were not counted. ESB NEEDS REVIEW means a warehouse sales table was opened read-only. That is not settlement and not current cash.

## VERIFIED

```
python3 scripts/tests/test_dashboard_truth_provenance.py | tail -3
PASS  staff-denied shows permission-denied
PASS=98 FAIL=0

python3 scripts/tests/test_dashboard_truth.py | tail -3
PASS  read_model has no live hard-coded 28%
PASS=62 FAIL=0

python3 scripts/tests/test_owner_empire_pack.py | tail -3
PASS=80 FAIL=0
EXIT: SUCCESS

python3 scripts/tests/test_staff_home.py | tail -3
PASS  beta 8788 up
PASS=89 FAIL=0
EXIT: SUCCESS

python3 scripts/tests/test_wolf_bzg_uma_nav.py | tail -3
PASS=111 FAIL=0
EXIT: SUCCESS

python3 scripts/tests/test_ggv_ops_pack.py | tail -3
PASS=97 FAIL=0

python3 scripts/tests/test_amg_ops_pack.py | tail -3
PASS=102 FAIL=4
EXIT: FAIL
```

The new suite's headless Chrome covered Owner `/dashboard-truth` at 1280px and 390px (Yanolja, ESB, a state chip, "Not commissioned") and staff My Work at 390px (Data truth, a state chip). Unsigned staff on `/dashboard-truth` returned `permission-denied`. Classifier cases covered stale-not-current, empty-not-unknown, claimed-not-verified, source-found-not-authoritative, historical-not-current, estimate-not-actual, and designed-not-live.

Deployed on Beta `:8788` after the restart, unsigned:

```
page 403
html 403
api 403
stamp 403
post 403
```

Each body is `error: forbidden` and `ui.component: permission-denied` (Cloudflare JWT required). Owner 200 was proven on the ephemeral handler with a development subject, not by bypassing the live Cloudflare gate. Production pid 15975 was still `serve.py` on `:8787` after the Beta restart. Beta pid 26115 is `scripts/serve_beta.py`.

`test_amg_ops_pack.py` is red for a live roster fact this pack did not write: `ASG-AMG-DAY-MISA` is ACTIVE for `PERS-MISA` on `ROLE-AMG-GM`. The four fails are "hotel ops unassigned", "misa forbidden on live roster", "live misa still out", and "misa GET 403" (got 200). The page assertions in that suite passed. This pack does not change AMG seats.

## STAFF READY?

NO. `staff_ready` is false on the register and on every source. A strip on My Work is not a staff walk.

## HUMAN COMMISSIONED?

NO.

## BLOCKERS

- No human evidence that any connector is commissioned.
- Yanolja has no reader. Occupancy was not invented.
- ESB settlement API remains unavailable. The warehouse read is not current cash.
- Finance books were not opened. The management-reporting file is not on disk.
- Metricool is not configured. Klaviyo was not called.
- NAS is mounted and the full tree was not counted, so the card stays UNKNOWN.
- Wolf Core CURRENT is a store read, not operating adoption.

## NEXT HUMAN TEST

Sign in on Beta as Owner and open `/dashboard-truth`. Check the seven cards against the table above. Confirm none of them is being read as live occupancy, live F&B cash, or a P&L. Then open My Work as a staff seat and confirm the strip names Wolf Core only, and that it does not say commissioned.

## FOUNDER DEPENDENCY

RETAIN. Declaring a source commissioned is an owner decision. This pack does not make that decision and does not remove it.

RESULT: PASS
