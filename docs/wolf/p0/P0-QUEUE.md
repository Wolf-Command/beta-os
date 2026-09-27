# P0 execution queue

SYSTEM = 19.65 / 77 = 25.52% ; STAFF READY = 0 ; HUMAN COMMISSIONED = 0 ; OPERATING ADOPTION = NOT MEASURED

Pack S2. Owner brief 27 Sep 2026 16:32 WITA. This is the one execution queue. Rule W3-P5-PRIORITY-v1. The ledger score was not raised.

Register count is **12**. `build_war_room()` in S1 returned P0 12, P1 20, P2 42, P3 3. The closed set is CAP-CORE-01 through CAP-CORE-10, plus CAP-MSC-02 and CAP-INTG-07. There is no thirteenth P0.

CAP-CORE-02 is READY_FOR_HUMAN. CAP-INTG-07 is BLOCKED_OWNER. CAP-CORE-05 is CLOSED after the empty-table deny in commit `fcae665`. CAP-CORE-08 is BLOCKED_OWNER after the self-close deny in commit `e2cab4f`. Live `core_sod_constraints` stayed 0. No finance pack was inserted. CAP-MSC-02 stays OPEN after the deny prove in commit `025dd13`. CAP-CORE-01 stays OPEN after the unsigned registry deny in commit `99f5a27`. CAP-CORE-06 stays OPEN after the temporary trail in commit `2229b21`. CAP-CORE-07 stays OPEN after the approval-route prove in commit `ab4af72`. CAP-CORE-09 stays OPEN after the gate list in commit `9d0b83c`. Live `core_evidence_records` is 4, not 3. No requirement was inserted. CAP-CORE-03 stays OPEN after the unsigned board deny in commit `5a814fe`. No grant was added. No person was created. CAP-CORE-04 and CAP-CORE-10 stay OPEN without a new slice. Staff ready, human commissioned, and operating adoption stay unset. None of these twelve is waiting on a named external provider.

Order is the critical path. A prerequisite is another P0 the next bar actually waits on. The catalog records no extra prerequisite inside the kernel, because those rows are already PROVEN or READY. That does not make the deployed observation done.

## 1. CAP-CORE-02 — Person & Auth Identity

- Current state: SYSTEM READY (1.00). Staff ready no. Human commissioned no. `test_real_auth_binding.py` PASS=51. Unsigned `GET /signout` on Beta `:8788` pid 59914 is 302 to the Access application logout. Unsigned and a bad JWT stay 403 on `/api/core/me`. No seated 200 was observed. There is no `ROLE-OWNER` row. Authorization is `person_id` plus assignment, not a name.
- Exact missing evidence: a real Cloudflare session for Haikal, Devi, and Matt, the landing and cross-role statuses, and the same route denied after Sign out.
- Cursor work: done in commit `8247252`. Evidence: `docs/wolf/p0/P0-CAP-CORE-02-RESULT.md`. Human test: `docs/wolf/p0/HUMAN-TESTS.md`. Do not mark anyone commissioned.
- Human work: one minute, after sign-out exists, on `https://beta.wolfcommand.net`. Haikal signs in and expects `/content-2.0`, denied on `/bzg/uma-blu`, `/wolf`, and `/ggv/finance`. Devi signs in and expects `/bzg/uma-blu`, denied on `/content-2.0`, `/wolf`, and `/ggv/finance`. Matt signs in and expects `/wolf`. Each person signs out. Record the statuses. The walk does not raise SYSTEM.
- External dependency: none.
- Prerequisite: none.
- Closure test: unsigned and a bad JWT stay 403 on `/api/core/me`. After each real session, landing and cross-role denial match the walk. After sign-out, the same route is denied. The local verifier is not this test.
- Target: READY_FOR_HUMAN. Status: READY_FOR_HUMAN. Commit: `8247252`.

## 2. CAP-INTG-07 — Secrets & Environment Separation

- Current state: SYSTEM SPECIFIED (0.05). The 27 Sep search named `~/.openclaw/credentials/` (decision 2026-07-21, plaintext, 30 JSON files). 1Password has no account. The keychain service `wolf-secrets-vault` encrypts off-site copies. It is not a vault product. Footage crypt, rclone, and the Atrium scratch backup are not this capability. No second vault was built.
- Exact missing evidence: a vault product Matt names, then a rotation and Dev/Beta/Prod separation prove. The repo-check test is not that prove.
- Cursor work: done. Evidence: `docs/wolf/p0/P0-CAP-INTG-07-RESULT.md`. The ledger was not edited.
- Human work: Matt names the vault product, or records that none is authorised.
- External dependency: none.
- Prerequisite: none.
- Closure test: the search names the store, with no secret value in the note. The ledger stays SPECIFIED. A passing repo-check test does not close this item.
- Target: BLOCKED_OWNER. Status: BLOCKED_OWNER. Commit: `44cd296`.

## 3. CAP-MSC-02 — Access & Cloudflare Posture

- Current state: SYSTEM BUILT (0.25). The deny prove is recorded. On Beta `:8788` pid 59914, unsigned, a spoofed email header, `X-Wolf-Subject`, and `Cf-Access-Jwt-Assertion: a.b.c` are 403 on `/api/core/me`, `/api/msc/posture`, and `/wolf`. The public hostname returns 302 to the Access login for those three paths. Access includes were not changed. No seated 200 was observed.
- Exact missing evidence: a review note that is not this queue, binding that deny prove to CAP-MSC-02. The 2026-09-20 review covers the empty framework and does not bind this prove. Seated allow and cross-role denial wait on the CAP-CORE-02 walk.
- Cursor work: done for the deny slice in commit `025dd13`. Evidence: `docs/wolf/p0/P0-CAP-MSC-02-RESULT.md`. Do not repeat the curl. Do not write the review. Do not call Grok. Do not raise the ledger.
- Human work: none for the deny prove. A seated observation uses the CAP-CORE-02 session and is not commissioning. The review is not that walk.
- External dependency: none.
- Prerequisite: CAP-CORE-02.
- Closure test: the deny cases exit 0, and a review note that is not this queue binds the result to CAP-MSC-02. The test half passed (`SUMMARY pass=38 fail=0`). The review half is absent, so the row stays OPEN. This queue does not raise the ledger.
- Target: CLOSED. Status: OPEN. Commit: `025dd13`. Remaining: the review note.

## 4. CAP-CORE-01 — Organisation Registry

- Current state: SYSTEM PROVEN (0.80). The entity list was already fail-closed. On Beta `:8788` pid 59914, an unsigned read of a real entity, its brands, locations, departments, and a brand returned 200. A missing id returned 404 with no identity. Commit `99f5a27` uses the same `organisation.entity.read` gate as the list. On pid 64196 those eight paths are 403 for unsigned, a spoofed email, `X-Wolf-Subject`, and a bad JWT. There is no separate org UI page. Catalog projection, not a session: `PERS-HAIKAL` and `PERS-DEVI` lack the grant. `PERS-MATT` holds it. No seated 200 was observed.
- Exact missing evidence: the Beta status of these routes under a real Cloudflare session. Allow for a person who holds the grant. Deny for a person who does not. The catalog projection is not that status.
- Cursor work: done for the unsigned slice in commit `99f5a27`. Evidence: `docs/wolf/p0/P0-CAP-CORE-01-RESULT.md`. After a real session, record `/api/core/entities` and one entity read. Do not send `X-Wolf-Subject`. Do not raise the ledger. Do not mark CLOSED from the unsigned deny.
- Human work: the session is CAP-CORE-02. No separate org acceptance. No organisation page was added.
- External dependency: none.
- Prerequisite: CAP-CORE-02.
- Closure test: the Beta status under the real session is recorded, including a denial for a person without organisation read. Unsigned stays fail-closed. The unsigned half passed (`SUMMARY pass=123 fail=0`). The seated half is absent, so the row stays OPEN. `test_org_registry.py` is not this closure. It is pass=35 fail=3. The three fails are the pre-existing census checks (brands 12, Habitat present, GGV owns 5). They were not repaired.
- Target: CLOSED. Status: OPEN. Commit: `99f5a27`. Remaining: the seated read.

## 5. CAP-CORE-03 — Role / Position / Assignment

- Current state: SYSTEM PROVEN (0.80). On Beta `:8788` pid 64196 the role list, the position list, and a missing id did not check identity. Commit `5a814fe` uses `organisation.role.read`. On pid 74540, unsigned, a spoofed email, `X-Wolf-Subject`, and a bad JWT are 403 on the board paths. `/api/core/me/assignments` was already 403. The public hostname redirects those paths to the Access login. Catalog projection, not a session: `PERS-MATT` and `PERS-AMANDA` hold the grant. `PERS-HAIKAL`, `PERS-DEVI`, `PERS-MISA`, and `PERS-LEAD-DEMO` lack it. Stored `ASG-HAIKAL-CD-1` is ACTIVE and primary. Stored `ASG-HAIKAL-VE-1` is ENDED. Live persons stayed 6. Live assignments stayed 10. No seated 200 was observed.
- Exact missing evidence: `GET /api/core/persons/PERS-HAIKAL/assignments` on Beta under a real Cloudflare session. Allow for a person who holds `organisation.role.read`. Deny for a person who does not. The stored rows are not that status.
- Cursor work: done for the unsigned slice in commit `5a814fe`. Evidence: `docs/wolf/p0/P0-CAP-CORE-03-RESULT.md`. Do not add a grant. Do not create a person. Do not move a primary assignment. After a real session, record the status. Do not raise the ledger. Do not mark CLOSED from the unsigned deny.
- Human work: the session is CAP-CORE-02. No separate assignment acceptance. Changing a primary assignment is a separate owner decision.
- External dependency: none.
- Prerequisite: CAP-CORE-01, CAP-CORE-02. The seated org read that keeps CAP-CORE-01 OPEN was not used. The critical path records no extra prerequisite.
- Closure test: Beta shows the stored active assignment and does not show the ended assignment as active. No new person row. Unsigned board stays denied. The unsigned half passed (`SUMMARY pass=172 fail=0`). The seated half is absent, so the row stays OPEN. `test_role_position_assignment.py` is exit 1, pass=33 fail=5. The fails are the pre-existing census checks (positions 12, assignments 10, GGV positions, scope NOT_BUILT, org_scopes present). They were not repaired. The suite's temporary rows were removed. Live assignments stayed 10.
- Target: CLOSED. Status: OPEN. Commit: `5a814fe`. Remaining: the seated read.

## 6. CAP-CORE-04 — Permission & Authority Engine

- Current state: SYSTEM PROVEN (0.80). The full seat matrix was not re-run on Beta. `ROLE-GGV-CREATIVE-DIRECTOR` does not hold `organisation.entity.read`. The ended edit grant does not apply.
- Exact missing evidence: allow and deny on Beta for the existing seats, under a verified person. The D3 catalog projection is not that HTTP proof.
- Cursor work: record allow and deny for `PERS-HAIKAL`, `PERS-DEVI`, and `PERS-MATT` only. Do not add a grant. Do not authorize by display name.
- Human work: the three sign-ins are CAP-CORE-02. This item records the statuses. It does not commission the people.
- External dependency: none.
- Prerequisite: CAP-CORE-03.
- Closure test: recorded statuses match the grants already on those assignments. Unsigned stays 403.
- Target: CLOSED. Status: OPEN.

## 7. CAP-CORE-05 — Authority Limits Evaluator

- Current state: SYSTEM PROVEN (0.80). The queue row is CLOSED. On a deleted catalog copy with zero limit rows, `PERS-MATT` on `content.plan.approve` and `PERS-HAIKAL` on `content.plan.edit` were denied (`higher_approval_required`, `no_matching_authority_limit`). An email string was not an allow. Live `org_authority_limits` stayed 0. On Beta `:8788` pid 64196, unsigned, a spoofed email, `X-Wolf-Subject`, and a bad JWT are 403 on `GET /api/core/authority/check` and `GET /api/core/me/authority-limits`. The public hostname redirects those two GETs to the Access login. No seated check was observed. The live count 0 is configuration, not a tolerance.
- Exact missing evidence: none for this queue row. The ledger READY bar was not observed and is not claimed.
- Cursor work: done in commit `fcae665`. Evidence: `docs/wolf/p0/P0-CAP-CORE-05-RESULT.md`. No limit was inserted. The ledger was not raised.
- Human work: none.
- External dependency: none.
- Prerequisite: CAP-CORE-04. The closure test does not use the seated matrix that keeps CAP-CORE-04 OPEN. The critical path records no extra prerequisite.
- Closure test: the action is denied, and the live count is still 0. That test passed (`SUMMARY pass=39 fail=0`). The empty table was not filled. `test_authority_limits.py` is pass=48 fail=1. The fail is `scope required denied`, already recorded in D1. It was not repaired.
- Target: CLOSED. Status: CLOSED. Commit: `fcae665`.

## 8. CAP-CORE-06 — Work Items / Promises / Decisions

- Current state: SYSTEM PROVEN (0.80). On a deleted catalog copy, one item walked OPEN, IN_PROGRESS, BLOCKED, IN_PROGRESS, COMPLETED, VERIFIED. Verify from IN_PROGRESS was denied and left IN_PROGRESS. Live `core_work_items` stayed 0. On Beta `:8788` pid 64196, unsigned, a spoofed email, `X-Wolf-Subject`, and a bad JWT are 403 on `GET /api/core/work-items` and `GET /api/core/work-items/WI-NONE`. Unsigned POST is 403. The public hostname redirects those two GETs to the Access login. No seated read was observed.
- Exact missing evidence: `GET /api/core/work-items` on Beta under a real Cloudflare session. The live table is empty, so that read must match count 0. The temporary trail is not that read.
- Cursor work: done for the temporary trail in commit `2229b21`. Evidence: `docs/wolf/p0/P0-CAP-CORE-06-RESULT.md`. Do not create a live work item. Do not mint a JWT. After a real session, record the status and count. Do not raise the ledger. Do not mark CLOSED from the temporary trail.
- Human work: none beyond the CAP-CORE-02 session used for the Beta read. That walk is not commissioning of this row.
- External dependency: none.
- Prerequisite: CAP-CORE-02.
- Closure test: the temporary trail has the stored states, the live work-item count is unchanged, and the Beta read under the real session matches the stored row. The temporary half passed (`SUMMARY pass=48 fail=0`). The live count stayed 0. The seated half is absent, so the row stays OPEN.
- Target: CLOSED. Status: OPEN. Commit: `2229b21`. Remaining: the seated read of the empty live list.

## 9. CAP-CORE-07 — Approval Engine

- Current state: SYSTEM PROVEN (0.80). On a deleted catalog copy, `PERS-MATT` resolved `ENT-BZG` and `ENT-GGV` and the engine listed zero requests. The copy was not written. Live `core_approval_requests` stayed 0. Live `core_approval_decisions` stayed 6. Live `core_governance_policies` stayed 1, id `GPO-HABITAT-CONTENT-PUBLISH`. That row is not a wide production pack. On Beta `:8788` pid 64196, unsigned, a spoofed email, `X-Wolf-Subject`, and a bad JWT are 403 on `GET /api/core/approvals` and `GET /api/core/approvals/APR-NONE`. Unsigned POST is 403. The public hostname redirects those two GETs to the Access login. No seated read was observed.
- Exact missing evidence: `GET /api/core/approvals` on Beta under a real Cloudflare session. The live request table is empty, so that read must match count 0. A wide production policy pack was not authored. The stored Habitat policy and the six decisions are not that pack.
- Cursor work: done for the copy read and the unsigned deny in commit `ab4af72`. Evidence: `docs/wolf/p0/P0-CAP-CORE-07-RESULT.md`. Do not insert a policy row. Do not mint a JWT. After a real session, record the status and count. Do not raise the ledger. Do not mark BLOCKED_OWNER from this prove.
- Human work: Matt authors a wide production policy pack, or records that none is authorised. The seated read uses the CAP-CORE-02 session. It is not commissioning.
- External dependency: none.
- Prerequisite: CAP-CORE-06. The copy read does not use the work-item trail that keeps CAP-CORE-06 OPEN. The critical path records no extra prerequisite.
- Closure test: Beta shows the engine, live `core_approval_requests` is still 0, and a pack exists only if Matt authored it. The copy half passed (`SUMMARY pass=56 fail=0`). The live request count stayed 0. The policy count stayed 1. The seated half is absent, so the row stays OPEN. `test_approval_engine.py` is pass=57 fail=3. The fails are the live decision count 6, already recorded in D1. They were not repaired.
- Target: BLOCKED_OWNER. Status: OPEN. Commit: `ab4af72`. Remaining: the seated read of the empty request list, then Matt's pack decision.

## 10. CAP-CORE-08 — Segregation of Duties

- Current state: SYSTEM PROVEN (0.80). The queue row is BLOCKED_OWNER. On a deleted catalog copy, `PERS-MATT` holds `venue.close.verify` through `ROLE-MATT` and `ASG-MATT-OWNER-1`. A resolved close submitted by `PERS-MATT` and resolved by `PERS-DEVI` stayed `RESOLVED` when `PERS-MATT` verified (`sod_self_close`). A display name and an email string were `forbidden`. `PERS-DEVI` on `ROLE-BZG-FB-OPS-LEAD` does not hold verify, so her verify was `forbidden`. `PERS-HAIKAL` was `forbidden`. The copy had no cash amount. Live `core_sod_constraints` stayed 0. Live `venue_daily_closes` stayed 0. `ROLE-BZG-CLOSER` has no active assignment. On Beta `:8788` pid 64196, unsigned, a spoofed email, `X-Wolf-Subject`, and a bad JWT are 403 on `GET /api/venue-close/list` and `POST /api/venue-close/verify`. The public hostname redirects the list GET to the Access login.
- Exact missing evidence: a broader finance SoD pack only if Matt authors one, or a record that no pack is authorised. The self-close deny is not that pack. The live count 0 is the absence of a pack. It is not a chosen finance rule.
- Cursor work: done in commit `e2cab4f`. Evidence: `docs/wolf/p0/P0-CAP-CORE-08-RESULT.md`. No constraint was inserted. No cash amount was written. The ledger was not raised. Do not seat a closer.
- Human work: Matt decides whether a broader finance SoD pack is required. If it is, he authors it. Cursor does not write the pack.
- External dependency: none.
- Prerequisite: CAP-CORE-04, CAP-CORE-07. The critical path records no extra prerequisite. This slice does not use the seat matrix or the approval seated read.
- Closure test: the temporary self-close deny still fails closed, and no new SoD pack was written to the live catalog. That test passed (`SUMMARY pass=73 fail=0`). The live constraint count stayed 0. `test_sod_constraints.py` is exit 1, PASS=42 FAIL=2, then `ApprovalError: required permission denied: test.spend.approve`. D1 already recorded that abort. It was not repaired.
- Target: BLOCKED_OWNER. Status: BLOCKED_OWNER. Commit: `e2cab4f`.

## 11. CAP-CORE-09 — Evidence Requirements

- Current state: SYSTEM PROVEN (0.80). The gate list is commit `9d0b83c`. Eight actions call the gate: `approval.request`, `approval.decide`, `work.loop.submit`, `HABITAT.CONTENT.PUBLISH`, `HABITAT.CONTENT.PUBLISH.submit`, `SPEND_APPROVE`, `EXCEPTION`, `GENERAL_MATERIAL`. Six stay not gated: `venue.close.declare_cash`, `venue.close.resolve_exception`, `venue.close.verify`, `ggv.nota.submit`, `uma.receive_goods`, `work.item.complete`. The only ACTIVE requirement is `EVR-HABITAT-CONTENT-PUBLISH`. Before `scripts/tests/test_work_loop.py` the live `core_evidence_records` count was 3. That suite left `EVD-50e827bd` invalidated, reason `P4-TEST cleanup`, at `2026-09-27T10:06:44Z`. Hard delete is refused. The count is 4. `core_approval_decisions` is 9. The no-delete triggers were not dropped. No requirement was inserted. The ledger stays PROVEN. Beta `:8788` stayed pid 64196. Production pid 15975 was not restarted.
- Exact missing evidence: the closure test asked for the live evidence count to stay 3. It is 4. The six not-gated actions stay open. Universal packs were not inserted.
- Cursor work: the list is done. Evidence: `docs/wolf/p0/P0-CAP-CORE-09-RESULT.md`. Do not drop the no-delete trigger. Do not delete `EVD-50e827bd`. Do not insert a requirement. Do not mark CLOSED from a count of 4.
- Human work: none for the list. Accepting the residue as the new count, or authorising a delete past the trigger, was not done.
- External dependency: none.
- Prerequisite: CAP-CORE-07. The critical path records no extra prerequisite. This list does not use the approval seated read.
- Closure test: every material action is named as gated or not gated, and the live evidence count is still 3. An ungated action stays listed as open. The list half passed (`SUMMARY pass=69 fail=0`) against the count of 4. The count half failed. The ledger was not raised.
- Target: CLOSED. Status: OPEN. Commit: `9d0b83c`. Remaining: the live count is 4, not 3.

## 12. CAP-CORE-10 — Exception / Override Governance

- Current state: SYSTEM PROVEN (0.80). Live `core_governance_exceptions` is 2. An operating review cadence is the READY bar.
- Exact missing evidence: that cadence, and a deployed view of the two existing exceptions. The two rows are not a cadence.
- Cursor work: show the existing exception read on Beta after the real session. Do not add a row.
- Human work: a person reviews the real exceptions on a repeating basis. That has not happened. It is not commissioning.
- External dependency: none.
- Prerequisite: CAP-CORE-09.
- Closure test: Beta shows the stored exceptions, the live count is still 2, and the cadence is not marked done without a person having run it.
- Target: READY_FOR_HUMAN. Status: OPEN.

## Cheap independent P1

These five do not edit the kernel. They are not a reason to skip an open P0.

1. CAP-GGV-02 Publish Gate. SYSTEM READY. The round-3 content walk is human. Do not hold it for The One = 0, 4,787 unknown brand, or 124 preview failures.
2. CAP-BZG-03 Venue Daily Close. SYSTEM READY. The absent policy now says BLOCKED BY BUSINESS POLICY. Do not invent a threshold, seat a closer, write ESB, or run a live close.
3. CAP-INTG-01 Yanolja. SYSTEM ABSENT. Leave it. Do not invent a feed.
4. CAP-FIN-03 accountant seat. `POS-GGV-EXT-ACCT` is empty. Do not invent a person. Amanda's content grant is not that seat.
5. CAP-FIN-01 books. Leave UNAVAILABLE. Do not type a balance.

CAP-STRAT-02 is not on this list. It requires CAP-CORE-01, CAP-CORE-06, and CAP-CORE-07.

## Variance sentence

When `venue_close_variance_policies` has no rows, the operator sentence is **BLOCKED BY BUSINESS POLICY**. `live_variance_threshold` remains the row count. That count is 0. It is not a tolerance.

Checked this session:

- `test_uma_blu_daily_close.py`: 71 passed, 0 failed, including the display assertion. Live policy count stayed 0.
- `test_uma_daily_loop_finish.py`: PASS=47 FAIL=0, including `lead-close shows BLOCKED BY BUSINESS POLICY`. Production pid 15975 and Beta pid 35844 were unchanged during that run.
- `test_progress_dashboard.py`: 198 passed, 0 failed, including the Empire variance sentence.
- `test_uma_ops_console.py`: PASS=24 FAIL=0.
- `test_blocker_explain.py`: PASS=55 FAIL=1. The failure is `issues page keeps Example label` in `dashboards/bzg-uma-blu-issues.html`, which this pack did not edit. The new close-policy assertions passed. Not repaired.

Beta `:8788` was restarted with `launchctl kickstart -k gui/501/net.wolfcommand.serve-beta` so the honesty route loaded the new field. Production `:8787` stayed pid 15975 (`serve.py`). Beta came back as pid 58953 (`scripts/serve_beta.py`).

Unsigned on pid 58953:

- `GET /api/venue-close/honesty` 200, `variance_policy_display` = `BLOCKED BY BUSINESS POLICY`, `live_variance_threshold` = 0
- `GET /uma-blu-close` 403
- `GET /uma-blu-close.html` 200, the phrase is in the body, the old "No variance policy set" sentence is not
- `GET /signout` 404

RESULT: PASS
