# GROK REVIEW — MSC Asset / Mgmt Operator Depth — 2026-09-23

- Run: `BF-msc-asset-operator-depth-20260923`
- Plan: `docs/deliveries/GROK-PLAN-MSC-ASSET-OPERATOR-DEPTH-2026-09-23.md`
- Bound: `beta-core-safe` (Beta `:8788` only)
- Claim: `bf-msc-asset-operator-depth-20260923`
- Reviewed: 2026-09-23 16:06 WITA
- Verdict: **PASS** (Cursor prove PASS=142 FAIL=0 under temporary `development_assertion`; launchd Beta restored `cloudflare_access`)

## Decision served

keep_building_without_matt (`state/build-claims/owner-autonomous-release-2026-09-19.json`) + CAP-MSC-01 asset register. Extends the existing MSC Management Cluster / Asset Register after INTG connector operator depth stayed PARKED. This pack does not restart that lane and does not compose BZG.

## What landed

- `scripts/core/msc_asset_operator_depth.py` — Owner desk for an asset, its maintenance note, an MSC desk module, or the EMPTY placeholder when the register has no rows. Actions: note / next-action-touch / handoff-touch / dismiss-noise / review-decision (`still_specified` / `not_complete` / `keep_as_note`). Recording refreshes the MSC desk projection and the MSC Needs-You projection and does not write the asset register. Schema `wolf.msc-asset-operator-depth.v1`
- `scripts/serve_beta.py` — additive routes: `/api/msc/assets/operator-depth` and `/api/msc/mgmt-cluster/operator-depth`, plus `/rbac`, `/objects/{id}`, and operator actions. Refuse inventory-complete / compliance-done / mfa-live / legal-hold / proven / ready / staff-ready / access-include / secret-mint / money / bzg-compose / production
- `dashboards/msc-assets.html` — operator depth panel (`#asset-depth`) on the live asset desk
- `dashboards/msc-mgmt-cluster.html` — same panel on the preserved cluster file. Top-level `/msc-mgmt-cluster` still soft-lands to `/progress` and does not copy the panel there
- `scripts/core/wolf_shell.py` — honesty flag `msc_asset_operator_depth=true`
- `scripts/tests/test_msc_asset_operator_depth.py` — **PASS=142 FAIL=0** · `EXIT: SUCCESS`

## Evidence table

| Check | Claimed | Verified |
|---|---|---|
| Tests | PASS=142 FAIL=0 | PASS=142 FAIL=0 |
| Anon desk | 403 | live `:8788` → **403** under `development_assertion` |
| Owner desk + rbac + detail + next-action | 200 | ok; staff_ready=false; inventory_count=null; register_mutated=false |
| Cluster API desk | 200 | schema `wolf.msc-asset-operator-depth.v1` |
| Outsider / Haikal / Devi / Amanda / Misa | 403 | 403 |
| Inventory-complete / proven refuse | 403 | 403 ×2 |
| CAP-MSC-01/03/04/05 | SPECIFIED | SPECIFIED |
| CAP-MSC-02 | BUILT | BUILT |
| AU-MSC-02-CF-DOORS | NOT STARTED | NOT STARTED (discovery file unchanged by the unit actions) |
| MSC CRs (5) | OPEN | OPEN ×5 |
| Progress/CORE CRs (4) | OPEN | OPEN ×4 |
| Asset desk page | `#asset-depth` | live `/msc-assets` **200** contains the panel |
| Cluster URL | soft-land | `/msc-mgmt-cluster` **302** → `/progress`; progress HTML does not contain the panel |
| Ports | 8787/8788 up | True / True |
| Production pid | 15975 | **15975** untouched; prod depth **404** |
| Auth restore | cloudflare_access | launchd Beta restored; spoof `X-Wolf-Subject` → **403** `missing_auth`; anon **403** |
| WIP quartet | untouched | sha unchanged ×4 |

## Red team

- CLAIMED≠PROVEN/READY invent: CAP-MSC-01/03/04/05 stay **SPECIFIED**; CAP-MSC-02 stays **BUILT**; staff_ready=false; inventory_complete=false; mfa_live=false; compliance_done=false; legal_hold_active=false
- Skeleton≠usable loop: empty placeholder and real asset/maintenance/MSC desk objects take the five allowed actions and refresh MSC desk + Needs-You. The asset register row count does not change
- AU-MSC-02-CF-DOORS stays **NOT STARTED**. No Cloudflare Access Include mutate. No secret mint
- Target MSC CRs and Progress/CORE CRs remain **OPEN**
- Anon fail-closed 403; outsider 403; inventory-complete and proven refused
- No BZG compose · no money · no INTG recover · Devi retest parked · Haikal human not_started
- Production untouched

## Live prove (temporary `development_assertion`)

1. `launchctl bootout` Beta only (`net.wolfcommand.serve-beta`); start `BETA_AUTH_MODE=development_assertion` on `:8788` (temp listen pid 63551). Auth mode payload was `development_assertion`. Production pid stayed **15975**
2. Anon desk → **403**; Owner desk/rbac/detail/next-action → **200**; cluster API desk **200**; outsider, Haikal, Devi, Amanda, Misa **403**
3. Inventory-complete and proven refuse **403**; CAP-MSC-01/03/04/05 SPECIFIED; CAP-MSC-02 BUILT; AU NOT STARTED; MSC CRs OPEN ×5; Progress/CORE CRs OPEN ×4; `/msc-assets` contains `#asset-depth`; `/msc-mgmt-cluster` soft-lands to `/progress` without the panel; prod depth **404**; prod pid **15975**
4. Kill temp server; `launchctl bootstrap` + `kickstart` Beta (no `BETA_AUTH_MODE` ⇒ `cloudflare_access`)
5. Spoof `X-Wolf-Subject` → **403** `missing_auth`; anon **403**; Production pid **15975** unchanged

A signed-in browser click-through was not run. The asset page and the operator actions were exercised over HTTP on `:8788`.

## Honesty

- proven=false · ready=false · staff_ready=false
- CAP-MSC-01/03/04/05 stay **SPECIFIED** · CAP-MSC-02 stays **BUILT**
- AU-MSC-02-CF-DOORS stays **NOT STARTED**
- Do **not** false-resolve CR-7ea69933a9d39ba9, CR-80296d7bc9c35452, CR-1f93c785c88e9564, CR-7dae8b389cce6f9a, CR-2d299c339747f432, or the Progress/CORE CRs — they stay **OPEN**
- Empty register = EMPTY honesty (not an inventory count)

## Exit

```
EXIT: SUCCESS
PASS=142 FAIL=0
```
