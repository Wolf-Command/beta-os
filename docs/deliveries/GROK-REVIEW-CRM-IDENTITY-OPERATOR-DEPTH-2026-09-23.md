# GROK REVIEW — CRM Identity Operator Depth — 2026-09-23

- Run: `BF-crm-identity-operator-depth-20260923`
- Plan: `docs/deliveries/GROK-PLAN-CRM-IDENTITY-OPERATOR-DEPTH-2026-09-23.md`
- Bound: `beta-crm-loop-safe` (Beta `:8788` only)
- Claim: `bf-crm-identity-operator-depth-20260923`
- Reviewed: 2026-09-23 ~15:20 WITA
- Verdict: **ENGINEERING_PASS** (Cursor prove PASS=142 FAIL=0 under temporary `development_assertion`; launchd Beta restored `cloudflare_access`)

## Decision served

keep_building_without_matt (owner-autonomous-release-2026-09-19) + CAP-CRM-02 customer identity memory v1 PICK 2026-09-19. Extends the existing identity desk after CORE Ops × Needs-You connective ENGINEERING_PASS. No BZG compose. No invent staff_ready / PROVEN / READY / graph_complete / silent merge.

## What landed

- `scripts/core/crm_identity_operator_depth.py` — desk + object detail for customers and link candidates; match confidence stays `uncertain`; human review required while uncertain; note / next-action-touch / handoff-touch / dismiss-noise / review-decision (`still_uncertain` / `not_a_match` / `keep_separate`); refresh of the identity desk and the CRM Needs-You projection; schema `wolf.crm-identity-operator-depth.v1`
- `scripts/serve_beta.py` — additive routes: `/api/crm/identity/operator-depth`, `/rbac`, `/objects/{id}`, and operator actions; refuse proven / ready / staff-ready / merge / habitat / cutover / klaviyo / money / secret / access / compose / production
- `dashboards/crm-identity.html` — confidence-match panel (`#identity-depth`) on the existing desk (no orphan dashboard)
- `scripts/core/wolf_shell.py` — honesty flag `crm_identity_operator_depth=true`
- `scripts/tests/test_crm_identity_operator_depth.py` — **PASS=142 FAIL=0** · `EXIT: SUCCESS`

## Evidence table

| Check | Claimed | Verified |
|---|---|---|
| Tests | PASS=142 FAIL=0 | PASS=142 FAIL=0 |
| Anon desk | 403 | live `:8788` → **403** under `development_assertion` |
| Amanda desk + rbac + detail + review | 200 | ok; staff_ready=false; proven=false; merged=false; confidence uncertain |
| Owner desk | 200 | live 200 |
| Haikal next-action | 200 | live 200; lead_spine_mutated=false |
| Outsider / Devi | 403 | 403; Devi `outsider` |
| Proven / cutover refuse | 403 | 403 ×2 |
| Amanda page | 200 | `/crm-identity` contains `#identity-depth` |
| CAP-CRM-01 / 04 | BUILT | BUILT |
| CAP-CRM-02 / 03 | SPECIFIED | SPECIFIED |
| AU-CRM-01-HABITAT | NOT STARTED | NOT STARTED |
| CRM + Progress/CORE CRs (8) | OPEN | OPEN ×8 (not false-resolved) |
| Ports | 8787/8788 up | True / True |
| Production pid | 15975 | **15975** untouched; prod depth **404** |
| Auth restore | cloudflare_access | launchd Beta restored pid **58869**; spoof `X-Wolf-Subject` → **403** `missing_auth` |
| WIP quartet | untouched | hash-object unchanged ×4 |

## Red team

- CLAIMED≠PROVEN/READY invent: CAP-CRM-02 stays **SPECIFIED**; staff_ready=false; proven=false; ready=false
- Skeleton≠usable loop: customer and link-candidate detail, uncertain confidence, human review, and the five operator actions refresh the identity desk and Needs-You projection
- Review decision does not merge and does not complete the graph; dismissed noise does not delete the candidate row
- Target CRM CRs and Progress/CORE CRs remain **OPEN**
- Anon fail-closed 403; outsider 403; Devi 403; proven/cutover refused
- No money · no Klaviyo/Metricool write · no CRM cutover · no Habitat commission · no BZG compose · no CF Access Include mutate · no secret mint
- No second lead-spine mutate surface
- Production untouched

## Live prove (temporary `development_assertion`)

1. `launchctl bootout` Beta only (`net.wolfcommand.serve-beta`); start `BETA_AUTH_MODE=development_assertion` on `:8788` (temp listen pid 58741). Auth mode payload was `development_assertion`. Production pid stayed **15975**
2. Anon desk → **403**; Amanda desk/rbac/page/detail/review → **200**; Owner 200; Haikal next-action 200; outsider 403; Devi 403 `outsider`
3. Proven/cutover refuse 403; CAP-CRM-02 SPECIFIED; CRs OPEN×8; prod depth 404; prod pid **15975**
4. Kill temp server; `launchctl bootstrap` + `kickstart` Beta (no `BETA_AUTH_MODE` ⇒ `cloudflare_access`)
5. Spoof `X-Wolf-Subject` → **403** `missing_auth`; anon 403 `missing_auth`; auth-mode payload `cloudflare_access`; Production pid **15975** unchanged; Beta listen pid **58869**

## Honesty

- proven=false · ready=false · staff_ready=false
- haikal_human=not_started · devi_retest=parked
- CAP-CRM-02 stays **SPECIFIED**; CAP-CRM-01 and CAP-CRM-04 stay **BUILT**; CAP-CRM-03 stays **SPECIFIED**
- AU-CRM-01-HABITAT stays **NOT STARTED**
- Do **not** false-resolve CR-ff42f3a7c49caa79, CR-820682ce791563fa, CR-e5ff219bb1d585f7, CR-c8719063fb940ed4, or the Progress/CORE CRs — they stay **OPEN**
- Empty candidate register = EMPTY honesty (not a complete identity graph)

## UI check

The identity page and operator actions were exercised over HTTP on `:8788` (desk, object detail, review-decision, next-action-touch, page HTML contains `#identity-depth`). No browser click-through was available in this session.

## Exit

```
EXIT: SUCCESS
PASS=142 FAIL=0
```
