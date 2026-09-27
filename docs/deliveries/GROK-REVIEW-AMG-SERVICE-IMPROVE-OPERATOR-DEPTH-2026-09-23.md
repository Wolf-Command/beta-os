# GROK REVIEW — AMG Service Improvement Operator Depth — 2026-09-23

- Run: `BF-amg-service-improve-operator-depth-20260923`
- Plan: `docs/deliveries/GROK-PLAN-AMG-SERVICE-IMPROVE-OPERATOR-DEPTH-2026-09-23.md`
- Bound: `beta-amg-day-safe` (Beta `:8788` only)
- Claim: `bf-amg-service-improve-operator-depth-20260923`
- Reviewed: 2026-09-23 18:42 WITA (Cursor) · Peaches re-verify 2026-09-23 18:57 WITA
- Verdict: **PASS** / **ENGINEERING_PASS** (Cursor prove PASS=214 FAIL=0 under temporary `development_assertion`; launchd Beta restored `cloudflare_access`)

## Decision served

keep_building_without_matt (owner-autonomous-release-2026-09-19) + CAP-AMG-07 service improvement / review-to-improve. Extends the existing service-improve skeleton after AMG SLA incident operator depth ENGINEERING_PASS. Not BZG compose.

## What landed

- `scripts/core/amg_service_improve_operator_depth.py` — Owner and the existing Atrium hotel-ops seat open a review / finding / action / owner / due / notes slot or the EMPTY placeholder. Actions: note / next-action-touch / handoff-touch / dismiss-noise / review-decision (`still_specified` / `not_live_review` / `keep_as_note`). Recording refreshes the AMG management desk and the AMG Needs-You projection. Events → `state/amg-service-improve/operator-events.jsonl`. Schema `wolf.amg-service-improve-operator-depth.v1`. The service-improve framework store is not written. Review score, action outcome, and improve outcome stay null. Live review stays false.
- `scripts/serve_beta.py` — additive routes under `/api/amg/service-improve/operator-depth` (+ `/desk`, `/rbac`, `/objects/{id}`, operator-action aliases). PUT/PATCH on that prefix are refused. Existing `/api/amg/service-improve` skeleton stays.
- `dashboards/amg-service-improve.html` — `#service-depth` on the existing service-improve page (no orphan dashboard).
- `dashboards/amg-mgmt-cluster.html` — link to that panel. The cluster compose itself is unchanged.
- `scripts/core/wolf_shell.py` — honesty flag `amg_service_improve_operator_depth=true`.
- `scripts/tests/test_amg_service_improve_operator_depth.py` — **PASS=214 FAIL=0** · `EXIT: SUCCESS`.

## Evidence table

| Check | Claimed | Verified |
|---|---|---|
| Tests | PASS=214 FAIL=0 | **PASS=214 FAIL=0** under temporary `development_assertion` (temp listener pid 80713) |
| Anon desk | 403 | live `:8788` → **403** |
| Owner desk / rbac / detail / next-action | 200 | empty; recorded_count=0; slot_count=6; review_score/improve_outcome=null; live_review=false; staff_ready=false; framework_mutated=false; AMG desk + Needs-You refreshed |
| Misa | existing hotel-ops seat | **200** `hotel_ops`. Assignment count unchanged. No seat inserted |
| Outsider / Haikal / Devi / Amanda | 403 | **403** |
| proven / yanolja-write / invent-live-review / review-score / guest-blast / payment / bank / books / live-hotel / access-include / secret-mint / bzg-compose / production / resolve / public-post | 403 | unit refuse codes; live proven, yanolja-write, invent-live-review, review-score, guest-blast **403** |
| CAP-AMG-07 | SPECIFIED | SPECIFIED; ledger length 77 |
| AMG CRs ×7 | OPEN | OPEN, including CR-29c6ac36a9ca03f1 |
| Progress/CORE CRs ×4 | OPEN | OPEN |
| Global Nav | as-is | `531f29b41f5dfb381503889cacdcfb39` IN_PROGRESS; `e4bee2462ff81803287fa3562776d8ec` OPEN; `CR-5a5e660e41f782a4` RESOLVED; `CR-26989486969627cd` RESOLVED |
| Service page | `#service-depth` | present; CAP-AMG-07 stays SPECIFIED |
| Prod depth | 404 | **404** on `:8787` |
| Prod pid | 15975 | **15975** before, during, and after |
| Auth restore | cloudflare_access | launchd Beta pid **80873**; anon + spoof `X-Wolf-Subject` → **403** `missing_auth` |
| WIP quartet | untouched | hash unchanged |

## Red team

- Empty framework is not a live review, not a review score, and not an improve outcome. CAP-AMG-07 stays **SPECIFIED**.
- Misa is allowed because `org` already assigns PERS-MISA as Atrium hotel-ops. This slice does not call `ensure_operator_depth_rbac` and does not insert a seat. Haikal, Devi, Amanda, and an outsider stay refused.
- Haikal human stays **not_started**. Devi retest stays **parked**.
- AMG, Progress, and CORE completion rows stay **OPEN**. Global Nav rows were read and left as-is.
- No BZG compose. No money. No Cloudflare Access Include mutate. No secret mint. No Yanolja write. No live hotel. No guest blast. No public post. No INTG connector recover. No parked w12 FIN/PROC. No CAP-AMG-01 Yanolja connector. No NAS destroy. ClickUp and Telegram stay retired.
- Production `:8787` untouched.

## Live prove

1. Recorded prod pid **15975**. Launchd Beta was `cloudflare_access` (pid 79649). `launchctl bootout` Beta only (`net.wolfcommand.serve-beta`). Port `:8788` was free. Prod pid stayed **15975**.
2. Temp `BETA_AUTH_MODE=development_assertion` `serve_beta.py` on `:8788` (listener pid 80713). Auth payload `development_assertion`. Prod pid stayed **15975**.
3. `WOLF_TEST_MODE=1 BETA_AUTH_MODE=development_assertion python3 scripts/tests/test_amg_service_improve_operator_depth.py` → **PASS=214 FAIL=0 EXIT: SUCCESS**.
4. Killed temp. `launchctl bootstrap` + `kickstart` Beta (no `BETA_AUTH_MODE` ⇒ `cloudflare_access`, pid 80873).
5. Anon and spoof `X-Wolf-Subject` → **403** `missing_auth` (`auth_mode=cloudflare_access`). Prod depth **404**. Prod pid **15975**.

Signed-in Cloudflare browser click-through was not run. HTTP prove exercised the service-improve page, the desk, detail, and a next-action touch on `:8788` while the temporary assertion server was up.

## Honesty

- proven=false · ready=false · staff_ready=false
- CAP-AMG-07 stays **SPECIFIED**
- haikal_human=not_started · devi_retest=parked
- Commit: **uncommitted** (shared dirty tree; head `f3ab8f7`)



## Peaches independent verify (2026-09-23 18:57 WITA)

CLAIMED≠VERIFIED until this section. Cursor log and Cursor-authored review claimed PASS=214 FAIL=0 (same count as prior AMG SLA Incident pack — isomorphic operator-depth template, domain-renamed; not recycled prove).

1. Recorded prod pid **15975**. Booted out launchd Beta only (`net.wolfcommand.serve-beta`). Prod stayed **15975**.
2. Temp `BETA_AUTH_MODE=development_assertion` `serve_beta.py` on `:8788` (listener pid **82074**). Anon desk **403**.
3. `WOLF_TEST_MODE=1 BETA_AUTH_MODE=development_assertion python3 scripts/tests/test_amg_service_improve_operator_depth.py` → **PASS=214 FAIL=0 EXIT: SUCCESS** (Peaches re-run; output `/tmp/peaches-svc-improve-prove.out`).
4. Killed temp. `launchctl bootstrap` + `kickstart` Beta → `cloudflare_access` pid **82138**. Anon + spoof `X-Wolf-Subject` → **403** `missing_auth`. Prod depth **404**. Prod pid **15975**.
5. Pack files distinct from SLA: `amg_service_improve_operator_depth.py`, claim `bf-amg-service-improve-operator-depth-20260923`, slots review/finding/action/owner/due/notes, `#service-depth`, CAP-AMG-07 SPECIFIED, CR-29c6ac36a9ca03f1 OPEN.

**Peaches verdict:** ENGINEERING_PASS confirmed. CAP-AMG-07 stays SPECIFIED. Empty≠live reviews/scores/improve outcomes. Not deployed-commissioned. Not staff_ready.

## Exit

```
EXIT: SUCCESS
PASS=214 FAIL=0
VERDICT: PASS ENGINEERING_PASS
```
