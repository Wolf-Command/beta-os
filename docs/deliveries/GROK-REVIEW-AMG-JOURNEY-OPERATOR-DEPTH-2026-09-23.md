# GROK REVIEW — AMG Guest Journey Operator Depth — 2026-09-23

- Run: `BF-amg-journey-operator-depth-20260923`
- Plan: `docs/deliveries/GROK-PLAN-AMG-JOURNEY-OPERATOR-DEPTH-2026-09-23.md`
- Bound: `beta-amg-day-safe` (Beta `:8788` only)
- Claim: `bf-amg-journey-operator-depth-20260923`
- Reviewed: 2026-09-23 17:47 WITA
- Verdict: **PASS** / **ENGINEERING_PASS** (Cursor prove PASS=200 FAIL=0 under temporary `development_assertion`; launchd Beta restored `cloudflare_access`)

## Decision served

keep_building_without_matt (owner-autonomous-release-2026-09-19) + CAP-AMG-02 guest journey. Extends the existing journey skeleton after AMG revenue and yield operator depth ENGINEERING_PASS. Not BZG compose.

## What landed

- `scripts/core/amg_journey_operator_depth.py` — Owner and the existing Atrium hotel-ops seat open an enquiry / booking / pre-arrival / arrival / stay / checkout / return slot or the EMPTY placeholder. Actions: note / next-action-touch / handoff-touch / dismiss-noise / review-decision (`still_specified` / `not_live_journey` / `keep_as_note`). Recording refreshes the AMG management desk and the AMG Needs-You projection. Events → `state/amg-journey-workflow/operator-events.jsonl`. Schema `wolf.amg-journey-operator-depth.v1`. The journey framework store is not written. Booking count and occupancy stay null. Live journey stays false.
- `scripts/serve_beta.py` — additive routes under `/api/amg/journey-workflow/operator-depth` (+ `/desk`, `/rbac`, `/objects/{id}`, operator-action aliases). PUT/PATCH on that prefix are refused. Existing `/api/amg/journey-workflow` skeleton stays.
- `dashboards/amg-journey-workflow.html` — `#journey-depth` on the existing journey page (no orphan dashboard).
- `dashboards/amg-mgmt-cluster.html` — link to that panel. The cluster compose itself is unchanged.
- `scripts/core/wolf_shell.py` — honesty flag `amg_journey_operator_depth=true`.
- `scripts/tests/test_amg_journey_operator_depth.py` — **PASS=200 FAIL=0** · `EXIT: SUCCESS`.

## Evidence table

| Check | Claimed | Verified |
|---|---|---|
| Tests | PASS=200 FAIL=0 | **PASS=200 FAIL=0** under temporary `development_assertion` (temp pid 74842) |
| Anon desk | 403 | live `:8788` → **403** |
| Owner desk / rbac / detail / next-action | 200 | empty; recorded_count=0; slot_count=7; booking_count/occupancy=null; live_journey=false; staff_ready=false; framework_mutated=false; AMG desk + Needs-You refreshed |
| Misa | existing hotel-ops seat | **200** `hotel_ops`. Assignment count unchanged. No seat inserted |
| Outsider / Haikal / Devi / Amanda | 403 | **403** |
| proven / yanolja-write / invent-live-journey / booking-count / payment / bank / books / live-hotel / access-include / secret-mint / bzg-compose / production / resolve | 403 | unit refuse codes; live proven, yanolja-write, invent-live-journey, booking-count **403** |
| CAP-AMG-02 | SPECIFIED | SPECIFIED; ledger length 77 |
| AMG CRs ×7 | OPEN | OPEN, including CR-ce127471ba41692b |
| Progress/CORE CRs ×4 | OPEN | OPEN |
| Global Nav | as-is | `531f29b41f5dfb381503889cacdcfb39` IN_PROGRESS; `e4bee2462ff81803287fa3562776d8ec` OPEN; `CR-5a5e660e41f782a4` RESOLVED; `CR-26989486969627cd` RESOLVED |
| Journey page | `#journey-depth` | present; CAP-AMG-02 stays SPECIFIED |
| Prod depth | 404 | **404** on `:8787` |
| Prod pid | 15975 | **15975** before, during, and after |
| Auth restore | cloudflare_access | launchd Beta pid **74978**; anon + spoof `X-Wolf-Subject` → **403** `missing_auth` |
| WIP quartet | untouched | hash unchanged |

## Red team

- Empty framework is not a live journey, not a booking count, and not occupancy. CAP-AMG-02 stays **SPECIFIED**.
- Misa is allowed because `org` already assigns PERS-MISA as Atrium hotel-ops. This slice does not call `ensure_operator_depth_rbac` and does not insert a seat. Haikal, Devi, Amanda, and an outsider stay refused.
- Haikal human stays **not_started**. Devi retest stays **parked**.
- AMG, Progress, and CORE completion rows stay **OPEN**. Global Nav rows were read and left as-is.
- No BZG compose. No money. No Cloudflare Access Include mutate. No secret mint. No Yanolja write. No live hotel. No INTG connector recover. No parked w12 FIN/PROC. No NAS destroy. ClickUp and Telegram stay retired.
- Production `:8787` untouched.

## Live prove

1. Recorded prod pid **15975**. Launchd Beta was `cloudflare_access` (pid 74021). `launchctl bootout` Beta only (`net.wolfcommand.serve-beta`). Port `:8788` was free. Prod pid stayed **15975**.
2. Temp `BETA_AUTH_MODE=development_assertion` `serve_beta.py` on `:8788` (temp pid 74842). Auth payload `development_assertion`. Prod pid stayed **15975**.
3. `WOLF_TEST_MODE=1 BETA_AUTH_MODE=development_assertion python3 scripts/tests/test_amg_journey_operator_depth.py` → **PASS=200 FAIL=0 EXIT: SUCCESS**.
4. Killed temp. `launchctl bootstrap` + `kickstart` Beta (no `BETA_AUTH_MODE` ⇒ `cloudflare_access`, pid 74978).
5. Anon and spoof `X-Wolf-Subject` → **403** `missing_auth`. Prod depth **404**. Prod pid **15975**.

Signed-in Cloudflare browser click-through was not run. HTTP prove exercised the journey page, the desk, detail, and a next-action touch on `:8788` while the temporary assertion server was up.

## Honesty

- proven=false · ready=false · staff_ready=false
- CAP-AMG-02 stays **SPECIFIED**
- haikal_human=not_started · devi_retest=parked
- Commit: **uncommitted** (shared dirty tree; head `f3ab8f7`)

## Exit

```
EXIT: SUCCESS
PASS=200 FAIL=0
VERDICT: PASS ENGINEERING_PASS
```
