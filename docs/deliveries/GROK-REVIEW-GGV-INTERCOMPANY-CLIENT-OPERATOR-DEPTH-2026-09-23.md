# GROK REVIEW — GGV Intercompany Client Operator Depth — 2026-09-23

- Run: `BF-ggv-intercompany-client-operator-depth-20260923`
- Plan: `docs/deliveries/GROK-PLAN-GGV-INTERCOMPANY-CLIENT-OPERATOR-DEPTH-2026-09-23.md`
- Bound: `beta-ggv-ops-safe` (Beta `:8788` only)
- Claim: `bf-ggv-intercompany-client-operator-depth-20260923`
- Reviewed: 2026-09-23 19:39 WITA (Cursor)
- Verdict: **PASS** / **ENGINEERING_PASS** (Cursor prove PASS=243 FAIL=0 under temporary `development_assertion`; launchd Beta restored `cloudflare_access`)

## Decision served

keep_building_without_matt (owner-autonomous-release-2026-09-19) + CAP-GGV-06 intercompany client mode. Extends the existing intercompany skeleton after GGV Client Profitability operator depth ENGINEERING_PASS. Not BZG compose.

## What landed

- `scripts/core/ggv_intercompany_client_operator_depth.py` — Owner and the existing GGV seats (Amanda, Haikal, Misa) open a service-record / invoice / allocation / arms-length / AR-AP / notes slot or the EMPTY placeholder. Actions: note / next-action-touch / handoff-touch / dismiss-noise / review-decision (`still_specified` / `not_live_billing` / `keep_as_note`). Recording refreshes the GGV management desk and the GGV Needs-You projection. Events → `state/ggv-intercompany-client/operator-events.jsonl`. Schema `wolf.ggv-intercompany-client-operator-depth.v1`. The intercompany framework store is not written. Service record, invoice, allocation, arms length, AR/AP, tax treatment, and payment stay null. Live billing stays false. No P&L strip (no revenue / cost / margin / FX).
- `scripts/serve_beta.py` — additive routes under `/api/ggv/intercompany-client/operator-depth` (+ `/desk`, `/rbac`, `/objects/{id}`, operator-action aliases). PUT/PATCH on that prefix are refused. Existing `/api/ggv/intercompany-client` skeleton stays.
- `dashboards/ggv-intercompany-client.html` — `#interco-depth` on the existing intercompany page (no orphan dashboard).
- `dashboards/ggv-mgmt-cluster.html` — link to that panel. The cluster compose itself is unchanged.
- `scripts/core/wolf_shell.py` — honesty flag `ggv_intercompany_client_operator_depth=true`.
- `scripts/tests/test_ggv_intercompany_client_operator_depth.py` — **PASS=243 FAIL=0** · `EXIT: SUCCESS`.
- Existing skeleton `scripts/tests/test_ggv_intercompany_client.py` — **PASS=257 FAIL=0** after the additive routes.

## Evidence table

| Check | Claimed | Verified |
|---|---|---|
| Tests | PASS=243 FAIL=0 | **PASS=243 FAIL=0** under temporary `development_assertion` (temp listener pid 86351) |
| Anon desk | 403 | live `:8788` → **403** `missing_subject` during assertion; after restore **403** `missing_auth` |
| Owner desk / rbac / detail / next-action | 200 | empty; recorded_count=0; slot_count=6; invoice/allocation/ar_ap/payment=null; live_billing=false; staff_ready=false; framework_mutated=false; GGV desk module_count=5 + Needs-You refreshed |
| Amanda / Haikal / Misa | existing GGV seats | **200** `content_management` / `editor` / `crew`. Assignment count unchanged. No seat inserted |
| Outsider / Devi | 403 | **403** |
| proven / invent-live-billing / invent-invoice / payment / alchemist-write / guest-blast / books / tax-write / bzg-compose | 403 | unit refuse codes; live those paths **403** |
| Skeleton invoice read | still empty | **200**; invoice=null; live_billing=false |
| CAP-GGV-06 | SPECIFIED | SPECIFIED; ledger length 77 |
| GGV CRs ×5 | OPEN | OPEN, including CR-6a19c9221cab0178 |
| Progress/CORE CRs ×4 | OPEN | OPEN |
| Global Nav | as-is | `531f29b41f5dfb381503889cacdcfb39` IN_PROGRESS; `e4bee2462ff81803287fa3562776d8ec` OPEN; `CR-5a5e660e41f782a4` RESOLVED; `CR-26989486969627cd` RESOLVED |
| Intercompany page | `#interco-depth` | present; CAP-GGV-06 stays SPECIFIED |
| Prod depth | 404 | **404** on `:8787` |
| Prod pid | 15975 | **15975** before, during, and after |
| Auth restore | cloudflare_access | launchd Beta pid **86473**; anon + spoof `X-Wolf-Subject` → **403** `missing_auth` |
| WIP quartet | untouched | hash unchanged |

## Red team

- Empty framework is not live intercompany billing, not an invoice, not an allocation, and not an AR/AP balance. CAP-GGV-06 stays **SPECIFIED**. The skeleton ceiling label stays BUILT. This slice does not raise it.
- Amanda, Haikal, and Misa are allowed because `ggv_ops_pack` already names them as Habitat GGV seats. This slice does not call `ensure_operator_depth_rbac` and does not insert a seat. Devi and an outsider stay refused. Haikal human stays **not_started**. Devi retest stays **parked**.
- GGV, Progress, and CORE completion rows stay **OPEN**. Global Nav rows were read and left as-is.
- No BZG compose. No money. No Cloudflare Access Include mutate. No secret mint. No Alchemist / bank / books write. No live billing. No tax write. No guest blast. No public post. No INTG connector recover. No parked w12 FIN/PROC. No CAP-AMG-01 Yanolja connector. No NAS destroy. ClickUp and Telegram stay retired.
- Production `:8787` untouched.
- The one operator event written during prove (`EVT-098fb567-a376-49b6-b86c-a51626d2b427`) is a next-action note on `EMPTY-GGV-IC`. Invoice, allocation, AR/AP, and payment are null. `live_billing` is false. `framework_mutated` is false.

## Live prove

1. Recorded prod pid **15975**. Launchd Beta was `cloudflare_access` (pid 84935). `launchctl bootout` Beta only (`net.wolfcommand.serve-beta`). Port `:8788` was free. Prod pid stayed **15975**.
2. Temp `BETA_AUTH_MODE=development_assertion` `serve_beta.py` on `:8788` (listener pid 86351). Anon desk **403** `missing_subject` / `auth_mode=development_assertion`. Prod pid stayed **15975**.
3. `WOLF_TEST_MODE=1 BETA_AUTH_MODE=development_assertion python3 scripts/tests/test_ggv_intercompany_client_operator_depth.py` → **PASS=243 FAIL=0 EXIT: SUCCESS**.
4. Killed temp. `launchctl bootstrap` + `kickstart` Beta (no `BETA_AUTH_MODE` ⇒ `cloudflare_access`, pid 86473).
5. Anon and spoof `X-Wolf-Subject` → **403** `missing_auth` (`auth_mode=cloudflare_access`). Prod depth **404**. Prod pid **15975**.

Signed-in Cloudflare browser click-through was not run. HTTP prove exercised the intercompany page, the desk, invoice-slot detail, a next-action touch, and the still-empty skeleton invoice read on `:8788` while the temporary assertion server was up.

## Honesty

- proven=false · ready=false · staff_ready=false
- CAP-GGV-06 stays **SPECIFIED**
- haikal_human=not_started · devi_retest=parked
- Commit: **uncommitted** (shared dirty tree)

## Peaches independent verify (2026-09-23 19:49 WITA)

CLAIMED≠VERIFIED until this section. Cursor-authored review claimed PASS=243 FAIL=0.

1. Recorded prod pid **15975**. Booted out launchd Beta only (`net.wolfcommand.serve-beta`; was pid 86473). Prod stayed **15975**. Port `:8788` free.
2. Temp `BETA_AUTH_MODE=development_assertion` `serve_beta.py` on `:8788` (durable Shell-tracked listener pid **87569**). Anon desk **403** `missing_subject` / `auth_mode=development_assertion`.
3. `WOLF_TEST_MODE=1 BETA_AUTH_MODE=development_assertion python3 scripts/tests/test_ggv_intercompany_client_operator_depth.py` → **PASS=243 FAIL=0 EXIT: SUCCESS** (Peaches re-run; output `/tmp/peaches-ggv-ic-prove3.out`).
4. Spot-check while temp up: Owner desk empty invoice/allocation/ar_ap/payment=null live_billing=false staff_ready=false recorded_count=0 slot_count=6; honesty cap_ggv_06=SPECIFIED cr_state=OPEN; refuse invent-live-billing/payment/books/bzg-compose **403**; CAP-GGV-06 SPECIFIED; CR-6a19c9221cab0178 OPEN; prod depth **404**.
5. Killed temp. `launchctl bootstrap` + `kickstart` Beta → `cloudflare_access` pid **87787**. Anon + spoof `X-Wolf-Subject` → **403** `missing_auth`. Prod pid **15975**.

**Peaches verdict:** ENGINEERING_PASS confirmed. CAP-GGV-06 stays SPECIFIED. Empty≠live billing/invoice/allocation/AR-AP/payment. Not deployed-commissioned. Not staff_ready. proven=false ready=false staff_ready=false. haikal_human=not_started. devi_retest=parked. ClickUp+Telegram RETIRED. Uncommitted soft head `f3ab8f7`.

## Exit

```
EXIT: SUCCESS
PASS=243 FAIL=0
VERDICT: PASS ENGINEERING_PASS
```
